"""Page Marketing / CRM : quels produits proposer à un client, et pourquoi.

Le dashboard ne recalcule rien : il interroge l'API de réachat du J3
(lancer d'abord : make api, ou l'image Docker sur le port 3000).
"""
import os
from pathlib import Path

import polars as pl
import requests
import streamlit as st

RACINE = Path(__file__).resolve().parent.parent.parent
DONNEES = RACINE / "data" / "processed"
API = os.getenv("API_REACHAT", "http://localhost:3000")

ACTIONS = {
    "Fidèles réguliers": "Programme de fidélité Premium (livraison prioritaire ou gratuite)",
    "Gros paniers bio et frais du week-end": "Notifications le vendredi soir ou le samedi matin",
    "Occasionnels petits paniers": "Coupons Fruits/Légumes et Bio pour gonfler le panier",
}

st.set_page_config(page_title="Panier Vert · Marketing / CRM", page_icon="🛒", layout="wide")


@st.cache_data
def charger():
    segments = pl.read_parquet(DONNEES / "segments_clients.parquet")
    # Variables qui expliquent le score (les plus importantes selon SHAP)
    historique = pl.read_parquet(
        DONNEES / "features_reachat.parquet",
        columns=["user_id", "product_id", "up_nb_achats", "up_commandes_depuis", "up_taux"],
    )
    return segments, historique


@st.cache_data(ttl=60)  # une même question n'est envoyée à l'API qu'une fois par minute
def recommandations(user_id: int, n: int):
    reponse = requests.post(f"{API}/recommandations", json={"user_id": user_id, "n": n}, timeout=10)
    if reponse.status_code == 404:
        return None
    reponse.raise_for_status()
    return reponse.json()


segments, historique = charger()

st.title("🎯 Marketing / CRM · Quels produits proposer à un client ?")
st.markdown(
    "Choisissez un client : l'API du modèle renvoie les produits qu'il a le plus de chances "
    "de **racheter à sa prochaine commande**, avec la raison. "
    "**Le score aide à décider, il ne décide pas** : l'action reste humaine."
)

col1, col2 = st.columns([1, 1])
user_id = col1.number_input("Numéro du client", min_value=1, value=23, step=1,
                            help="Seuls les clients de l'échantillon d'entraînement sont connus de l'API")
n = col2.slider("Nombre de produits à afficher", min_value=3, max_value=20, value=10)

# 1. Profil du client
profil = segments.filter(pl.col("user_id") == user_id)
if profil.height:
    nom = profil["nom_segment"][0]
    st.info(f"**Profil du client {user_id} : {nom}.** Action conseillée : {ACTIONS.get(nom, '–')}.")

# 2. Appel de l'API
try:
    resultats = recommandations(int(user_id), int(n))
except requests.exceptions.ConnectionError:
    st.error(f"L'API ne répond pas à l'adresse {API}. Lancez-la d'abord : `make api` "
             "(ou `docker run --rm -p 3000:3000 reachat:latest`).")
    st.stop()

if resultats is None:
    st.warning(f"Client {user_id} inconnu de l'API : il ne fait pas partie de l'échantillon "
               "d'entraînement. Essayez par exemple le client 23. Aucune prédiction n'est inventée.")
    st.stop()

# 3. Tableau des produits, avec la raison du score
tableau = (
    pl.DataFrame(resultats)
    .join(historique.filter(pl.col("user_id") == user_id), on="product_id", how="left")
    .select(
        pl.col("product_name").alias("Produit"),
        (pl.col("proba_reachat") * 100).round(1).alias("Probabilité de rachat (%)"),
        pl.when(pl.col("recommander")).then(pl.lit("✔ Oui")).otherwise(pl.lit("Non")).alias("À proposer ?"),
        pl.format("acheté {} fois, dernier achat il y a {} commande(s)",
                  pl.col("up_nb_achats"), pl.col("up_commandes_depuis")).alias("Pourquoi ce score"),
    )
)
a_proposer = tableau.filter(pl.col("À proposer ?") == "✔ Oui").height
st.subheader(f"{a_proposer} produit(s) à proposer au client {user_id}")
st.dataframe(
    tableau.to_pandas(), hide_index=True, use_container_width=True,
    column_config={"Probabilité de rachat (%)": st.column_config.ProgressColumn(
        "Probabilité de rachat (%)", min_value=0, max_value=100, format="%.1f %%")},
)
st.caption("« À proposer » = probabilité au moins égale au seuil du modèle (22 %, choisi pour équilibrer "
            "précision et rappel). La raison reprend les variables les plus influentes selon l'analyse SHAP : "
            "nombre d'achats du produit et commandes écoulées depuis le dernier achat. "
            f"Source : API de réachat ({API}), modèle champion MLflow.")

st.download_button("⬇️ Exporter la liste (CSV)", tableau.write_csv(),
                   file_name=f"recommandations_client_{user_id}.csv", mime="text/csv")
