"""Prédiction du réachat : baseline vs XGBoost, SHAP et équité.

Lancement : uv run python -m src.classification
"""

from pathlib import Path
import joblib

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
from sklearn.model_selection import GroupShuffleSplit, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import mlflow
from mlflow import MlflowClient

# ---- CONFIGURATION MLFLOW ----
mlflow.set_tracking_uri("http://localhost:5001")
mlflow.set_experiment("prediction_reachat")

P = "data/processed"
SORTIE = Path("reports")
GRAINE = 42
NB_CLIENTS = 30_000
VARIABLES = [
    "up_nb_achats", "up_taux", "up_commandes_depuis", "up_position_moy",
    "nb_commandes", "delai_moyen", "panier_moyen", "user_taux_reachat",
    "prod_nb_achats", "prod_taux_reachat", "bio", "frais",
    "delai_cible", "jour_cible", "heure_cible",
]

def construire_table():
    orders = pl.scan_parquet(f"{P}/orders.parquet")
    commandes_train = (
        orders.filter(pl.col("eval_set") == "train")
        .select("user_id", "order_id", delai_cible="days_since_prior_order", jour_cible="order_dow", heure_cible="order_hour_of_day")
        .collect()
        .sample(n=NB_CLIENTS, seed=GRAINE)
    )
    clients = commandes_train.select("user_id").lazy()

    prior_o = orders.filter(pl.col("eval_set") == "prior")
    prior_o = prior_o.join(clients, on="user_id")
    colonnes = ["order_id", "user_id", "order_number", "is_first_order"]
    lignes = pl.scan_parquet(f"{P}/order_products__prior.parquet")
    lignes = lignes.join(prior_o.select(colonnes), on="order_id")

    up = lignes.group_by("user_id", "product_id").agg(
        up_nb_achats=pl.len(),
        up_derniere=pl.col("order_number").max(),
        up_position_moy=pl.col("add_to_cart_order").mean(),
    )

    paniers = lignes.group_by("user_id", "order_id").agg(taille=pl.len()).group_by("user_id").agg(panier_moyen=pl.col("taille").mean())
    historique = prior_o.group_by("user_id").agg(nb_commandes=pl.col("order_number").max(), delai_moyen=pl.col("days_since_prior_order").mean())
    reachat_client = lignes.filter(~pl.col("is_first_order")).group_by("user_id").agg(user_taux_reachat=pl.col("reordered").mean())
    
    user = paniers.join(historique, on="user_id").join(reachat_client, on="user_id", how="left")

    toutes = pl.scan_parquet(f"{P}/order_products__prior.parquet").join(orders.select("order_id", "is_first_order"), on="order_id")
    stats_produit = toutes.group_by("product_id").agg(prod_nb_achats=pl.len(), prod_taux_reachat=pl.col("reordered").filter(~pl.col("is_first_order")).mean())
    
    catalogue = (
        pl.scan_parquet(f"{P}/products.parquet")
        .join(pl.scan_parquet(f"{P}/departments.parquet"), on="department_id")
        .select("product_id", bio=pl.col("product_name").str.contains("(?i)organic").cast(pl.Int8), frais=pl.col("department").is_in(["produce", "dairy eggs"]).cast(pl.Int8))
    )
    produit = stats_produit.join(catalogue, on="product_id")

    cible = (
        pl.scan_parquet(f"{P}/order_products__train.parquet")
        .join(commandes_train.lazy().select("order_id", "user_id"), on="order_id")
        .select("user_id", "product_id", achete=pl.lit(1, dtype=pl.Int8))
    )

    table = (
        up.join(user, on="user_id")
        .join(produit, on="product_id")
        .join(commandes_train.lazy().drop("order_id"), on="user_id")
        .join(cible, on=["user_id", "product_id"], how="left")
        .with_columns(
            achete=pl.col("achete").fill_null(0),
            up_taux=pl.col("up_nb_achats") / pl.col("nb_commandes"),
            up_commandes_depuis=(pl.col("nb_commandes") - pl.col("up_derniere")),
            user_taux_reachat=pl.col("user_taux_reachat").fill_null(0),
            prod_taux_reachat=pl.col("prod_taux_reachat").fill_null(0),
        )
    )
    # AJOUT IMPORTANT : le tri pour la reproductibilité (demandé par Haintso)
    return table.collect().sort("user_id", "product_id")

def meilleur_seuil(y, proba):
    seuils = np.arange(0.05, 0.95, 0.01)
    scores = [f1_score(y, proba >= s) for s in seuils]
    return float(seuils[np.argmax(scores)])

def evaluer(nom, y, proba, seuil):
    pred = proba >= seuil
    return {
        "modele": nom, "seuil": round(seuil, 2), "roc_auc": round(roc_auc_score(y, proba), 3),
        "pr_auc": round(average_precision_score(y, proba), 3), "f1": round(f1_score(y, pred), 3),
        "precision": round(precision_score(y, pred), 3), "rappel": round(recall_score(y, pred), 3),
    }

