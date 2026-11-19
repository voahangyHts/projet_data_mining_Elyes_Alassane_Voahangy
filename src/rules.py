"""Règles d'association (ticket PAN-7) : FP-Growth sur les paniers Instacart.

Deux niveaux d'analyse :
- rayons (134 aisles)       -> implantation des rayons en magasin
- produits (top 200 ventes) -> ventes croisées entre rayons et offres groupées

Chaque niveau est tracé dans MLflow (expérience « regles_association ») :
paramètres, nombre de règles, lift maximal et top 5 des règles.

Prérequis : MLflow lancé (docker compose --profile mlops up -d)
Lancement : uv run python -m src.rules
"""

import os
from pathlib import Path

import mlflow
import pandas as pd
import polars as pl
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42             # graine aléatoire fixée : même échantillon à chaque exécution
NB_COMMANDES = 300_000  # échantillon de commandes (sur 3,2 M)
NB_PRODUITS = 200       # produits les plus vendus gardés pour l'analyse par produit
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def get_association_rules(transactions, min_support=0.05, min_lift=1.2, min_confidence=0.6, top=5):
    """Squelette d'Elyes, adapté : transactions = liste de paniers (listes d'articles).

    top=None renvoie toutes les règles retenues (pour les filtrer ensuite).
    """
    te = TransactionEncoder()
    te_ary = te.fit_transform(transactions, sparse=True)            # matrice creuse : économise la mémoire
    df = pd.DataFrame.sparse.from_spmatrix(te_ary, columns=te.columns_)

    # FP-Growth (plus rapide qu'Apriori)
    frequent_itemsets = fpgrowth(df, min_support=min_support, use_colnames=True)

    # Filtrage par le lift
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)

    # On garde les règles fiables, triées par lift
    top_rules = rules[rules["confidence"] >= min_confidence].sort_values("lift", ascending=False)
    print(f"  {len(frequent_itemsets)} ensembles fréquents, {len(rules)} règles avec lift >= {min_lift}, "
          f"{len(top_rules)} avec confiance >= {min_confidence}")

    # Traçabilité MLflow (si un run est ouvert)
    if mlflow.active_run():
        mlflow.log_params({
            "min_support": min_support,
            "min_lift": min_lift,
            "min_confidence": min_confidence,
            "nb_paniers": len(transactions),
        })
        mlflow.log_metrics({
            "nb_ensembles_frequents": len(frequent_itemsets),
            "nb_regles_lift": len(rules),
            "nb_regles_retenues": len(top_rules),
            "lift_max": float(top_rules["lift"].max()) if len(top_rules) else 0.0,
        })
    return top_rules if top is None else top_rules.head(top)


def ventes_croisees(rules: pd.DataFrame, rayon_de: dict) -> pd.DataFrame:
    """Garde les règles entre produits de rayons DIFFÉRENTS et supprime les doublons A=>B / B=>A."""

    def rayons(produits):
        return {rayon_de[p] for p in produits}

    entre_rayons = [
        rayons(a).isdisjoint(rayons(c)) for a, c in zip(rules["antecedents"], rules["consequents"])
    ]
    croisees = rules[entre_rayons].copy()
    # même paire de produits lue dans les deux sens -> on garde la règle la plus fiable
    croisees["paire"] = [a | c for a, c in zip(croisees["antecedents"], croisees["consequents"])]
    croisees = (
        croisees.sort_values("confidence", ascending=False)
        .drop_duplicates("paire")
        .drop(columns="paire")
        .sort_values("lift", ascending=False)
    )
    print(f"  {len(croisees)} règles entre rayons différents (sans doublons)")
    return croisees


def lisible(rules: pd.DataFrame) -> pd.DataFrame:
    """Met les règles sous une forme lisible : 'A, B  =>  C' avec les 3 métriques."""
    return pd.DataFrame({
        "si le panier contient": rules["antecedents"].apply(lambda s: ", ".join(sorted(s))),
        "alors il contient aussi": rules["consequents"].apply(lambda s: ", ".join(sorted(s))),
        "support": rules["support"].round(3),
        "confiance": rules["confidence"].round(2),
        "lift": rules["lift"].round(2),
    })


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 45)
    SORTIE.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("regles_association")
    parametres_communs = {"nb_commandes": NB_COMMANDES, "graine": GRAINE, "algorithme": "FP-Growth"}

    # 1. Échantillon de commandes
    commandes = (
        pl.scan_parquet(f"{P}/orders.parquet")
        .filter(pl.col("eval_set") == "prior")
        .select("order_id")
        .collect()
        .sample(n=NB_COMMANDES, seed=GRAINE)
    )
    lignes = (
        pl.scan_parquet(f"{P}/order_products__prior.parquet")
        .join(commandes.lazy(), on="order_id")
        .join(pl.scan_parquet(f"{P}/products.parquet"), on="product_id")
        .join(pl.scan_parquet(f"{P}/aisles.parquet"), on="aisle_id")
        .select("order_id", "product_name", "aisle")
        .collect()
    )
    print(f"Échantillon : {NB_COMMANDES:,} commandes, {lignes.height:,} produits achetés")

    # 2. Niveau RAYONS : chaque panier = liste des rayons visités
    paniers_rayons = (
        lignes.group_by("order_id").agg(pl.col("aisle").unique()).get_column("aisle").to_list()
    )
    print("\n=== Règles entre RAYONS (implantation en magasin) ===")
    with mlflow.start_run(run_name="fpgrowth_rayons"):
        mlflow.log_params({**parametres_communs, "niveau": "rayons"})
        top_rayons = lisible(get_association_rules(paniers_rayons, min_support=0.05, min_lift=1.2, min_confidence=0.6))
        print(top_rayons.to_string(index=False))
        top_rayons.to_csv(SORTIE / "regles_rayons.csv", index=False)
        mlflow.log_artifact(str(SORTIE / "regles_rayons.csv"), artifact_path="regles")

    # 3. Niveau PRODUITS : on garde les 200 produits les plus vendus
    top_produits = (
        lignes.group_by("product_name").len().sort("len", descending=True).head(NB_PRODUITS)
        .get_column("product_name")
    )
    paniers_produits = (
        lignes.filter(pl.col("product_name").is_in(top_produits.implode()))
        .group_by("order_id").agg(pl.col("product_name").unique())
        .filter(pl.col("product_name").list.len() >= 2)        # un panier d'1 produit ne crée pas de règle
        .get_column("product_name").to_list()
    )
    rayon_de = dict(lignes.select("product_name", "aisle").unique().iter_rows())

    print(f"\n=== Règles entre PRODUITS – {len(paniers_produits):,} paniers ===")
    with mlflow.start_run(run_name="fpgrowth_produits"):
        mlflow.log_params({**parametres_communs, "niveau": "produits", "nb_produits": NB_PRODUITS})
        toutes = get_association_rules(paniers_produits, min_support=0.003, min_lift=1.5, min_confidence=0.1, top=None)
        toutes_croisees = ventes_croisees(toutes, rayon_de)
        croisees = lisible(toutes_croisees.head(5))
        print("Top 5 des ventes croisées entre rayons différents :")
        print(croisees.to_string(index=False))
        croisees.to_csv(SORTIE / "regles_produits.csv", index=False)
        mlflow.log_metric("nb_ventes_croisees", len(toutes_croisees))
        mlflow.log_artifact(str(SORTIE / "regles_produits.csv"), artifact_path="regles")

    print(f"\nRésultats enregistrés dans {SORTIE}/")


if __name__ == "__main__":
    main()