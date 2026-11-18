"""Prépare le modèle de réachat pour l'API BentoML.

- réentraîne XGBoost avec les mêmes réglages que src/classification.py
- choisit le seuil sur la validation (F1 max), mesure le test une seule fois
- enregistre le modèle dans le magasin BentoML, sous le nom « reachat »
- enregistre la table des caractéristiques (data/processed/features_reachat.parquet)

Lancement : uv run python -m src.export_modele
"""
import bentoml
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier

from src.classification import (
    GRAINE,
    P,
    VARIABLES,
    construire_table,
    evaluer,
    meilleur_seuil,
)

FEATURES = f"{P}/features_reachat.parquet"


def main():
    table = construire_table()
    X = table.select(VARIABLES).to_pandas()
    y = table["achete"].to_numpy()
    groupes = table["user_id"].to_numpy()

    # Même découpage par client que classification.py (même graine)
    decoupe = GroupShuffleSplit(test_size=0.2, random_state=GRAINE)
    idx_app, idx_test = next(decoupe.split(X, y, groupes))
    idx_ent, idx_val = next(
        decoupe.split(X.iloc[idx_app], y[idx_app], groupes[idx_app])
    )
    idx_ent, idx_val = idx_app[idx_ent], idx_app[idx_val]

    # Mêmes réglages que dans classification.py
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
    xgb.fit(X.iloc[idx_ent], y[idx_ent])
    proba_val = xgb.predict_proba(X.iloc[idx_val])[:, 1]
    seuil = meilleur_seuil(y[idx_val], proba_val)
    proba_test = xgb.predict_proba(X.iloc[idx_test])[:, 1]
    scores = evaluer("XGBoost", y[idx_test], proba_test, seuil)
    print("Scores sur le test :", scores)

    # 1. Le modèle, avec son seuil et ses scores, dans le magasin BentoML
    modele = bentoml.xgboost.save_model(
        "reachat",
        xgb,
        metadata={
            "variables": VARIABLES,
            **{k: float(v) for k, v in scores.items() if k != "modele"},
        },
    )
    print("Modèle enregistré dans BentoML :", modele.tag)

    # 2. Les caractéristiques de chaque couple client-produit
    table.select("user_id", "product_id", *VARIABLES).write_parquet(FEATURES)
    print(f"{table.height:,} couples enregistrés dans {FEATURES}")


if __name__ == "__main__":
    main()