def main():
    SORTIE.mkdir(exist_ok=True)
    table = construire_table()
    taux = table["achete"].mean()
    print(f"{table.height:,} couples client-produit, {taux:.1%} rachetés")

    X = table.select(VARIABLES).to_pandas()
    y = table["achete"].to_numpy()
    groupes = table["user_id"].to_numpy()

    decoupe = GroupShuffleSplit(test_size=0.2, random_state=GRAINE)
    idx_app, idx_test = next(decoupe.split(X, y, groupes))
    X_app, y_app, g_app = X.iloc[idx_app], y[idx_app], groupes[idx_app]
    
    idx_ent, idx_val = next(decoupe.split(X_app, y_app, g_app))
    idx_ent, idx_val = idx_app[idx_ent], idx_app[idx_val]

    # --- NOUVEAUTÉ : Validation croisée (K-Fold) sur XGBoost demandée par le prof ---
    print("\nCalcul de la validation croisée (5-Fold)...")
    kf = GroupKFold(n_splits=5)
    xgb_cv = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, tree_method="hist", random_state=GRAINE, n_jobs=-1)
    auc_scores = []
    
    for train_idx, val_idx in kf.split(X_app, y_app, groups=g_app):
        xgb_cv.fit(X_app.iloc[train_idx], y_app[train_idx])
        preds = xgb_cv.predict_proba(X_app.iloc[val_idx])[:, 1]
        auc_scores.append(roc_auc_score(y_app[val_idx], preds))
    mean_cv_auc = np.mean(auc_scores)
    print(f"AUC moyen en validation croisée : {mean_cv_auc:.3f}")

    # --- ENTRAINEMENT BASELINE ---
    print("\nEntraînement de la Baseline...")
    mlflow.sklearn.autolog()
    baseline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    with mlflow.start_run(run_name="baseline_logreg"):
        baseline.fit(X.iloc[idx_ent], y[idx_ent])
        proba_val = baseline.predict_proba(X.iloc[idx_val])[:, 1]
        seuil = meilleur_seuil(y[idx_val], proba_val)
        proba_test = baseline.predict_proba(X.iloc[idx_test])[:, 1]
        res_baseline = evaluer("Baseline", y[idx_test], proba_test, seuil)
        mlflow.log_metrics({k: v for k, v in res_baseline.items() if isinstance(v, (int, float))})
    
    # --- ENTRAINEMENT XGBOOST ---
    print("\nEntraînement de XGBoost...")
    mlflow.xgboost.autolog(log_models=False)
    xgb = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.1, subsample=0.8,
        colsample_bytree=0.8, tree_method="hist", random_state=GRAINE, n_jobs=-1,
    )
    
    with mlflow.start_run(run_name="xgboost_modele"):
        xgb.fit(X.iloc[idx_ent], y[idx_ent])
        proba_val = xgb.predict_proba(X.iloc[idx_val])[:, 1]
        seuil = meilleur_seuil(y[idx_val], proba_val)
        proba_test = xgb.predict_proba(X.iloc[idx_test])[:, 1]
        
        # Évaluation et logs MLflow
        res_xgb = evaluer("XGBoost", y[idx_test], proba_test, seuil)
        mlflow.log_metrics({k: v for k, v in res_xgb.items() if isinstance(v, (int, float))})
        mlflow.log_metric("cv_roc_auc_moyen", mean_cv_auc) # Ajout du score CV demandé par le prof
        
        # Tracé de l'équité pour le logguer
        seuil_xgb = res_xgb["seuil"]
        proba = xgb.predict_proba(X.iloc[idx_test])[:, 1]
        test = table[idx_test].with_columns(pred=pl.Series(proba >= seuil_xgb))
        segments = pl.read_parquet(f"{P}/segments_clients.parquet")
        test = test.join(segments, on="user_id", how="left")
        vrais_positifs = pl.col("pred") & (pl.col("achete") == 1)
        equite = test.group_by("segment").agg(rappel=vrais_positifs.sum() / (pl.col("achete") == 1).sum()).sort("segment")
        for idx, row in enumerate(equite.iter_rows()):
            mlflow.log_metric(f"equite_rappel_seg_{idx}", row[1])

        # Création et sauvegarde SHAP
        echantillon = X.iloc[idx_test].sample(2_000, random_state=GRAINE)
        valeurs = shap.TreeExplainer(xgb)(echantillon)
        shap.summary_plot(valeurs, echantillon, show=False)
        plt.tight_layout()
        shap_file = SORTIE / "shap_reachat.png"
        plt.savefig(shap_file, dpi=120)
        plt.close()
        
        # Enregistrement du modèle avec signature
        info = mlflow.xgboost.log_model(
            xgb, 
            artifact_path="modele",
            registered_model_name="reachat_xgb",
            input_example=X.iloc[idx_test].head(3)
        )
        
        # ---> AJOUT DE L'EXPORT .JOBLIB <---
        Path("models").mkdir(exist_ok=True)
        joblib.dump(xgb, "models/reachat_xgb.joblib")

        # Ajout des graphiques au run
        mlflow.log_artifact(str(shap_file), artifact_path="figures")
        print("\nModèle XGBoost tracé dans MLflow et exporté en .joblib avec succès.")

    # --- PROMOTION DU CHAMPION ---
    print("\nPromotion du XGBoost en tant que Champion...")
    MlflowClient().set_registered_model_alias(
        "reachat_xgb", "champion", info.registered_model_version
    )
    print("Succès ! L'API peut désormais utiliser l'alias @champion.")

if __name__ == "__main__":
    main()