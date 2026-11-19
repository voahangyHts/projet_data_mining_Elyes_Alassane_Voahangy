"""API de réachat Panier Vert (BentoML).

POST /predict          {"user_id": 1, "product_id": 196}
  -> probabilité que ce client rachète ce produit à sa prochaine commande
POST /recommandations  {"user_id": 1, "n": 10}
  -> les n produits que ce client a le plus de chances de racheter

Prérequis : uv run python -m src.export_modele (modèle + caractéristiques)
Lancement : uv run bentoml serve api.service:Reachat
Documentation interactive : http://localhost:3000
"""
import bentoml
import polars as pl
from bentoml.exceptions import NotFound

FEATURES = "data/processed/features_reachat.parquet"
PRODUITS = "data/processed/products.parquet"


@bentoml.service(resources={"cpu": "1"}, traffic={"timeout": 10})
class Reachat:
    # Le modèle enregistré par src/export_modele.py (dernière version)
    bento_model = bentoml.models.get("reachat:latest")

    def __init__(self):
        self.model = bentoml.xgboost.load_model(self.bento_model)
        infos = self.bento_model.info.metadata
        self.variables = list(infos["variables"])
        self.seuil = float(infos["seuil"])
        self.features = pl.read_parquet(FEATURES)
        self.produits = pl.read_parquet(PRODUITS).select(
            "product_id", "product_name"
        )

    def _probas(self, lignes: pl.DataFrame):
        X = lignes.select(self.variables).to_pandas()
        return self.model.predict_proba(X)[:, 1]

    @bentoml.api
    def predict(self, user_id: int, product_id: int) -> dict:
        """Probabilité de réachat d'un produit par un client."""
        ligne = self.features.filter(
            (pl.col("user_id") == user_id) & (pl.col("product_id") == product_id)
        )
        if ligne.is_empty():
            raise NotFound(
                f"Couple inconnu : le client {user_id} n'a jamais acheté "
                f"le produit {product_id}, ou ne fait pas partie de l'échantillon."
            )
        proba = float(self._probas(ligne)[0])
        return {
            "user_id": user_id,
            "product_id": product_id,
            "proba_reachat": round(proba, 3),
            "recommander": proba >= self.seuil,
            "seuil": self.seuil,
        }

    @bentoml.api
    def recommandations(self, user_id: int, n: int = 10) -> list[dict]:
        """Les n produits que le client a le plus de chances de racheter."""
        lignes = self.features.filter(pl.col("user_id") == user_id)
        if lignes.is_empty():
            raise NotFound(f"Client inconnu : {user_id}")
        resultat = (
            lignes.select("product_id")
            .with_columns(
                proba_reachat=pl.Series(self._probas(lignes), dtype=pl.Float64).round(3)
            )
            .join(self.produits, on="product_id", how="left")
            .sort("proba_reachat", descending=True)
            .head(n)
            .with_columns(recommander=pl.col("proba_reachat") >= self.seuil)
        )
        return resultat.to_dicts()