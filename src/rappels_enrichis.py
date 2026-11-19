"""Table « or » : chaque rappel RappelConso enrichi de sa fiche Open Food Facts.

Jointure par code-barres : rappels.gtin = off_produits.code.
- Tous les rappels sont gardés (jointure à gauche) : un rappel sans code-barres
  ou inconnu d'Open Food Facts reste présent, avec trouve_off = False.
- Aucune valeur n'est inventée : les notes absentes restent vides.

Entrées : data/processed/rappels.parquet, data/processed/off_produits.parquet
Sortie  : data/processed/rappels_enrichis.parquet (contrat RappelsEnrichis)
Lancement : uv run python -m src.rappels_enrichis
"""
import logging
from pathlib import Path

import polars as pl

from src.schemas import RappelsEnrichis

P = "data/processed"
SORTIE = Path(f"{P}/rappels_enrichis.parquet")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


def enrichir(rappels: pl.DataFrame, off: pl.DataFrame) -> pl.DataFrame:
    """Ajoute à chaque rappel les informations Open Food Facts de son code-barres."""
    fiches = off.select(
        pl.col("code").alias("gtin"),
        pl.col("nom").alias("nom_off"),
        pl.col("marques").alias("marques_off"),
        "categories",
        "nutriscore",
        "ecoscore",
        "nova",
        "allergenes",
        "vendu_en_france",
        pl.lit(True).alias("trouve_off"),
    )
    table = rappels.join(fiches, on="gtin", how="left").with_columns(
        pl.col("trouve_off").fill_null(False)
    )
    # Le code-barres est unique côté Open Food Facts : la jointure
    # ne doit ni ajouter ni perdre de rappels.
    if table.height != rappels.height:
        raise ValueError(
            f"Jointure anormale : {rappels.height} rappels -> {table.height} lignes"
        )
    return table


def main():
    rappels = pl.read_parquet(f"{P}/rappels.parquet")
    off = pl.read_parquet(f"{P}/off_produits.parquet")
    table = enrichir(rappels, off)

    RappelsEnrichis.validate(table)
    table.write_parquet(SORTIE)

    avec_code = table.filter(pl.col("gtin").is_not_null()).height
    trouves = table.filter(pl.col("trouve_off")).height
    log.info(
        "%d rappels : %d avec code-barres, %d enrichis par Open Food Facts (%.1f %%)",
        table.height, avec_code, trouves, 100 * trouves / table.height,
    )
    log.info("Contrat OK, écrit dans %s", SORTIE)

    # Aperçu métier : Nutri-Score des produits rappelés et retrouvés
    print(
        table.filter(pl.col("trouve_off"))["nutriscore"]
        .value_counts()
        .sort("nutriscore")
    )
    # Les sous-catégories les plus rappelées, avec la part retrouvée dans OFF
    print(
        table.group_by("sous_categorie_produit")
        .agg(
            nb_rappels=pl.len(),
            part_trouvee=pl.col("trouve_off").mean().round(2),
        )
        .sort("nb_rappels", descending=True)
        .head(8)
    )


if __name__ == "__main__":
    main()
