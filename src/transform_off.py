"""Transformation Open Food Facts : JSON brut -> table propre validée.

Entrée : data/raw/off/produits_*.parquet
Sortie : data/processed/off_produits.parquet (contrat OffProduits)
"""
import json
import logging
from pathlib import Path

import polars as pl

from src.schemas import OffProduits

BRUT = "data/raw/off/produits_*.parquet"
SORTIE = Path("data/processed/off_produits.parquet")
NUTRISCORES = {"a", "b", "c", "d", "e"}
ECOSCORES = {"a-plus", "a", "b", "c", "d", "e", "f"}
SCHEMA = {
    "code": pl.String,
    "nom": pl.String,
    "marques": pl.String,
    "categories": pl.String,
    "nutriscore": pl.String,
    "ecoscore": pl.String,
    "nova": pl.Int64,
    "allergenes": pl.String,
    "vendu_en_france": pl.Boolean,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


def texte(valeur):
    """Nettoie un texte : espaces en trop retirés, texte vide -> None."""
    if not isinstance(valeur, str):
        return None
    valeur = " ".join(valeur.split())
    return valeur or None


def liste(tags):
    """['en:gluten', 'en:nuts'] -> 'gluten | nuts' (préfixe de langue retiré)."""
    if not tags:
        return None
    propres = [t.split(":", 1)[-1] for t in tags if isinstance(t, str)]
    return " | ".join(propres) or None


def note(valeur, autorisees):
    """Garde une note seulement si elle est valide ('unknown' -> None)."""
    valeur = texte(valeur)
    if valeur is None:
        return None
    valeur = valeur.lower()
    return valeur if valeur in autorisees else None


def nova(valeur):
    """Groupe NOVA : un entier de 1 à 4, sinon None."""
    try:
        valeur = int(valeur)
    except (TypeError, ValueError):
        return None
    return valeur if 1 <= valeur <= 4 else None


def extraire(code, texte_json):
    """Découpe le JSON d'un produit en colonnes propres."""
    p = json.loads(texte_json)
    return {
        "code": code,
        "nom": texte(p.get("product_name")),
        "marques": texte(p.get("brands")),
        "categories": liste(p.get("categories_tags")),
        "nutriscore": note(p.get("nutriscore_grade"), NUTRISCORES),
        "ecoscore": note(p.get("ecoscore_grade"), ECOSCORES),
        "nova": nova(p.get("nova_group")),
        "allergenes": liste(p.get("allergens_tags")),
        "vendu_en_france": "en:france" in (p.get("countries_tags") or []),
    }


def main():
    brut = pl.read_parquet(BRUT)
    log.info("%d lignes brutes lues", brut.height)

    # Un code interrogé deux fois : on garde la réponse la plus récente
    brut = brut.sort("_ingested_at").unique(subset="code", keep="last")

    trouves = brut.filter(
        (pl.col("status") == "1") & pl.col("json_produit").is_not_null()
    )
    log.info(
        "%d codes interrogés, %d trouvés sur Open Food Facts (%.1f %%)",
        brut.height, trouves.height, 100 * trouves.height / brut.height,
    )
    if trouves.height == 0:
        log.error("Aucun produit trouvé : rien à transformer")
        raise SystemExit(1)

    lignes = [
        extraire(code, j)
        for code, j in zip(trouves["code"], trouves["json_produit"])
    ]
    propre = pl.DataFrame(lignes, schema=SCHEMA).with_columns(
        trouves["_ingested_at"].dt.replace_time_zone(None).alias("ingested_at")
    )

    OffProduits.validate(propre)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    propre.write_parquet(SORTIE)
    log.info("%d produits propres : contrat OK, écrits dans %s", propre.height, SORTIE)

    for colonne in ["nutriscore", "ecoscore", "nova"]:
        print(propre[colonne].value_counts().sort(colonne))


if __name__ == "__main__":
    main()