"""EDA – test des 3 hypothèses métier (H1, H2, H3) sur les données propres.

Lancement : uv run python -m src.eda_hypotheses
"""

import polars as pl

P = "data/processed"
pl.Config.set_tbl_rows(30)
pl.Config.set_tbl_hide_dataframe_shape(True)

# --- Chargement (lazy) ---
orders = pl.scan_parquet(f"{P}/orders.parquet")
prior = pl.scan_parquet(f"{P}/order_products__prior.parquet")
departments = pl.scan_parquet(f"{P}/departments.parquet")
products = pl.scan_parquet(f"{P}/products.parquet").with_columns(
    bio=pl.col("product_name").str.contains("(?i)organic")
).select("product_id", "department_id", "bio")

# Lignes de commandes enrichies, SANS les 1res commandes
lignes = (
    prior.join(orders.select("order_id", "user_id", "is_first_order"), on="order_id")
    .filter(~pl.col("is_first_order"))
    .join(products, on="product_id")
    .join(departments, on="department_id")
)

taux_global = lignes.select(pl.col("reordered").mean()).collect().item()
print(f"\nTaux de réachat global (hors 1res commandes) : {taux_global:.1%}")

# ===================== H1 =====================
print("\n=== H1 – Les clients qui commandent souvent rachètent davantage ===")
delai_client = (
    orders.filter(~pl.col("is_first_order") & (pl.col("eval_set") == "prior"))
    .group_by("user_id")
    .agg(delai_moyen=pl.col("days_since_prior_order").mean())
)
reachat_client = lignes.group_by("user_id").agg(taux_reachat=pl.col("reordered").mean())
h1 = (
    delai_client.join(reachat_client, on="user_id")
    .with_columns(
        frequence=pl.when(pl.col("delai_moyen") <= 7).then(pl.lit("1. hebdo (<= 7 j)"))
        .when(pl.col("delai_moyen") <= 14).then(pl.lit("2. 8-14 j"))
        .when(pl.col("delai_moyen") <= 21).then(pl.lit("3. 15-21 j"))
        .otherwise(pl.lit("4. > 21 j"))
    )
    .collect()
)
print(
    h1.group_by("frequence")
    .agg(nb_clients=pl.len(), taux_reachat_moyen=pl.col("taux_reachat").mean().round(3))
    .sort("frequence")
)
corr = h1.select(pl.corr("delai_moyen", "taux_reachat", method="spearman")).item()
print(f"Corrélation de Spearman (délai moyen / taux de réachat) : {corr:.2f}")

# ===================== H2 =====================
print("\n=== H2 – Les produits frais et bio sont plus rachetés ===")
print(
    lignes.group_by("department")
    .agg(nb_lignes=pl.len(), taux_reachat=pl.col("reordered").mean().round(3))
    .sort("taux_reachat", descending=True)
    .collect()
)
print(
    lignes.group_by("bio")
    .agg(nb_lignes=pl.len(), taux_reachat=pl.col("reordered").mean().round(3))
    .sort("bio")
    .collect()
)

# ===================== H3 =====================
print("\n=== H3 – Le moment de commande et la position dans le panier comptent ===")
panier = (
    prior.group_by("order_id").agg(taille_panier=pl.len())
    .join(orders.select("order_id", "order_dow", "order_hour_of_day"), on="order_id")
)
print("Par jour de la semaine (order_dow 0 à 6) :")
print(
    panier.group_by("order_dow")
    .agg(nb_commandes=pl.len(), panier_moyen=pl.col("taille_panier").mean().round(2))
    .sort("order_dow")
    .collect()
)
print("Par heure de commande :")
print(
    panier.group_by("order_hour_of_day")
    .agg(nb_commandes=pl.len(), panier_moyen=pl.col("taille_panier").mean().round(2))
    .sort("order_hour_of_day")
    .collect()
)
print("Par position dans le panier (ordre d'ajout) :")
print(
    lignes.with_columns(
        position=pl.when(pl.col("add_to_cart_order") == 1).then(pl.lit("1. 1er produit"))
        .when(pl.col("add_to_cart_order") <= 5).then(pl.lit("2. 2e à 5e"))
        .when(pl.col("add_to_cart_order") <= 10).then(pl.lit("3. 6e à 10e"))
        .otherwise(pl.lit("4. 11e et +"))
    )
    .group_by("position")
    .agg(nb_lignes=pl.len(), taux_reachat=pl.col("reordered").mean().round(3))
    .sort("position")
    .collect()
)