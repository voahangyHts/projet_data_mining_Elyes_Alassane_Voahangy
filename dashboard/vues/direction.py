"""Dashboard Panier Vert – page d'accueil : vue Direction.

Page affichée par dashboard/app.py aux rôles Direction et Équipe Data.
"""
from pathlib import Path

import plotly.express as px
import polars as pl
import streamlit as st

RACINE = Path(__file__).resolve().parents[2]   # dossier du projet
DONNEES = RACINE / "data" / "processed"
RAPPORTS = RACINE / "reports"

# Action marketing de chaque segment (rapport EDA du J2)
ACTIONS = {
    "Fidèles réguliers": "Programme de fidélité Premium (livraison prioritaire ou gratuite)",
    "Gros paniers bio et frais du week-end": "Notifications le vendredi soir ou le samedi matin",
    "Occasionnels petits paniers": "Coupons Fruits/Légumes et Bio pour gonfler le panier",
}

@st.cache_data  # lu une seule fois, puis gardé en mémoire
def charger():
    segments = pl.read_csv(RAPPORTS / "segments_profils.csv")
    scores = pl.read_csv(RAPPORTS / "classification_resultats.csv")
    reachat = (
        pl.scan_parquet(DONNEES / "features_reachat.parquet")
        .select(clients=pl.col("user_id").n_unique(), couples=pl.len())
        .collect()
    )
    return segments, scores, reachat


segments, scores, reachat = charger()
xgb = scores.filter(pl.col("modele") == "XGBoost").row(0, named=True)
base = scores.filter(pl.col("modele") == "Baseline").row(0, named=True)
nb_clients = segments["nb_clients"].sum()

st.title("🛒 Panier Vert · Vue Direction")
st.markdown(
    "**Ce qu'il faut retenir :** les clients se répartissent en **3 profils de taille comparable**, "
    "et le modèle repère les produits qu'un client va racheter **mieux qu'une méthode simple**. "
    "On peut donc cibler les relances au lieu de les envoyer à tout le monde."
)

# 1. Chiffres clés
c1, c2, c3, c4 = st.columns(4)
c1.metric("Clients analysés", f"{nb_clients:,}".replace(",", " "))
c2.metric("Profils de clients", f"{segments.height}")
c3.metric("Clients couverts par l'API", f"{reachat['clients'][0]:,}".replace(",", " "),
          help=f"{reachat['couples'][0]:,} couples client-produit peuvent être scorés".replace(",", " "))
c4.metric("Qualité du modèle (ROC-AUC)", f"{xgb['roc_auc']:.3f}".replace(".", ","),
          delta=f"+{xgb['roc_auc'] - base['roc_auc']:.3f} vs méthode simple".replace(".", ","),
          help="1 = parfait, 0,5 = hasard. Méthode simple : régression logistique")

# 2. Répartition des clients par profil
st.subheader("Répartition des clients par profil")
profils = segments.with_columns(part=pl.col("nb_clients") / nb_clients).sort("nb_clients")
graphique = px.bar(
    profils.to_pandas(), x="nb_clients", y="nom_segment", orientation="h",
    text=[f"{n:,} clients ({p:.1%})".replace(",", " ").replace(".", ",") for n, p in zip(profils["nb_clients"], profils["part"])],
    labels={"nb_clients": "Nombre de clients", "nom_segment": ""},
    # une seule couleur : l'information est dans le texte. #2E7D32 : contraste
    # 5,1:1 sur fond clair et 3,7:1 sur fond sombre (#1B5E20 tombait à 2,4:1
    # en thème sombre) ; texte blanc dessus : 5,1:1 (voir dashboard/ACCESSIBILITE.md)
    color_discrete_sequence=["#2E7D32"],
)
graphique.update_traces(textposition="inside", textfont_color="white",
                        hovertemplate="%{y} : %{x:,} clients<extra></extra>")
graphique.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(graphique, width="stretch")
st.caption("Résumé : trois profils de taille proche, de 32,7 % à 34,5 % des clients chacun. "
           "Source : segmentation K-means (k = 3) sur 206 209 clients Instacart.")

# 3. Profil et action pour chaque segment
st.subheader("Que faire pour chaque profil ?")
tableau = (
    segments.sort("segment")
    .select(
        pl.col("nom_segment").alias("Profil"),
        pl.col("nb_clients").alias("Clients"),
        pl.col("nb_commandes").alias("Commandes (moyenne)"),
        pl.col("delai_moyen").alias("Jours entre 2 commandes"),
        pl.col("panier_moyen").alias("Articles par panier"),
        (pl.col("part_bio") * 100).round(0).alias("Part de bio (%)"),
    )
    .with_columns(pl.col("Profil").replace_strict(ACTIONS, default="").alias("Action recommandée"))
)
st.dataframe(tableau.to_pandas(), hide_index=True, width="stretch")
st.caption("Source : reports/segments_profils.csv (pipeline DVC) · actions issues du rapport EDA du J2.")
