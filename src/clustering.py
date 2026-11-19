"""Segmentation des clients (ticket PAN-7) : K-means sur des variables de comportement.

Chaque k testé est tracé dans MLflow (expérience « segmentation_clients »),
avec le modèle retenu, ses graphiques et les profils des segments.

Prérequis : MLflow lancé (docker compose --profile mlops up -d)
Lancement : uv run python -m src.clustering
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # génère les graphiques en fichiers, sans ouvrir de fenêtre
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42
K_TESTES = range(2, 9)   # nombres de segments testés
K_FORCE = None           # mettre un nombre (ex. 4) pour imposer k après lecture des résultats
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
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
    # tri par client : group_by de Polars rend les lignes dans un ordre aléatoire,
    # ce qui changerait le résultat du K-means d'une exécution à l'autre
    return commandes_client.join(achats_client, on="user_id").sort("user_id").collect()


def numeroter_segments(labels: np.ndarray, nb_commandes: np.ndarray) -> np.ndarray:
    """Renumérote les segments par nombre moyen de commandes croissant.

    Le K-means numérote ses groupes au hasard : sans ce tri, le segment
    « fidèles » pourrait s'appeler 0 un jour et 2 le lendemain.
    """
    ordre = np.argsort([nb_commandes[labels == s].mean() for s in np.unique(labels)])
    nouveau = np.empty_like(ordre)
    nouveau[ordre] = np.arange(len(ordre))
    return nouveau[labels]


def nommer_segments(profils: pl.DataFrame) -> dict[int, str]:
    """Nom métier de chaque segment, déduit de son profil (et non de son numéro,
    que K-means peut attribuer différemment d'un lancement à l'autre)."""
    if profils.height != 3:
        return {s: f"Segment {s}" for s in profils["segment"].to_list()}
    fideles = profils.sort("nb_commandes", descending=True)["segment"][0]
    autres = profils.filter(pl.col("segment") != fideles)
    bio = autres.sort("part_bio", descending=True)["segment"][0]
    occasionnels = autres.filter(pl.col("segment") != bio)["segment"][0]
    return {
        fideles: "Fidèles réguliers",
        bio: "Gros paniers bio et frais du week-end",
        occasionnels: "Occasionnels petits paniers",
    }


def main() -> None:
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("segmentation_clients")
    SORTIE.mkdir(exist_ok=True)
    clients = construire_variables()
    print(f"{clients.height:,} clients décrits par {len(VARIABLES)} variables")

    # 1. Standardiser (nb_commandes passé au log car très asymétrique : 3 à 99)
    X_brut = clients.select(VARIABLES).with_columns(pl.col("nb_commandes").log1p()).to_numpy()
    normaliseur = StandardScaler().fit(X_brut)
    X = normaliseur.transform(X_brut)

    # 2. Choisir k : coude (inertie) + silhouette
    # Un run MLflow parent « kmeans_segmentation », avec un run enfant par k testé
    run_parent = mlflow.start_run(run_name="kmeans_segmentation")
    mlflow.log_params({
        "variables": ", ".join(VARIABLES),
        "k_testes": f"{min(K_TESTES)}-{max(K_TESTES)}",
        "n_init": 10,
        "graine": GRAINE,
        "nb_clients": clients.height,
    })
    print("\n  k   inertie   silhouette")
    resultats = []
    for k in K_TESTES:
        km = KMeans(n_clusters=k, n_init=10, random_state=GRAINE).fit(X)
        sil = silhouette_score(X, km.labels_, sample_size=10_000, random_state=GRAINE)
        resultats.append((k, km.inertia_, sil))
        print(f"  {k}   {km.inertia_:9.0f}   {sil:.3f}")
        with mlflow.start_run(run_name=f"kmeans_k{k}", nested=True):
            mlflow.log_param("k", k)
            mlflow.log_metrics({"inertie": km.inertia_, "silhouette": sil})

    ks, inerties, sils = zip(*resultats)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(ks, inerties, marker="o"); ax1.set(title="Méthode du coude", xlabel="k", ylabel="inertie")
    ax2.plot(ks, sils, marker="o"); ax2.set(title="Score de silhouette", xlabel="k", ylabel="silhouette")
    fig.tight_layout(); fig.savefig(SORTIE / "choix_k.png", dpi=120); plt.close(fig)

    # k retenu : meilleure silhouette entre 3 et 6 segments (utilisables par le métier), sauf choix imposé
    k = K_FORCE or max((r for r in resultats if 3 <= r[0] <= 6), key=lambda r: r[2])[0]
    km = KMeans(n_clusters=k, n_init=10, random_state=GRAINE).fit(X)
    segments = numeroter_segments(km.labels_, clients["nb_commandes"].to_numpy())
    clients = clients.with_columns(segment=pl.Series(segments))
    print(f"\nk retenu : {k}")

    # 3. Profil moyen de chaque segment (pour le nommer)
    profils = (
        clients.group_by("segment")
        .agg(nb_clients=pl.len(), *[pl.col(v).mean().round(2) for v in VARIABLES])
        .sort("segment")
    )
    noms = nommer_segments(profils)
    profils = profils.with_columns(
        nom_segment=pl.col("segment").replace_strict(noms, return_dtype=pl.String)
    )
    clients = clients.with_columns(
        nom_segment=pl.col("segment").replace_strict(noms, return_dtype=pl.String)
    )
    pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(200)
    print("\nProfil moyen des segments :")
    print(profils)
    profils.write_csv(SORTIE / "segments_profils.csv")
    clients.select("user_id", "segment", "nom_segment").write_parquet(f"{P}/segments_clients.parquet")

    # 4. Projection ACP en 2D (5 000 clients tirés au hasard, pour la lisibilité)
    idx = np.random.default_rng(GRAINE).choice(len(X), size=5_000, replace=False)
    coords = PCA(n_components=2, random_state=GRAINE).fit_transform(X)[idx]
    fig, ax = plt.subplots(figsize=(6, 5))
    nuage = ax.scatter(coords[:, 0], coords[:, 1], c=segments[idx], cmap="tab10", s=6, alpha=0.6)
    ax.legend(*nuage.legend_elements(), title="segment"); ax.set(title="Segments clients (ACP 2D)", xlabel="CP1", ylabel="CP2")
    fig.tight_layout(); fig.savefig(SORTIE / "segments_acp.png", dpi=120); plt.close(fig)
    print(f"\nGraphiques et profils enregistrés dans {SORTIE}/")

    # 5. MLflow : k retenu, ses scores, ses graphiques et le modèle (normalisation + K-means)
    sil_retenu = next(r[2] for r in resultats if r[0] == k)
    mlflow.log_param("k_retenu", k)
    mlflow.log_params({f"nom_segment_{s}": n for s, n in noms.items()})
    mlflow.log_metrics({"silhouette_k_retenu": sil_retenu, "inertie_k_retenu": km.inertia_})
    for fichier in ["choix_k.png", "segments_acp.png", "segments_profils.csv"]:
        mlflow.log_artifact(str(SORTIE / fichier), artifact_path="rapports")
    modele = make_pipeline(normaliseur, km)
    mlflow.sklearn.log_model(modele, name="kmeans", input_example=X_brut[:3])
    mlflow.end_run()
    print(f"Segmentation tracée dans MLflow (run {run_parent.info.run_id[:8]})")


if __name__ == "__main__":
    main()