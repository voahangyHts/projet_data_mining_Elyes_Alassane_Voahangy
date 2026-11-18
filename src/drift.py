"""Rapport de dérive (Evidently) : les dernières commandes ressemblent-elles à l'historique ?

Référence : commandes de l'historique (eval_set = prior)
Courant   : dernière commande de chaque client (eval_set = train)
Variables : jour, heure, délai depuis la commande précédente,
            taille du panier, part de produits rachetés.
Sortie    : reports/drift_report.html

Evidently 0.7 n'est pas compatible avec pandas 3 (utilisé par le projet) :
le script tourne dans un environnement séparé, lancé par « make drift ».
"""
from pathlib import Path

import polars as pl
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42
TAILLE = 50_000  # commandes tirées au hasard dans chaque jeu

NUMERIQUES = [
    "order_hour_of_day",
    "days_since_prior_order",
    "taille_panier",
    "part_rachetes",
]
CATEGORIELLES = ["order_dow"]


def commandes(eval_set, fichier_lignes):
    """Un échantillon de commandes avec la taille du panier et la part de rachats."""
    orders = (
        pl.read_parquet(f"{P}/orders.parquet")
        .filter(pl.col("eval_set") == eval_set)
        .sample(n=TAILLE, seed=GRAINE)
        .select("order_id", "order_dow", "order_hour_of_day", "days_since_prior_order")
    )
    paniers = (
        pl.scan_parquet(f"{P}/{fichier_lignes}")
        .join(orders.lazy().select("order_id"), on="order_id")
        .group_by("order_id")
        .agg(
            taille_panier=pl.len(),
            part_rachetes=pl.col("reordered").cast(pl.Float64).mean(),
        )
        .collect()
    )
    table = orders.join(paniers, on="order_id").drop("order_id")
    return table.with_columns(pl.col("order_dow").cast(pl.String)).to_pandas()


def main():
    SORTIE.mkdir(exist_ok=True)
    reference = commandes("prior", "order_products__prior.parquet")
    courant = commandes("train", "order_products__train.parquet")
    print(f"Référence : {len(reference):,} commandes ; courant : {len(courant):,}")

    definition = DataDefinition(
        numerical_columns=NUMERIQUES,
        categorical_columns=CATEGORIELLES,
    )
    ref = Dataset.from_pandas(reference, data_definition=definition)
    cour = Dataset.from_pandas(courant, data_definition=definition)

    rapport = Report([DataDriftPreset()])
    resultat = rapport.run(current_data=cour, reference_data=ref)

    fichier = SORTIE / "drift_report.html"
    resultat.save_html(str(fichier))
    print(f"Rapport de dérive enregistré dans {fichier}")

    # Résumé dans le terminal : moyennes des deux jeux, côte à côte
    resume = (
        pl.concat([
            pl.from_pandas(reference).select(NUMERIQUES).mean()
            .with_columns(jeu=pl.lit("référence (prior)")),
            pl.from_pandas(courant).select(NUMERIQUES).mean()
            .with_columns(jeu=pl.lit("courant (train)")),
        ])
        .select("jeu", *NUMERIQUES)
    )
    print(resume)


if __name__ == "__main__":
    main()