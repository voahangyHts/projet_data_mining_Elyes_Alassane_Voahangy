"""Prépare le modèle de réachat pour l'API BentoML, à partir du champion MLflow.

- récupère le modèle @champion du registre MLflow (celui qui a passé la quality gate)
- récupère son seuil et ses scores (métriques de son run)
- l'enregistre dans le magasin BentoML, sous le nom « reachat »
- enregistre la table des caractéristiques (data/processed/features_reachat.parquet)

Prérequis : MLflow lancé (docker compose --profile mlops up -d) et « make train » déjà fait.
Lancement : uv run python -m src.export_modele
"""
import bentoml
import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from src.classification import (
    MLFLOW_URI,
    NOM_MODELE,
    P,
    VARIABLES,
    construire_table,
)

FEATURES = f"{P}/features_reachat.parquet"
SCORES = ["seuil", "roc_auc", "pr_auc", "f1", "precision", "rappel"]


def main():
    # 1. Le champion dans le registre MLflow
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    try:
        version = client.get_model_version_by_alias(NOM_MODELE, "champion")
    except MlflowException:
        print(
            f"Aucun champion « {NOM_MODELE} » dans MLflow ({MLFLOW_URI}).\n"
            "Lancer d'abord : docker compose --profile mlops up -d, puis make train"
        )
        raise SystemExit(1)

    metriques = client.get_run(version.run_id).data.metrics
    xgb = mlflow.xgboost.load_model(f"models:/{NOM_MODELE}@champion")
    print(
        f"Champion récupéré : {NOM_MODELE} version {version.version} "
        f"(seuil {metriques['seuil']}, ROC-AUC {metriques['roc_auc']})"
    )

    # 2. Le même modèle, avec son seuil et ses scores, dans le magasin BentoML
    modele = bentoml.xgboost.save_model(
        "reachat",
        xgb,
        metadata={
            "variables": VARIABLES,
            "mlflow_modele": NOM_MODELE,
            "mlflow_version": int(version.version),
            "mlflow_run_id": version.run_id,
            **{k: float(metriques[k]) for k in SCORES if k in metriques},
        },
    )
    print("Modèle enregistré dans BentoML :", modele.tag)

    # 3. Les caractéristiques de chaque couple client-produit
    #    (même table triée que pour l'entraînement)
    table = construire_table()
    table.select("user_id", "product_id", *VARIABLES).write_parquet(FEATURES)
    print(f"{table.height:,} couples enregistrés dans {FEATURES}")


if __name__ == "__main__":
    main()
