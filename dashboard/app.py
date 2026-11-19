"""Dashboard Panier Vert : écran de connexion, puis pages selon le rôle.

Lancement : make dashboard (l'API doit tourner : make api)
Comptes   : variables DASHBOARD_COMPTE_* du fichier .env (voir .env.example)
Nouveau compte : uv run python -m dashboard.auth <identifiant> <role>

Aucune page n'est chargée sans connexion valide : les pages sont dans dashboard/vues/
(et non pages/, que Streamlit afficherait automatiquement) et seul ce fichier les ouvre.
"""
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from auth import ROLES, charger_comptes, verifier

ICI = Path(__file__).resolve().parent
load_dotenv(ICI.parent / ".env")

# Page, titre, icône, rôles autorisés (minimisation : chaque rôle ne voit que ce qui lui sert)
PAGES = [
    ("vues/direction.py", "Direction", "📊", {"direction", "data"}),
    ("vues/marketing_crm.py", "Marketing CRM", "🎯", {"metier", "data"}),
    ("vues/qualite_catalogue.py", "Qualité catalogue", "🧪", {"metier", "data"}),
    ("vues/equipe_data.py", "Équipe data", "🛠️", {"data"}),
]

st.set_page_config(page_title="Panier Vert", page_icon="🛒", layout="wide")


def ecran_connexion():
    st.title("🛒 Panier Vert · Connexion")
    comptes = charger_comptes()
    if not comptes:
        st.error("Aucun compte n'est configuré. Ajoutez les lignes DASHBOARD_COMPTE_* "
                 "dans le fichier .env (voir .env.example).")
        return
    with st.form("connexion"):
        identifiant = st.text_input("Identifiant")
        mot_de_passe = st.text_input("Mot de passe", type="password")
        valider = st.form_submit_button("Se connecter")
    if valider:
        compte = comptes.get(identifiant.strip().lower())
        if compte and verifier(mot_de_passe, compte["empreinte"]):
            st.session_state.utilisateur = identifiant.strip().lower()
            st.session_state.role = compte["role"]
            st.rerun()
        time.sleep(1)  # ralentit les essais de mots de passe en série
        st.error("Identifiant ou mot de passe incorrect.")


if "role" not in st.session_state:
    # Non connecté : la seule page qui existe est l'écran de connexion
    st.navigation([st.Page(ecran_connexion, title="Connexion", icon="🔒")], position="hidden").run()
    st.stop()

 PAN-finitions-dashboard
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
st.plotly_chart(graphique, use_container_width=True)
st.caption("Résumé : trois profils de taille proche, de 32,7 % à 34,5 % des clients chacun. "
           "Source : segmentation K-means (k = 3) sur 206 209 clients Instacart.")

role = st.session_state.role
pages = [
    st.Page(ICI / fichier, title=titre, icon=icone)
    for fichier, titre, icone, roles in PAGES
    if role in roles and (ICI / fichier).exists()
]
with st.sidebar:
    st.markdown(f"Connecté : **{st.session_state.utilisateur}**  \nRôle : {ROLES[role]}")
    if st.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()
 main

st.navigation(pages).run()
