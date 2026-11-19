"""Page « Équipe data » : santé du modèle de réachat.

- Champion : registre MLflow (alias @champion du modèle reachat_xgb) si le
  serveur répond, sinon reports/champion.json (référence du quality gate CI)
- Métriques : reports/classification_resultats.csv (baseline vs XGBoost)
- Dérive    : reports/drift_resume.csv (Evidently, `make drift`)
- Équité    : reports/equite_segments.csv (rappel / précision par segment)

Accessibilité : titres explicites, valeurs écrites sur les barres, statut de
dérive écrit en toutes lettres (jamais la couleur seule), unités et sources.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import altair as alt
import polars as pl
import requests
import streamlit as st

RACINE = Path(__file__).resolve().parents[2]
REPORTS = RACINE / "reports"
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
NOM_MODELE = "reachat_xgb"

# Contraste WCAG >= 3:1 (éléments graphiques) en thème clair ET sombre (fond #0E1117) :
# gris 3,9 / 4,8:1 ; vert 5,1 / 3,7:1 ; rouge 5,0 / 3,8:1
BASELINE, XGB, ALERTE = "#808080", "#2E7D32", "#D32F2F"
METRIQUES = {
    "roc_auc": "ROC-AUC",
    "pr_auc": "PR-AUC",
    "f1": "F1",
    "precision": "Précision",
    "rappel": "Rappel",
}
VARIABLES_DERIVE = {
    "days_since_prior_order": "Délai depuis la commande précédente (jours)",
    "part_rachetes": "Part de produits rachetés",
    "taille_panier": "Taille du panier (articles)",
    "order_dow": "Jour de la semaine",
    "order_hour_of_day": "Heure de commande (h)",
}


def lire_csv(nom: str) -> pl.DataFrame | None:
    chemin = REPORTS / nom
    return pl.read_csv(chemin) if chemin.exists() else None


@st.cache_data(ttl=60)
def champion_mlflow() -> dict | None:
    """Version @champion dans le registre MLflow, ou None si le serveur ne répond pas."""
    try:
        r = requests.get(
            f"{MLFLOW_URI}/api/2.0/mlflow/registered-models/alias",
            params={"name": NOM_MODELE, "alias": "champion"}, timeout=2,
        )
        r.raise_for_status()
        version = r.json()["model_version"]
        run = requests.get(
            f"{MLFLOW_URI}/api/2.0/mlflow/runs/get",
            params={"run_id": version["run_id"]}, timeout=2,
        ).json()["run"]
        metriques = {m["key"]: m["value"] for m in run["data"].get("metrics", [])}
        return {
            "version": version["version"],
            "date": datetime.fromtimestamp(int(version["creation_timestamp"]) / 1000),
            "roc_auc": metriques.get("roc_auc"),
            "pr_auc": metriques.get("pr_auc"),
        }
    except (requests.RequestException, KeyError, ValueError):
        return None


def virgule(x: float, decimales: int = 3) -> str:
    """0.834 -> « 0,834 » (virgule décimale, à la française)."""
    return f"{x:.{decimales}f}".replace(".", ",")


def pourcentage(x: float) -> str:
    return f"{x:.0%}".replace("%", " %")


# Graduations des axes avec une virgule décimale (Vega écrirait « 0.2 »)
AXE_DECIMAL = alt.Axis(labelExpr="replace(format(datum.value, '.1f'), '.', ',')")


st.title("Équipe data : santé du modèle de réachat")
st.markdown(
    "Le modèle prédit si un client va **racheter un produit** à sa prochaine "
    "commande. Cette page suit sa version en production, ses scores, la "
    "**dérive** des données et son **équité** entre segments de clients."
)

# --- 1. Version du champion -------------------------------------------------
st.header("Modèle en production (champion)")
champion = champion_mlflow()
reference_ci = json.loads((REPORTS / "champion.json").read_text(encoding="utf-8")) \
    if (REPORTS / "champion.json").exists() else None

c1, c2, c3 = st.columns(3)
if champion:
    c1.metric("Version MLflow @champion", f"v{champion['version']}")
    c2.metric("ROC-AUC du champion", virgule(champion["roc_auc"]) if champion["roc_auc"] else "n.d.")
    c3.metric("Promu le", champion["date"].strftime("%d/%m/%Y %H:%M"))
    st.caption(f"Source : registre MLflow ({MLFLOW_URI}), modèle « {NOM_MODELE} ».")
else:
    st.info(
        "Serveur MLflow injoignable ou sans champion : affichage de la référence "
        "du quality gate de la CI. Pour la version MLflow : "
        "`docker compose --profile mlops up -d` puis `make train`."
    )
if reference_ci:
    st.markdown(
        f"**Référence du quality gate CI** (`reports/champion.json`) : "
        f"{reference_ci['modele']}, {METRIQUES.get(reference_ci['metrique'], reference_ci['metrique'])} "
        f"= {virgule(reference_ci['score'])} (tolérance {virgule(reference_ci['tolerance'])}). "
        "Une pull request dont le modèle fait moins bien est refusée."
    )

# --- 2. Métriques comparées à la baseline ----------------------------------
st.header("XGBoost comparé à la baseline")
resultats = lire_csv("classification_resultats.csv")
if resultats is None:
    st.warning("`reports/classification_resultats.csv` introuvable : lancer `dvc repro`.")
else:
    resultats = resultats.with_columns(
        modele=pl.when(pl.col("modele").str.contains("(?i)xgboost"))
        .then(pl.lit("XGBoost")).otherwise(pl.lit("Baseline (régression logistique)"))
    )
    long = resultats.unpivot(
        index="modele", on=list(METRIQUES), variable_name="metrique", value_name="score"
    ).with_columns(metrique=pl.col("metrique").replace_strict(METRIQUES)).to_pandas()
    long["score_texte"] = [virgule(s) for s in long["score"]]

    base = alt.Chart(long).encode(
        y=alt.Y("modele:N", title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("score:Q", title="Score (0 à 1, plus haut = meilleur)",
                scale=alt.Scale(domain=[0, 1]), axis=AXE_DECIMAL),
    )
    barres = base.mark_bar().encode(
        color=alt.Color(
            "modele:N",
            scale=alt.Scale(domain=["Baseline (régression logistique)", "XGBoost"], range=[BASELINE, XGB]),
            legend=None,  # le nom du modèle est écrit sur l'axe
        ),
        tooltip=[alt.Tooltip("modele:N", title="Modèle"), alt.Tooltip("metrique:N", title="Métrique"),
                 alt.Tooltip("score_texte:N", title="Score")],
    )
    texte = base.mark_text(align="left", dx=4).encode(text="score_texte:N")
    st.altair_chart(
        (barres + texte).properties(height=60).facet(
            row=alt.Row("metrique:N", title=None, sort=list(METRIQUES.values()),
                        header=alt.Header(labelAngle=0, labelAlign="left", labelFontWeight="bold")),
        ).properties(
            title="Scores sur le jeu de test (clients jamais vus à l'entraînement)",
            description="Barres, scores de la baseline et de XGBoost : " + " ; ".join(
                f"{m} {mo} {s}" for m, mo, s in zip(long["metrique"], long["modele"], long["score_texte"])),
        ),
        use_container_width=True,
    )
    xgb = resultats.filter(pl.col("modele") == "XGBoost").row(0, named=True)
    base_r = resultats.filter(pl.col("modele") != "XGBoost").row(0, named=True)
    st.markdown(
        f"**Lecture :** XGBoost fait mieux que la baseline sur la PR-AUC "
        f"({virgule(xgb['pr_auc'])} contre {virgule(base_r['pr_auc'])}), la métrique "
        "retenue car seuls ~10 % des couples client-produit sont rachetés. "
        f"Seuil de décision : {virgule(xgb['seuil'], 2)} (choisi sur la validation pour maximiser le F1)."
    )
    st.caption("Source : `reports/classification_resultats.csv` (`dvc repro`, étape classification).")
    with st.expander("Voir les données du graphique"):
        st.dataframe(resultats, hide_index=True, use_container_width=True)

# --- 3. Dérive des données (Evidently) -------------------------------------
st.header("Dérive des données (Evidently)")
derive = lire_csv("drift_resume.csv")
if derive is None:
    st.warning("`reports/drift_resume.csv` introuvable : lancer `make drift`.")
else:
    derive = derive.with_columns(
        variable_lisible=pl.col("variable").replace(VARIABLES_DERIVE),
        statut=pl.when(pl.col("derive")).then(pl.lit("⚠️ Dérive détectée"))
        .otherwise(pl.lit("✓ Stable")),
    )
    nb = derive["derive"].sum()
    st.metric("Variables en dérive", f"{nb} sur {derive.height}")
    df = derive.to_pandas()
    df["etiquette"] = [f"{virgule(s)} – {t}" for s, t in zip(df["score"], df["statut"])]
    seuil = float(derive["seuil"][0])
    # ordre explicite (score décroissant) : dans un graphique à plusieurs
    # couches, Vega ignore sort="-x" et repasse en ordre alphabétique
    ordre = list(df.sort_values("score", ascending=False)["variable_lisible"])
    barres_d = alt.Chart(df).mark_bar().encode(
        x=alt.X("score:Q", title=f"Score de dérive (0 = identique ; pointillés = seuil {virgule(seuil, 1)})",
                axis=AXE_DECIMAL),
        y=alt.Y("variable_lisible:N", sort=ordre, title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("statut:N", scale=alt.Scale(
            domain=["⚠️ Dérive détectée", "✓ Stable"], range=[ALERTE, BASELINE]), legend=None),
        tooltip=[alt.Tooltip("variable_lisible:N", title="Variable"), alt.Tooltip("methode:N", title="Test"),
                 alt.Tooltip("etiquette:N", title="Score et statut")],
    )
    texte_d = alt.Chart(df).mark_text(align="left", dx=4).encode(
        x="score:Q", y=alt.Y("variable_lisible:N", sort=ordre), text="etiquette:N",
    )
    regle = alt.Chart(df.head(1)).mark_rule(strokeDash=[6, 4], size=2).encode(x="seuil:Q")
    st.altair_chart(
        (barres_d + texte_d + regle).properties(
            title="Historique des commandes (référence) vs dernière commande de chaque client",
            height=alt.Step(34),
            description="Barres, score de dérive par variable : " + " ; ".join(
                f"{v} {e}" for v, e in zip(df["variable_lisible"], df["etiquette"])),
        ),
        use_container_width=True,
    )
    for ligne in derive.filter(pl.col("derive")).iter_rows(named=True):
        evolution = ""
        if ligne["moyenne_reference"] is not None:
            evolution = (f" : moyenne passée de {virgule(ligne['moyenne_reference'], 1)} "
                         f"à {virgule(ligne['moyenne_courant'], 1)}")
        st.markdown(f"**⚠️ {ligne['variable_lisible']}**{evolution}.")
    st.markdown(
        "**Lecture :** les habitudes d'achat (heure, jour, panier, réachat) sont stables ; "
        "seul le délai entre deux commandes change. C'est probablement un effet de la "
        "construction du jeu Instacart (la commande courante est la dernière de chaque "
        "client) : à surveiller, sans réentraîner le modèle pour l'instant."
    )
    st.caption(
        "Source : Evidently 0.7, 50 000 commandes tirées au hasard dans chaque jeu "
        "(`reports/drift_resume.csv`, rapport complet : `reports/drift_report.html`). "
        "Tests : Wasserstein (variables numériques), Jensen-Shannon (jour)."
    )
    with st.expander("Voir les données du graphique"):
        st.dataframe(
            derive.select("variable_lisible", "methode", "score", "seuil", "statut",
                          "moyenne_reference", "moyenne_courant"),
            column_config={
                "variable_lisible": "Variable", "methode": "Test", "score": "Score",
                "seuil": "Seuil", "statut": "Statut",
                "moyenne_reference": "Moyenne (référence)", "moyenne_courant": "Moyenne (courant)",
            },
            hide_index=True, use_container_width=True,
        )

# --- 4. Équité par segment --------------------------------------------------
st.header("Équité du modèle entre segments de clients")
equite = lire_csv("equite_segments.csv")
if equite is None:
    st.warning("`reports/equite_segments.csv` introuvable : lancer `dvc repro`.")
else:
    equite = equite.with_columns(
        segment_lisible=pl.format("{} – {}", pl.col("segment"), pl.col("nom_segment"))
    )
    long_e = equite.unpivot(
        index="segment_lisible", on=["rappel", "precision"],
        variable_name="indicateur", value_name="valeur",
    ).with_columns(indicateur=pl.col("indicateur").replace_strict(
        {"rappel": "Rappel (réachats bien détectés)", "precision": "Précision (alertes justes)"}
    )).to_pandas()
    long_e["valeur_texte"] = [pourcentage(v) for v in long_e["valeur"]]
    base_e = alt.Chart(long_e).encode(
        y=alt.Y("segment_lisible:N", title=None, axis=alt.Axis(labelLimit=340)),
        x=alt.X("valeur:Q", title="Part (0 à 1)", scale=alt.Scale(domain=[0, 1]), axis=AXE_DECIMAL),
        tooltip=[alt.Tooltip("segment_lisible:N", title="Segment"),
                 alt.Tooltip("indicateur:N", title="Indicateur"),
                 alt.Tooltip("valeur_texte:N", title="Valeur")],
    )
    st.altair_chart(
        (base_e.mark_bar(color=XGB) + base_e.mark_text(align="left", dx=4).encode(
            text="valeur_texte:N"))
        .properties(height=alt.Step(30))
        .facet(row=alt.Row("indicateur:N", title=None,
                           header=alt.Header(labelAngle=0, labelAlign="left", labelFontWeight="bold")))
        .properties(
            title="XGBoost sur le jeu de test, par segment",
            description="Barres, rappel et précision par segment : " + " ; ".join(
                f"{s} {i} {v}" for s, i, v in zip(long_e["segment_lisible"], long_e["indicateur"], long_e["valeur_texte"])),
        ),
        use_container_width=True,
    )
    ecart = equite["rappel"].max() - equite["rappel"].min()
    meilleur = equite.sort("rappel", descending=True).row(0, named=True)
    moins_bon = equite.sort("rappel").row(0, named=True)
    st.markdown(
        f"**Lecture :** le modèle détecte {virgule(meilleur['rappel'] * 100, 0)} % des réachats "
        f"pour « {meilleur['nom_segment']} » contre {virgule(moins_bon['rappel'] * 100, 0)} % "
        f"pour « {moins_bon['nom_segment']} », soit un écart de {virgule(ecart * 100, 0)} points. "
        "Hypothèse : un client qui commande rarement laisse moins d'historique au modèle. "
        "À garder en tête avant d'utiliser le modèle pour des offres ciblées, pour ne pas "
        "défavoriser un segment."
    )
    st.caption("Source : `reports/equite_segments.csv` (`dvc repro`, étape classification).")
    with st.expander("Voir les données du graphique"):
        st.dataframe(
            equite.select("segment", "nom_segment", "nb_couples", "taux_reachat_reel", "rappel", "precision"),
            column_config={
                "segment": "Segment", "nom_segment": "Nom",
                "nb_couples": st.column_config.NumberColumn("Couples client-produit testés"),
                "taux_reachat_reel": st.column_config.NumberColumn("Taux de réachat réel", format="percent"),
                "rappel": st.column_config.NumberColumn("Rappel", format="percent"),
                "precision": st.column_config.NumberColumn("Précision", format="percent"),
            },
            hide_index=True, use_container_width=True,
        )
