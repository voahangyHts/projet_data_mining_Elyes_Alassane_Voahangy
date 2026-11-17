"""Transformation RappelConso : brut (data/raw) -> propre (data/processed).

Lancement : uv run python -m src.transform_rappelconso
"""

import logging
from pathlib import Path

import polars as pl

from src.schemas import Rappels

BRUT = "data/raw/rappelconso/rappels_*.parquet"
SORTIE = Path("data/processed/rappels.parquet")
TEXTES = [
    "sous_categorie_produit",
    "marque_produit",
    "libelle",
    "motif_rappel",
    "risques_encourus",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("transform_rappelconso")


def main() -> None:
    brut = pl.read_parquet(BRUT)
    log.info("%s lignes brutes lues", f"{brut.height:,}")

    # 1. Filtrer : uniquement l'alimentation
    alim = brut.filter(
        pl.col("categorie_produit").str.to_lowercase() == "alimentation"
    )
    log.info("%s lignes de la catégorie alimentation", f"{alim.height:,}")

    # 2. Nettoyer les textes (retours à la ligne, espaces en trop)
    alim = alim.with_columns(
        pl.col(c).str.replace_all(r"\s+", " ").str.strip_chars()
        for c in TEXTES
    )

    # GTIN valide = 8 à 14 chiffres.
    # Les autres ('0', '1'...) sont des valeurs de remplissage.
    gtin_propre = pl.col("gtin").str.strip_chars()
    gtin_valide = gtin_propre.str.contains(r"^\d{8,14}$")
    nb_invalides = alim.filter(~gtin_valide).height
    log.warning(
        "%s GTIN invalides remplacés par une valeur vide",
        f"{nb_invalides:,}",
    )

    # 3. Typer et renommer
    propre = alim.select(
        pl.col("id").cast(pl.Int64),
        pl.col("numero_version").cast(pl.Int16, strict=False),
        pl.when(gtin_valide).then(gtin_propre).otherwise(None).alias("gtin"),
        *TEXTES,
        pl.col("date_publication")
        .str.to_datetime("%Y-%m-%dT%H:%M:%S%z")
        .dt.replace_time_zone(None),
        pl.col("date_de_fin_de_la_procedure_de_rappel")
        .str.to_date("%Y-%m-%d", strict=False)
        .alias("date_fin_procedure"),
        pl.col("lien_vers_la_fiche_rappel").alias("lien_fiche"),
        pl.col("_ingested_at").dt.replace_time_zone(None).alias("ingested_at"),
    )

    # 4. Dédoublonner : version la plus récente de chaque (rappel, produit)
    avant = propre.height
    propre = propre.sort(
        ["numero_version", "ingested_at"], descending=True, nulls_last=True
    ).unique(subset=["id", "gtin"], keep="first", maintain_order=True)
    log.info(
        "%s doublons / anciennes versions retirés",
        f"{avant - propre.height:,}",
    )

    # 5. Contrat de données puis écriture
    Rappels.validate(propre)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    propre.sort("date_publication", descending=True).write_parquet(SORTIE)
    log.info(
        "%s rappels alimentaires : contrat OK, écrits dans %s",
        f"{propre.height:,}",
        SORTIE,
    )


if __name__ == "__main__":
    main()