"""Prédiction du réachat : baseline vs XGBoost, SHAP et équité.

Lancement : uv run python -m src.classification
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42
NB_CLIENTS = 30_000
VARIABLES = [
    # couple client-produit
    "up_nb_achats",
    "up_taux",
    "up_commandes_depuis",
    "up_position_moy",
    # client
    "nb_commandes",
    "delai_moyen",
    "panier_moyen",
    "user_taux_reachat",
    # produit
    "prod_nb_achats",
    "prod_taux_reachat",
    "bio",
    "frais",
    # commande à prédire
    "delai_cible",
    "jour_cible",
    "heure_cible",
]


def construire_table():
    """Une ligne par couple (client, produit déjà acheté).

    Cible : le produit est-il racheté dans la commande train ?
    """
    orders = pl.scan_parquet(f"{P}/orders.parquet")
    commandes_train = (
        orders.filter(pl.col("eval_set") == "train")
        .select(
            "user_id",
            "order_id",
            delai_cible="days_since_prior_order",
            jour_cible="order_dow",
            heure_cible="order_hour_of_day",
        )
        .collect()
        .sample(n=NB_CLIENTS, seed=GRAINE)
    )
    clients = commandes_train.select("user_id").lazy()

    prior_o = orders.filter(pl.col("eval_set") == "prior")
    prior_o = prior_o.join(clients, on="user_id")
    colonnes = ["order_id", "user_id", "order_number", "is_first_order"]
    lignes = pl.scan_parquet(f"{P}/order_products__prior.parquet")
    lignes = lignes.join(prior_o.select(colonnes), on="order_id")

    # Variables du couple client-produit
    up = lignes.group_by("user_id", "product_id").agg(
        up_nb_achats=pl.len(),
        up_derniere=pl.col("order_number").max(),
        up_position_moy=pl.col("add_to_cart_order").mean(),
    )

    # Variables du client
    paniers = (
        lignes.group_by("user_id", "order_id")
        .agg(taille=pl.len())
        .group_by("user_id")
        .agg(panier_moyen=pl.col("taille").mean())
    )
    historique = prior_o.group_by("user_id").agg(
        nb_commandes=pl.col("order_number").max(),
        delai_moyen=pl.col("days_since_prior_order").mean(),
    )
    reachat_client = (
        lignes.filter(~pl.col("is_first_order"))
        .group_by("user_id")
        .agg(user_taux_reachat=pl.col("reordered").mean())
    )
    user = paniers.join(historique, on="user_id")
    user = user.join(reachat_client, on="user_id", how="left")

    # Variables du produit (calculées sur TOUS les clients)
    toutes = pl.scan_parquet(f"{P}/order_products__prior.parquet")
    toutes = toutes.join(
        orders.select("order_id", "is_first_order"), on="order_id"
    )
    stats_produit = toutes.group_by("product_id").agg(
        prod_nb_achats=pl.len(),
        prod_taux_reachat=pl.col("reordered")
        .filter(~pl.col("is_first_order"))
        .mean(),
    )
    catalogue = (
        pl.scan_parquet(f"{P}/products.parquet")
        .join(
            pl.scan_parquet(f"{P}/departments.parquet"),
            on="department_id",
        )
        .select(
            "product_id",
            bio=pl.col("product_name")
            .str.contains("(?i)organic")
            .cast(pl.Int8),
            frais=pl.col("department")
            .is_in(["produce", "dairy eggs"])
            .cast(pl.Int8),
        )
    )
    produit = stats_produit.join(catalogue, on="product_id")

    # Cible : le produit est-il dans la commande train du client ?
    cible = (
        pl.scan_parquet(f"{P}/order_products__train.parquet")
        .join(
            commandes_train.lazy().select("order_id", "user_id"),
            on="order_id",
        )
        .select(
            "user_id",
            "product_id",
            achete=pl.lit(1, dtype=pl.Int8),
        )
    )

    table = (
        up.join(user, on="user_id")
        .join(produit, on="product_id")
        .join(commandes_train.lazy().drop("order_id"), on="user_id")
        .join(cible, on=["user_id", "product_id"], how="left")
        .with_columns(
            achete=pl.col("achete").fill_null(0),
            up_taux=pl.col("up_nb_achats") / pl.col("nb_commandes"),
            up_commandes_depuis=(
                pl.col("nb_commandes") - pl.col("up_derniere")
            ),
            user_taux_reachat=pl.col("user_taux_reachat").fill_null(0),
            prod_taux_reachat=pl.col("prod_taux_reachat").fill_null(0),
        )
    )
    return table.collect()


def meilleur_seuil(y, proba):
    """Seuil qui maximise le F1 (choisi sur la validation)."""
    seuils = np.arange(0.05, 0.95, 0.01)
    scores = [f1_score(y, proba >= s) for s in seuils]
    return float(seuils[np.argmax(scores)])


def evaluer(nom, y, proba, seuil):
    pred = proba >= seuil
    return {
        "modele": nom,
        "seuil": round(seuil, 2),
        "roc_auc": round(roc_auc_score(y, proba), 3),
        "pr_auc": round(average_precision_score(y, proba), 3),
        "f1": round(f1_score(y, pred), 3),
        "precision": round(precision_score(y, pred), 3),
        "rappel": round(recall_score(y, pred), 3),
    }


def main():
    SORTIE.mkdir(exist_ok=True)
    table = construire_table()
    taux = table["achete"].mean()
    print(f"{table.height:,} couples client-produit, {taux:.1%} rachetés")

    X = table.select(VARIABLES).to_pandas()
    y = table["achete"].to_numpy()
    groupes = table["user_id"].to_numpy()

    # 1. Découpage PAR CLIENT : test (20 %),
    #    puis validation (20 % du reste) pour choisir le seuil
    decoupe = GroupShuffleSplit(test_size=0.2, random_state=GRAINE)
    idx_app, idx_test = next(decoupe.split(X, y, groupes))
    X_app = X.iloc[idx_app]
    y_app = y[idx_app]
    g_app = groupes[idx_app]
    idx_ent, idx_val = next(decoupe.split(X_app, y_app, g_app))
    idx_ent = idx_app[idx_ent]
    idx_val = idx_app[idx_val]

    baseline = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000),
    )
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=GRAINE,
        n_jobs=-1,
    )
    modeles = {
        "Baseline (régression logistique)": baseline,
        "XGBoost": xgb,
    }

    resultats = []
    for nom, modele in modeles.items():
        modele.fit(X.iloc[idx_ent], y[idx_ent])
        proba_val = modele.predict_proba(X.iloc[idx_val])[:, 1]
        seuil = meilleur_seuil(y[idx_val], proba_val)
        # le jeu de test ne sert qu'ici, une seule fois
        proba_test = modele.predict_proba(X.iloc[idx_test])[:, 1]
        resultats.append(evaluer(nom, y[idx_test], proba_test, seuil))
        print(f"{nom} : entraîné")

    print("\nRésultats sur le jeu de TEST :")
    print(pl.DataFrame(resultats))

    # 2. SHAP : quelles variables pèsent le plus ?
    echantillon = X.iloc[idx_test].sample(2_000, random_state=GRAINE)
    valeurs = shap.TreeExplainer(xgb)(echantillon)
    shap.summary_plot(valeurs, echantillon, show=False)
    plt.tight_layout()
    plt.savefig(SORTIE / "shap_reachat.png", dpi=120)
    plt.close()
    importance = pl.DataFrame({
        "variable": VARIABLES,
        "shap_moyen": np.abs(valeurs.values).mean(axis=0),
    }).sort("shap_moyen", descending=True)
    print("\nImportance des variables (SHAP moyen) :")
    print(importance)

    # 3. Équité : le modèle est-il aussi bon pour chaque segment ?
    seuil_xgb = resultats[1]["seuil"]
    proba = xgb.predict_proba(X.iloc[idx_test])[:, 1]
    test = table[idx_test].with_columns(
        pred=pl.Series(proba >= seuil_xgb)
    )
    segments = pl.read_parquet(f"{P}/segments_clients.parquet")
    test = test.join(segments, on="user_id", how="left")
    vrais_positifs = pl.col("pred") & (pl.col("achete") == 1)
    equite = (
        test.group_by("segment")
        .agg(
            nb_couples=pl.len(),
            taux_reel=pl.col("achete").mean().round(3),
            rappel=vrais_positifs.sum() / (pl.col("achete") == 1).sum(),
            precision=vrais_positifs.sum() / pl.col("pred").sum(),
        )
        .sort("segment")
    )
    print("\nContrôle d'équité par segment (XGBoost, jeu de test) :")
    print(equite)

    fichier = SORTIE / "classification_resultats.csv"
    pl.DataFrame(resultats).write_csv(fichier)
    print(f"\nRésultats et graphique SHAP enregistrés dans {SORTIE}/")


if __name__ == "__main__":
    main()