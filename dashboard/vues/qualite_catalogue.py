"""Page « Qualité catalogue » : produits rappelés, enrichis par Open Food Facts.

Données : data/processed/rappels_enrichis.parquet (table or, `make enrichir`).
Une ligne = un produit rappelé (un rappel peut viser plusieurs codes-barres).

Accessibilité : chaque graphique a un titre explicite, ses valeurs écrites sur
les barres (l'information ne passe jamais par la couleur seule), ses unités,
sa source et un tableau de données équivalent.
"""
from pathlib import Path

import altair as alt
import polars as pl
import streamlit as st

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "data/processed/rappels_enrichis.parquet"

# Couleurs officielles du Nutri-Score ; la lettre est toujours écrite à côté
NUTRISCORE_COULEURS = {
    "A": "#038141", "B": "#85BB2F", "C": "#FECB02", "D": "#EE8100", "E": "#E63E11",
}
# Contraste WCAG >= 3:1 (éléments graphiques) en thème clair ET sombre :
# vert 5,1:1 sur blanc et 3,7:1 sur le fond sombre de Streamlit
VERT = "#2E7D32"
# Contour des barres Nutri-Score : les couleurs officielles B, C, D sont trop
# pâles sur fond blanc (1,5 à 2,7:1) ; ce gris fait 4,5:1 (clair) et 4,2:1 (sombre)
CONTOUR = "#767676"
SOURCE = (
    "Sources : RappelConso (DGAL / DGCCRF, Licence Ouverte Etalab 2.0) et "
    "Open Food Facts (ODbL), jointure par code-barres."
)


@st.cache_data
def charger() -> pl.DataFrame:
    return pl.read_parquet(FICHIER).with_columns(
        annee=pl.col("date_publication").dt.year(),
        nutriscore=pl.col("nutriscore").str.to_uppercase(),
    )


def pourcentage(x: float) -> str:
    """0.634 -> « 63 % » (espace insécable avant %, à la française)."""
    return f"{x:.0%}".replace("%", " %")


def nombre(n: int) -> str:
    """14548 -> « 14 548 » (espace fine insécable entre les milliers)."""
    return f"{n:,}".replace(",", " ")


# Axes en chiffres simples (Vega écrirait « 1,000 » à l'anglaise)
AXE_ENTIER = alt.Axis(format="d")
AXE_POURCENT = alt.Axis(labelExpr="replace(format(datum.value, '.0%'), '%', ' %')")


st.title("Qualité catalogue : produits rappelés")
st.markdown(
    "Quels types de produits sont le plus souvent rappelés, et quelle est la "
    "qualité nutritionnelle des produits rappelés ? Ces données aident à "
    "**prioriser les contrôles qualité** du catalogue Panier Vert."
)

if not FICHIER.exists():
    st.error(
        "Table des rappels enrichis introuvable. Lancer `dvc pull` puis "
        "`make enrichir` depuis la racine du projet."
    )
    st.stop()

rappels = charger()

# --- Filtre : période de publication ---------------------------------------
annee_min, annee_max = int(rappels["annee"].min()), int(rappels["annee"].max())
debut, fin = st.slider(
    "Années de publication des rappels",
    min_value=annee_min, max_value=annee_max, value=(annee_min, annee_max),
)
choix = rappels.filter(pl.col("annee").is_between(debut, fin))
if choix.is_empty():
    st.warning("Aucun rappel sur cette période.")
    st.stop()

# --- Chiffres clés -----------------------------------------------------------
notes = choix.filter(pl.col("nutriscore").is_not_null())
part_de = notes["nutriscore"].is_in(["D", "E"]).mean() if notes.height else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Produits rappelés", nombre(choix.height))
c2.metric("Rappels distincts", nombre(choix["id"].n_unique()))
c3.metric("Retrouvés dans Open Food Facts", pourcentage(choix["trouve_off"].mean()))
c4.metric(
    "Nutri-Score D ou E",
    pourcentage(part_de) if part_de is not None else "n.d.",
    help="Parmi les produits rappelés dont le Nutri-Score est connu.",
)

# --- 1. Rappels par catégorie (barres triées) ------------------------------
st.header("Produits rappelés par catégorie")
par_categorie = (
    choix.group_by("sous_categorie_produit")
    .agg(
        nb_produits=pl.len(),
        part_enrichie=pl.col("trouve_off").mean().round(3),
    )
    .sort("nb_produits", descending=True)
    .rename({"sous_categorie_produit": "categorie"})
)
nb_max = par_categorie.height
nb_affiche = st.slider(
    "Nombre de catégories affichées", min_value=5, max_value=nb_max,
    value=min(12, nb_max),
)
top = par_categorie.head(nb_affiche).to_pandas()
top["nb_texte"] = [nombre(n) for n in top["nb_produits"]]
top["part_texte"] = [pourcentage(p) for p in top["part_enrichie"]]
# ordre explicite (le plus rappelé en haut) : sûr même avec plusieurs couches
ordre = list(top["categorie"])

