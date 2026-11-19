# Plan du Dossier Écrit MSPR 5.1 — Projet Panier Vert

- **Certification :** RNCP 40167 · Bloc 5 · Activité 14 (Compétences B5C1, B5C6, B5C8)
- **Format :** 30 pages hors annexes (remise PDF individuelle le **12/02/2027**, code figé au tag `v1.0`, soutenance le **15/02/2027**)
- **Équipe :** Elyes (Chef de projet / Data Scientist), Voahangy (Data Engineer / MLOps & API), Alassane (MLOps / Qualité & Gouvernance)

---

## Structure détaillée (30 pages hors annexes)

| Partie | Titre de la section | Pages | Contenu attendu | Preuves déjà disponibles & à produire | Échéance | Responsable |
| :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| — | **Page de garde** | 1 | Intitulé officiel « Mise en situation professionnelle reconstituée · Data Mining », projet Panier Vert, équipe et rôles, date, version | Charte graphique équipe, dépôt Git tag `v1.0` | P5 | **Tous** (individuel) |
| — | **Sommaire et synthèse** | 2 | Sommaire automatique paginé, liste des figures et tableaux, synthèse exécutive d'une page (réponse SCQA) | `docs/storytelling_scqa.md`, résultats clés J2–J4 | P5 | **Elyes** |
| **1** | **Cadrage et spécifications fonctionnelles** | 3 | Contexte Panier Vert (42 épiceries bio), besoin métier, acteurs (Direction, CRM, Qualité, Data), cas d'usage, user stories (MoSCoW), règles de gestion, KPI, maquettes, matrice des rôles (IDs `EF-01`...) | Note de cadrage J1, maquettes dashboard, grille des rôles | J1 | **Elyes** |
| **2** | **Cadre réglementaire du projet** | 2 | Conformité RGPD (pseudonymisation `user_id`, minimisation, base légale, durée de conservation), AI Act (règlement UE 2024/1689), licences et CGU (`robots.txt`, attribution ODbL Open Food Facts, licence ouverte RappelConso), hébergement UE | `.env.example` (secrets hors Git), documentation conformité, analyse des risques | J1 → P5 | **Alassane** |
| **3** | **Spécifications techniques** | 2 | Architecture médaillon (Bronze `data/raw/`, Silver & Gold `data/processed/`), flux de données, modèle de données, contrat d'API BentoML (`/predict`, `/recommandations`), exigences non fonctionnelles (`ENF-01`...) | Section médaillon du `README.md`, `api/service.py`, `bentofile.yaml`, `docker-compose.yml` | J1, J3 | **Voahangy** |
| **4** | **Choix des outils et justification** | 2 | Matrice d'arbitrage (Besoin / Outil retenu / Alternatives étudiées / Justification : Parquet-Polars vs CSV-pandas, Pandera vs Great Expectations, XGBoost-SHAP vs LightGBM/RF, DVC-MLflow, BentoML-Docker vs FastAPI, Streamlit-Plotly vs Dash/Power BI) | `pyproject.toml`, `uv.lock`, justification de stack | J1 → J3 | **Voahangy** |
| **5** | **Collecte** | 3 | Intégration des 4 sources (Instacart 3,42 M commandes, Open Food Facts 61,4 % trouvés sur 10 217 codes, RappelConso 14 548 rappels, mercuriales RNM), gestion rate limiting, retries, logs, contrôles qualité Pandera | `src/prepare.py`, `src/rappels_enrichis.py`, `src/schemas.py`, `src/upload_lake.py` (RustFS), rapport qualité | J1, P1 | **Voahangy** |
| **6** | **Analyse et mining** | 4 | EDA et validation d'hypothèses, clustering K-means (k=3 segments nommés), règles d'association FP-Growth (lift, confiance), classification réachat (XGBoost ROC-AUC 0,834 / CV 5-fold 0,832 vs Baseline 0,824, seuil 0,22), interprétabilité SHAP, contrôle d'équité | `Rapport_EDA_Panier_Vert_J2.pdf`, `src/clustering.py`, `src/rules.py`, `src/classification.py`, `reports/shap_reachat.png`, `reports/segments_profils.csv` | J2, P2 | **Elyes** |
| **7** | **Industrialisation** | 3 | Tracking MLflow (3 expériences, 4 modèles, registre `@champion` v4), pipeline DVC (8 étapes, remote OneDrive), CI GitHub Actions (26 tests + quality gates ROC-AUC & PR-AUC), serving BentoML/Docker, surveillance de dérive Evidently | `dvc.yaml`, `dvc.lock`, `.github/workflows/ci.yml`, `src/quality_gate.py`, `src/export_modele.py`, `src/drift.py`, `reports/drift_report.html` | J3, P3 | **Alassane & Voahangy** |
| **8** | **Restitution** | 2 | Récit décisionnel SCQA adapté aux 4 publics, présentation du dashboard Streamlit multi-vues, conformité accessibilité (WCAG 2.2 / RGAA 4.1), éthique et transparence (SHAP, humain dans la boucle), tests utilisateurs et conduite du changement | `dashboard/app.py`, `dashboard/pages/`, captures d'écran dashboard v1/v2, `docs/storytelling_scqa.md` | J4, P4 | **Elyes** |
| **9** | **Gestion de projet** | 2 | Démarche Agile (Scrum allégé en 5 sprints P1–P5 de 2 semaines), rituels, pilotage Jira, workflow Git (branches par ticket, PR relues, tags jalons `j1-collecte` à `v1.0`), répartition des rôles | Board Jira, historique des PR GitHub, `docs/feuille_de_route.md`, comptes rendus de sprint | J1 → P5 | **Alassane** |
| **10** | **Bilan et retour d'expérience** | 2 | Analyse de 3 à 5 difficultés réelles (cause, impact, solution : tri Polars, numérotation segments, compatibilité Evidently/pandas 3, conflits `uv.lock`, CRLF Windows), limites du système, perspectives, rétrospectives et bilan individuel | `docs/journal_de_bord.md`, section 7 du résumé J3, rétrospectives P1–P5 | P5 | **Tous** (bilan perso) |
| — | **Sources bibliographiques** | 1 | Références citées dans le texte au format APA ou ISO 690 (documentations techniques, articles scientifiques, licences Open Food Facts / Instacart / RappelConso, textes RGPD et AI Act) | Liste structurée des références | Continu | **Tous** |
| — | **Glossaire** | 1 | Définition claire de 20 à 30 termes techniques pour un lecteur métier (RFM, lift, confiance, support, SHAP, ROC-AUC, PR-AUC, dérive/drift, Wasserstein, MLOps, DVC, ODbL...) | Glossaire alphabétique | Continu | **Elyes** |
| — | **Annexes** | *Hors 30 p.* | Dictionnaire de données complet, rapports qualité Pandera, comptes rendus de sprint, captures d'écran détaillées, extraits de code clés | Renvois explicites vers le dépôt Git au tag `v1.0` | P5 | **Tous** |

---

## Règles de rédaction pour l'intersession (P1 → P5)

1. **Socle commun vs Exemplaire individuel :** Les preuves techniques, schémas, métriques et captures sont communs à l'équipe, mais chaque membre remet un **dossier écrit individuel** mettant en valeur sa contribution personnelle et son retour d'expérience (Partie 10).
2. **Traçabilité des exigences :** Chaque exigence fonctionnelle (`EF-xx`) et non fonctionnelle (`ENF-xx`) définie en Partie 1 et 3 est reliée aux tickets Jira et aux tests automatisés.
3. **Remplissage au fil de l'eau :** Chaque fin de palier (P1 à P5) alimente directement les sections correspondantes afin d'éviter la rédaction dans l'urgence lors du gel en P5.
