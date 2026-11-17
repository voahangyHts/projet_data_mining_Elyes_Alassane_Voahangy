"""Transformation RNM : prix bruts (data/raw/rnm) -> propres (data/processed).

Lancement : uv run python -m src.transform_rnm
"""

import logging
from pathlib import Path

import polars as pl

from src.schemas import PrixRnm

BRUT = "data/raw/rnm/prix_*.parquet"
SORTIE = Path("data/processed/rnm_prix.parquet")

# Mot-clé anglais pour retrouver les produits Instacart correspondants
MOTS_CLES = {
    "TOMATE": "tomato", "POMME": "apple", "POIRE": "pear",
    "BANANE": "banana", "CAROTTE": "carrot", "CONCOMBRE": "cucumber",
    "COURGETTE": "zucchini", "OIGNON": "onion", "AIL": "garlic",
    "CITRON": "lemon", "ORANGE": "orange", "CLEMENTINE": "clementine",
    "KIWI": "kiwi", "AVOCAT": "avocado", "FRAISE": "strawberr",
    "FRAMBOISE": "raspberr", "RAISIN": "grape", "ABRICOT": "apricot",
}
NOMBRES = ["prix_moyen", "variation", "mini", "maxi"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("transform_rnm")


def en_nombre(colonne: str) -> pl.Expr:
    """'0.92' ou '0,92' -> 0.92 ; texte vide -> valeur vide."""
    return (
        pl.col(colonne)
        .str.strip_chars()
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )


def main() -> None:
    brut = pl.read_parquet(BRUT)
    log.info("%s prix bruts lus", f"{brut.height:,}")

    propre = brut.select(
        "produit_code",
        pl.col("produit_code")
        .replace_strict(MOTS_CLES, default=None)
        .alias("mot_cle_instacart"),
        pl.col("marche").str.strip_chars(),
        pl.col("date_cotation").str.to_date("%d/%m/%y", strict=False),
        pl.col("stade").str.strip_chars(),
        pl.col("unite").str.extract(r"^([^*]*)", 1).str.strip_chars().alias("unite"),
        pl.col("unite").str.extract(r"\*\s*(.+)$", 1).str.strip_chars().alias("commentaire_marche"),
        pl.col("libelle").str.replace_all(r"\s+", " ").str.strip_chars(),
        *[en_nombre(c) for c in NOMBRES],
        "url",
        pl.col("_ingested_at").dt.replace_time_zone(None).alias("ingested_at"),
    )

    # Écarter les lignes sans prix
    sans_prix = propre.filter(pl.col("prix_moyen").is_null()).height
    propre = propre.filter(pl.col("prix_moyen").is_not_null())
    log.info("%s lignes sans prix écartées", f"{sans_prix:,}")

    sans_date = propre.filter(pl.col("date_cotation").is_null()).height
    if sans_date:
        log.warning("%s prix sans date de cotation lisible", f"{sans_date:,}")

    # Dédoublonner : la collecte la plus récente l'emporte
    cles = ["produit_code", "marche", "date_cotation", "stade", "libelle"]
    avant = propre.height
    propre = propre.sort("ingested_at", descending=True).unique(
        subset=cles, keep="first", maintain_order=True
    )
    log.info("%s doublons retirés", f"{avant - propre.height:,}")

    # Contrat de données puis écriture
    PrixRnm.validate(propre)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    propre.sort(["produit_code", "marche", "libelle"]).write_parquet(SORTIE)
    log.info("%s prix propres : contrat OK, écrits dans %s",
             f"{propre.height:,}", SORTIE)
    print(propre.group_by("unite").len().sort("len", descending=True))


if __name__ == "__main__":
    main()