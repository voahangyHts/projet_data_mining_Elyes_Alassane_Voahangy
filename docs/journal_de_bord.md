# Journal de Bord — Projet Panier Vert

- **Équipe :** Elyes (Chef de projet / Data Scientist), Voahangy (Data Engineer / MLOps & API), Alassane (MLOps / Qualité & Gouvernance)
- **Dépôt Git :** `voahangyHts/projet_data_mining_Elyes_Alassane_Voahangy`
- **Objectif :** Chaîne décisionnelle complète de la collecte au tableau de bord (Soutenance J5 le 15/02/2027)

---

## Journal des ateliers (J1 à J4)

### J1 — Lundi 16/11/2026 : Cadrage & Collecte (`tag: j1-collecte`)
- **Livrables produits :** Note de cadrage (besoin métier Panier Vert, 42 épiceries bio, KPI, matrice des rôles), schéma d'architecture globale, pipeline de collecte v1 reproductible (`src/prepare.py`) et jeux bruts convertis au format Parquet.
- **Décisions clés :** Choix de Polars et Parquet pour traiter efficacement les 3,42 millions de commandes Instacart ; sélection de 4 sources (Instacart, Open Food Facts sous licence ODbL, RappelConso, mercuriales RNM).
- **Difficultés & solutions :** Gestion des valeurs manquantes sur `days_since_prior_order` (conservées car correspondant aux premières commandes clients) et validation de l'intégrité référentielle entre les 6 tables.

### J2 — Mardi 17/11/2026 : Préparation & Mining (`tag: j2-mining`)
- **Livrables produits :** Rapport EDA (`Rapport_EDA_Panier_Vert_J2.pdf`), segmentation clients K-means (`src/clustering.py`), règles d'association FP-Growth (`src/rules.py`), modèle de prédiction du réachat (`src/classification.py`) et graphiques SHAP (`reports/shap_reachat.png`).
- **Décisions clés :** Retenir $k=3$ segments clients (plus parlants pour le métier que $k=2$), utiliser un découpage groupé par `user_id` (`GroupShuffleSplit`) pour éviter toute fuite de données, et calibrer le seuil de classification sur la validation (F1 maximal à 0,22).
- **Difficultés & solutions :** Déséquilibre de classe (9,8 % de rachats sur 1,94 M de couples) résolu par l'optimisation du seuil décisionnel et le suivi du PR-AUC en complément du ROC-AUC.

### J3 — Mercredi 18/11 & Jeudi matin 19/11/2026 : Industrialisation MLOps (`tag: j3-mlops`)
- **Livrables produits :**
  - Data lake local RustFS Dockerisé avec couches Bronze/Silver/Gold (`docker-compose.yml`, `src/upload_lake.py`).
  - Table Gold des rappels alimentaires enrichis Open Food Facts (`src/rappels_enrichis.py` : 14 548 rappels, 63 % en Nutri-Score D/E).
  - Tracking MLflow sur 3 expériences et 4 modèles, promotion automatique `@champion` (`reachat_xgb` v4, ROC-AUC 0,834, validation croisée 5-fold 0,832).
  - Pipeline DVC complet en 8 étapes (`dvc.yaml`, `dvc.lock`) relié au remote OneDrive.
  - Intégration continue GitHub Actions (`.github/workflows/ci.yml`, 26 tests verts + 2 quality gates ROC-AUC et PR-AUC).
  - API BentoML conteneurisée Docker (`api/service.py`, `bentofile.yaml`) servant `/predict` et `/recommandations` sur le port `3000` (latence 25 à 190 ms).
  - Rapport de surveillance de dérive Evidently (`src/drift.py`, `reports/drift_report.html`).
- **Difficultés réelles rencontrées & solutions apportées :**
  1. *Instabilité du seuil (0,24 / 0,23 / 0,22) :* Ordre aléatoire des lignes Polars après `group_by`/`join` → résolu par `.sort("user_id", "product_id")`.
  2. *Inversion des numéros de segments :* K-means attribuait des IDs arbitraires → résolu par une numérotation déterministe croissante (`numeroter_segments()`) + nommage automatique.
  3. *Crash d'Evidently 0.7 avec pandas 3 :* Exécution isolée dans un environnement dédié avec pandas 2 (`uv run --no-project`).
  4. *Fins de ligne CRLF sous Windows bloquant `dvc status` :* Ajout d'un fichier `.gitattributes` imposant `LF` sur les fichiers suivis par DVC.
  5. *Conflits `uv.lock` et artefacts MLflow poussés par erreur (PR #10) :* Fermeture propre de la PR #10, mise à jour du `.gitignore` (`mlartifacts/`, `mlflow.db`) et recalcul propre de `uv.lock` sur `main`.

### J4 — Jeudi 19/11/2026 : Storytelling, Restitution & Lancement Agile (`tag: j4-restitution`)
- **Livrables produits :**
  - Dashboard interactif Streamlit multi-publics (`dashboard/app.py` et `dashboard/pages/`) branché sur l'API BentoML (`localhost:3000`) et conforme aux règles d'accessibilité WCAG 2.2 / RGAA 4.1.
  - Récit décisionnel SCQA (`docs/storytelling_scqa.md`) adapté aux 4 audiences.
  - Plan détaillé du dossier écrit MSPR 5.1 en 10 parties (`docs/plan_dossier_MSPR.md`).
  - Feuille de route de l'intersession (`docs/feuille_de_route.md`) et structuration des 5 sprints P1–P5 dans Jira.
- **Décisions clés :** Le dashboard ne recalcule rien en local mais interroge l'API du J3 avec mise en cache (`@st.cache_data`) ; planification de l'authentification Streamlit en Sprint P4 (Dashboard v2).

---

## Suivi des paliers d'intersession (P1 → P5)

- **P1 (23/11 – 06/12/2026) :** *À compléter en fin de palier (Revue + Rétrospective).*
- **P2 (07/12 – 20/12/2026) :** *À compléter en fin de palier (Jalon `sprint-1` le 18/12).*
- **P3 (04/01 – 17/01/2027) :** *À compléter en fin de palier.*
- **P4 (18/01 – 31/01/2027) :** *À compléter en fin de palier (Jalon `sprint-2` le 29/01).*
- **P5 (01/02 – 14/02/2027) :** *Gel fonctionnel, remise dossier PDF + tag `v1.0` le 12/02, soutenance le 15/02.*
