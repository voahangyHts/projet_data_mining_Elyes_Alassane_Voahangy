"""Segmentation des clients (ticket PAN-7) : K-means sur des variables de comportement.

Lancement : uv run python -m src.clustering
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # génère les graphiques en fichiers, sans ouvrir de fenêtre
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42
K_TESTES = range(2, 9)   # nombres de segments testés
K_FORCE = None           # mettre un nombre (ex. 4) pour imposer k après lecture des résultats
VARIABLES = ["nb_commandes", "delai_moyen", "panier_moyen", "taux_reachat",
             "part_bio", "part_frais", "part_jours_0_1"]


def construire_variables() -> pl.DataFrame:
    """Une ligne par client, avec ses variables de comportement (historique prior)."""
    orders = pl.scan_parquet(f"{P}/orders.parquet").filter(pl.col("eval_set") == "prior")
    prior = pl.scan_parquet(f"{P}/order_products__prior.parquet")
    products = (
        pl.scan_parquet(f"{P}/products.parquet")
        .join(pl.scan_parquet(f"{P}/departments.parquet"), on="department_id")
        .select(
            "product_id",
            bio=pl.col("product_name").str.contains("(?i)organic"),
            frais=pl.col("department").is_in(["produce", "dairy eggs"]),
        )
    )
    paniers = prior.group_by("order_id").agg(taille=pl.len())

    commandes_client = (
        orders.join(paniers, on="order_id")
        .group_by("user_id")
        .agg(
            nb_commandes=pl.len(),
            delai_moyen=pl.col("days_since_prior_order").mean(),   # les vides (1re commande) sont ignorés
            panier_moyen=pl.col("taille").mean(),
            part_jours_0_1=pl.col("order_dow").is_in([0, 1]).mean(),
        )
    )
    achats_client = (
        prior.join(orders.select("order_id", "user_id", "is_first_order"), on="order_id")
        .join(products, on="product_id")
        .group_by("user_id")
        .agg(
            taux_reachat=pl.col("reordered").filter(~pl.col("is_first_order")).mean(),
            part_bio=pl.col("bio").mean(),
            part_frais=pl.col("frais").mean(),
        )
    )
    return commandes_client.join(achats_client, on="user_id").collect()


def main() -> None:
    SORTIE.mkdir(exist_ok=True)
    clients = construire_variables()
    print(f"{clients.height:,} clients décrits par {len(VARIABLES)} variables")

    # 1. Standardiser (nb_commandes passé au log car très asymétrique : 3 à 99)
    X = clients.select(VARIABLES).with_columns(pl.col("nb_commandes").log1p()).to_numpy()
    X = StandardScaler().fit_transform(X)

    # 2. Choisir k : coude (inertie) + silhouette
    print("\n  k   inertie   silhouette")
    resultats = []
    for k in K_TESTES:
        km = KMeans(n_clusters=k, n_init=10, random_state=GRAINE).fit(X)
        sil = silhouette_score(X, km.labels_, sample_size=10_000, random_state=GRAINE)
        resultats.append((k, km.inertia_, sil))
        print(f"  {k}   {km.inertia_:9.0f}   {sil:.3f}")

    ks, inerties, sils = zip(*resultats)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(ks, inerties, marker="o"); ax1.set(title="Méthode du coude", xlabel="k", ylabel="inertie")
    ax2.plot(ks, sils, marker="o"); ax2.set(title="Score de silhouette", xlabel="k", ylabel="silhouette")
    fig.tight_layout(); fig.savefig(SORTIE / "choix_k.png", dpi=120); plt.close(fig)

    # k retenu : meilleure silhouette entre 3 et 6 segments (utilisables par le métier), sauf choix imposé
    k = K_FORCE or max((r for r in resultats if 3 <= r[0] <= 6), key=lambda r: r[2])[0]
    km = KMeans(n_clusters=k, n_init=10, random_state=GRAINE).fit(X)
    clients = clients.with_columns(segment=pl.Series(km.labels_))
    print(f"\nk retenu : {k}")

    # 3. Profil moyen de chaque segment (pour le nommer)
    profils = (
        clients.group_by("segment")
        .agg(nb_clients=pl.len(), *[pl.col(v).mean().round(2) for v in VARIABLES])
        .sort("segment")
    )
    pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(200)
    print("\nProfil moyen des segments :")
    print(profils)
    profils.write_csv(SORTIE / "segments_profils.csv")
    clients.select("user_id", "segment").write_parquet(f"{P}/segments_clients.parquet")

    # 4. Projection ACP en 2D (5 000 clients tirés au hasard, pour la lisibilité)
    idx = np.random.default_rng(GRAINE).choice(len(X), size=5_000, replace=False)
    coords = PCA(n_components=2, random_state=GRAINE).fit_transform(X)[idx]
    fig, ax = plt.subplots(figsize=(6, 5))
    nuage = ax.scatter(coords[:, 0], coords[:, 1], c=km.labels_[idx], cmap="tab10", s=6, alpha=0.6)
    ax.legend(*nuage.legend_elements(), title="segment"); ax.set(title="Segments clients (ACP 2D)", xlabel="CP1", ylabel="CP2")
    fig.tight_layout(); fig.savefig(SORTIE / "segments_acp.png", dpi=120); plt.close(fig)
    print(f"\nGraphiques et profils enregistrés dans {SORTIE}/")


if __name__ == "__main__":
    main()