barres = alt.Chart(top).mark_bar(color=VERT).encode(
    x=alt.X("nb_produits:Q", title="Nombre de produits rappelés", axis=AXE_ENTIER),
    y=alt.Y("categorie:N", sort=ordre, title=None, axis=alt.Axis(labelLimit=320)),
    tooltip=[
        alt.Tooltip("categorie:N", title="Catégorie"),
        alt.Tooltip("nb_texte:N", title="Produits rappelés"),
        alt.Tooltip("part_texte:N", title="Retrouvés dans Open Food Facts"),
    ],
)
etiquettes = barres.mark_text(align="left", dx=4).encode(text="nb_texte:N")
st.altair_chart(
    (barres + etiquettes).properties(
        title=f"Les {nb_affiche} catégories les plus rappelées ({debut}–{fin})",
        height=alt.Step(26),
        # texte lu par les lecteurs d'écran (aria-label du graphique)
        description="Barres horizontales, nombre de produits rappelés par catégorie : "
        + " ; ".join(f"{c} {n}" for c, n in zip(top["categorie"], top["nb_texte"])),
    ),
    width="stretch",
)
tete = par_categorie.row(0, named=True)
st.markdown(
    f"**Lecture :** « {tete['categorie']} » est la catégorie la plus rappelée "
    f"({nombre(tete['nb_produits'])} produits, soit {pourcentage(tete['nb_produits'] / choix.height)} "
    "du total)."
)
st.caption(SOURCE + " Un rappel peut viser plusieurs codes-barres : on compte des produits.")
with st.expander("Voir les données du graphique"):
    st.dataframe(
        par_categorie,
        column_config={
            "categorie": "Catégorie",
            "nb_produits": st.column_config.NumberColumn("Produits rappelés"),
            "part_enrichie": st.column_config.NumberColumn(
                "Part retrouvée dans Open Food Facts", format="percent"
            ),
        },
        hide_index=True,
        width="stretch",
    )

# --- 2. Nutri-Score des produits rappelés ----------------------------------
st.header("Nutri-Score des produits rappelés")
if notes.is_empty():
    st.info("Aucun produit rappelé avec un Nutri-Score connu sur cette période.")
else:
    repartition = (
        notes.group_by("nutriscore").agg(nb_produits=pl.len())
        .with_columns(part=(pl.col("nb_produits") / pl.col("nb_produits").sum()).round(3))
        .sort("nutriscore")
    )
    df = repartition.to_pandas()
    df["etiquette"] = [
        f"{pourcentage(p)} ({nombre(n)})" for p, n in zip(df["part"], df["nb_produits"])
    ]
    df["nb_texte"] = [nombre(n) for n in df["nb_produits"]]
    barres_ns = alt.Chart(df).mark_bar(stroke=CONTOUR, strokeWidth=1.5).encode(
        x=alt.X("nutriscore:N", title="Nutri-Score (A = meilleur, E = moins bon)",
                sort=list(NUTRISCORE_COULEURS), axis=alt.Axis(labelAngle=0)),
        y=alt.Y("part:Q", title="Part des produits rappelés notés (%)",
                axis=AXE_POURCENT),
        color=alt.Color(
            "nutriscore:N",
            scale=alt.Scale(domain=list(NUTRISCORE_COULEURS),
                            range=list(NUTRISCORE_COULEURS.values())),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("nutriscore:N", title="Nutri-Score"),
            alt.Tooltip("nb_texte:N", title="Produits"),
            alt.Tooltip("etiquette:N", title="Part (nombre)"),
        ],
    )
    # étiquettes sans couleur imposée : le thème Streamlit les rend lisibles
    # en mode clair comme en mode sombre
    texte_ns = alt.Chart(df).mark_text(dy=-8).encode(
        x=alt.X("nutriscore:N", sort=list(NUTRISCORE_COULEURS)),
        y="part:Q",
        text="etiquette:N",
    )
    st.altair_chart(
        (barres_ns + texte_ns).properties(
            title=f"Répartition des {nombre(notes.height)} produits rappelés notés ({debut}–{fin})",
            height=320,
            description="Barres, part des produits rappelés par Nutri-Score : "
            + " ; ".join(f"{l} {e}" for l, e in zip(df["nutriscore"], df["etiquette"])),
        ),
        width="stretch",
    )
    sans_note = choix.height - notes.height
    st.markdown(
        f"**Lecture :** {pourcentage(part_de)} des produits rappelés notés sont "
        "classés **D ou E**, les deux moins bonnes notes nutritionnelles. "
        f"Attention : {nombre(sans_note)} produits rappelés ({pourcentage(sans_note / choix.height)}) "
        "n'ont pas de Nutri-Score connu (absents d'Open Food Facts ou fiche incomplète) ; "
        "ils ne sont pas comptés ici."
    )
    st.caption(SOURCE)
    with st.expander("Voir les données du graphique"):
        st.dataframe(
            repartition,
            column_config={
                "nutriscore": "Nutri-Score",
                "nb_produits": st.column_config.NumberColumn("Produits rappelés"),
                "part": st.column_config.NumberColumn("Part", format="percent"),
            },
            hide_index=True,
            width="stretch",
        )
