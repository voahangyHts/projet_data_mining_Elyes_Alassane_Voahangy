# 🛒 Projet Data Mining - Panier Vert

## 👥 Membres de l'équipe
- Elyes
- Alassane
- Voahangy

## 🎯 Sujet et Problématique
Création d'une chaîne de valeur data de bout en bout pour l'enseigne **Panier Vert**. L'objectif est de valoriser les données pour comprendre les clients (segmentation), proposer des offres (règles d'association), estimer les futurs achats (prédiction) et sécuriser le catalogue (alertes qualité).

## 📦 Livrables J1 (Cadrage & Collecte)
- [📝 Note de Cadrage complète (Google Docs)](https://docs.google.com/document/d/1zu0tuSSn_PA3QzpIr4u32soNZXNI1GxXzssuX4ym5qs/edit?usp=sharing)
- [🏗️ Schéma d'Architecture Globale (PDF)](Architecture_Panier_Vert.pdf)
- [🔄 Flux de données Panier Vert (PDF)](Flux_de_donnees_Panier_Vert.pdf)

## 📦 Livrables J2 (Préparation & Mining)
- [📝 Rapport EDA et Synthèse Métier (Google Docs)](https://docs.google.com/document/d/1m8OablzJl25cVh0iweTxN7jopfrI9zkhE0kl3Su5QBk/edit?usp=sharing)
- Données nettoyées et validées par schéma (Pandera) dans `data/processed/`
- Algorithmes entraînés : Segmentation (K-means), Recommandation (FP-Growth), Prédiction de réachat (XGBoost).

## 📊 Sources de données

| Source | Contenu | Accès | Commande | Volume obtenu | Licence |
|---|---|---|---|---|---|
| Instacart (Kaggle) | 3,4 M de commandes, 49 688 produits, historique de 32,4 M de lignes | Fichiers CSV téléchargés | `make prepare` | 6 tables Parquet (127 Mo) | Usage non commercial (conditions Instacart / Kaggle) |
| RappelConso V2 | Rappels de produits en France (`rappelconso-v2-gtin-trie`) | API open data, export JSON incrémental | `make rappelconso` | 19 020 rappels bruts, 14 548 rappels alimentaires propres | Licence Ouverte Etalab 2.0 |
| RNM FranceAgriMer | Prix de gros de 18 fruits et légumes | Scraping HTML (pause de 2 s entre les pages) | `make rnm` | 1 209 prix | Données publiques, source citée (voir mentions légales du RNM) |
| Open Food Facts | Nutri-Score, Eco-Score, NOVA, allergènes des produits rappelés | API produit par code-barres | `make off` | 10 217 codes interrogés, 6 278 produits trouvés (61,4 %) | ODbL |

Chaque source suit le même circuit : **collecte** → `data/raw/<source>/` (brut fidèle, tout en texte, date d'ingestion en UTC) → **transformation** (typage, nettoyage, dédoublonnage) → **contrat Pandera** → `data/processed/`. Si le contrat échoue, le pipeline s'arrête. Aucune valeur n'est inventée : une donnée absente reste vide.

### Liens entre les sources

- **RappelConso ↔ Open Food Facts** : par le code-barres (GTIN).
- **RNM ↔ Instacart** : par un mot-clé anglais (ex. TOMATE → `tomato`), car Instacart n'a ni prix ni code-barres.

### Limites connues

- **Instacart** : pas de prix, pas de dates réelles, noms de produits en anglais ; le délai entre commandes est plafonné à 30 jours.
- **RappelConso** : 199 codes-barres invalides (« 0 », « 1 »…) remplacés par une valeur vide ; 48 doublons (même rappel, même code) retirés en gardant la version la plus récente.
- **RNM** : 18 produits seulement ; unités variables (90 % en € HT/kg, le reste en € TTC ou à la tonne) ; prix de gros, pas de prix en magasin.
- **Open Food Facts** :
  - la recherche de l'API est souvent indisponible (erreur 503) : on interroge produit par produit (≈ 15 codes par minute) ;
  - les 1 783 codes commençant par 2 sont exclus : ce sont des codes internes aux magasins (norme GS1), inconnus d'Open Food Facts ;
  - les fiches sont souvent incomplètes : 32 % sans Nutri-Score, 43 % sans groupe NOVA.

## 📁 Organisation du dépôt
- `data/raw/` : Données brutes au format Parquet et CSV (ne jamais modifier manuellement)
- `data/processed/` : Données nettoyées pour l'analyse
- `notebooks/` : Notebooks d'analyse (EDA, modélisation)
- `src/` : Scripts Python (collecte, api, scraping)

## 🧹 Préparation des données (J2 – ticket PAN-5)

Le pipeline lit les CSV bruts d'Instacart, les type, les nettoie, vérifie l'intégrité entre les tables et un **contrat de données Pandera**, puis écrit les tables propres en Parquet dans `data/processed/`.

```bash
make install   # première fois : installe l'environnement (Python 3.12, Polars, Pandera)
make prepare   # nettoyage + contrat de données
make test      # tests automatiques
```

- **Code :** `src/prepare.py` (nettoyage Polars) et `src/schemas.py` (contrat Pandera)
- **Entrée :** `data/raw/instacart/*.csv` (6 fichiers, 681 Mo)
- **Sortie :** `data/processed/*.parquet` (6 tables, 127 Mo), en ~12 s
- **Contrat :** types stricts, bornes (jour 0-6, heure 0-23, délai 0-30…), unicité des clés, aucune colonne inattendue ; toute violation arrête le pipeline
- **Manquants :** `days_since_prior_order` est vide uniquement pour la 1re commande de chaque client ; l'information est conservée dans la colonne `is_first_order`

> **PC Windows ARM** : si Polars affiche `unknown feature flag: 'sse3'`, exécuter une fois `setx POLARS_SKIP_CPU_CHECK 1` puis redémarrer le terminal / VS Code.

## 🚀 Démarrage rapide (Collecte)
Conformément aux exigences de reproductibilité, chaque source se collecte et se transforme avec une seule commande :
```bash
make install       # première fois : installe l'environnement
make rappelconso   # RappelConso : collecte incrémentale + transformation
make rnm           # RNM : scraping des prix + transformation
make off           # Open Food Facts : collecte incrémentale (longue) + transformation
make prepare       # Instacart : nettoyage + contrat de données
make test          # tests automatiques (14 tests)
```

> `make off` interroge l'API produit par produit (environ 15 codes par minute) : la collecte complète prend plusieurs heures. Elle est **incrémentale** : on peut l'arrêter (Ctrl + C) et la relancer, elle reprend où elle s'était arrêtée.


## 🐳 Data lake (Docker + RustFS)

Les données peuvent aussi être rangées dans un **data lake S3** local, RustFS, lancé avec Docker. Il reprend les deux zones du projet : le compartiment `raw` (données brutes) et le compartiment `processed` (données validées par les contrats Pandera).

```bash
cp .env.example .env    # première fois : puis changer les mots de passe dans .env
docker compose up -d    # démarre RustFS et crée les compartiments raw et processed
make lake               # envoie data/raw et data/processed (incrémental)
docker compose down     # arrête le data lake (les données sont conservées)
```

- **Console web :** http://localhost:9001 (identifiants du fichier `.env`)
- **Incrémental :** un fichier déjà présent avec la même taille n'est pas renvoyé.
- **Services optionnels :** `docker compose --profile restitution up -d` (PostgreSQL + Adminer) et `docker compose --profile mlops up -d` (MLflow, prévu pour le J3).
- **Sécurité :** `.env` contient les mots de passe et n'est jamais envoyé sur GitHub (il est dans `.gitignore`) ; seul le modèle `.env.example` est versionné.


## 🔌 API de réachat (BentoML + Docker)

L'API sert le modèle XGBoost du J2 : pour un client et un produit qu'il a déjà acheté, elle donne la probabilité qu'il le rachète à sa prochaine commande.

```bash
make modele       # entraîne XGBoost, l'enregistre dans BentoML (seuil 0,23) + table des caractéristiques
make api          # lance l'API en local -> http://localhost:3000 (documentation interactive)
make api-docker   # construit l'image Docker de l'API
docker run --rm -p 3000:3000 reachat:latest
```

| Route | Entrée | Sortie |
|---|---|---|
| `POST /predict` | `{"user_id": 184235, "product_id": 44683}` | `{"proba_reachat": 0.135, "recommander": false, "seuil": 0.23}` |
| `POST /recommandations` | `{"user_id": 184235, "n": 5}` | les 5 produits les plus probables, avec leur nom et leur probabilité |

- **Seuil** : 0,23, choisi sur la validation (F1 maximal) et enregistré avec le modèle.
- **Couple inconnu** : erreur 404 explicite, aucune prédiction inventée.
- **Limite** : l'API ne connaît que les 30 000 clients de l'échantillon d'entraînement.
- **Testé** : temps de réponse de 25 à 190 ms ; résultats identiques en local et dans le conteneur Docker.



## 🧪 Suivi des modèles (MLflow)

```bash
docker compose --profile mlops up -d   # lance MLflow -> http://localhost:5000 (mode « Model training »)
make train                             # entraîne baseline + XGBoost et les trace dans MLflow
```

- **Runs tracés :** `baseline_logreg` et `xgboost_modele` (paramètres, métriques, SHAP, équité par segment, modèle).
- **Validation croisée :** 5 plis groupés par client (`GroupKFold`) → ROC-AUC moyen **0,832**, proche du test (**0,834**) : modèle stable.
- **Reproductible :** table triée (`user_id`, `product_id`) et graine fixe → mêmes métriques à chaque lancement.
- **Registre :** modèle `reachat_xgb`, alias **`@champion`**.
- **Quality gate :** une nouvelle version ne devient champion que si son ROC-AUC est au moins égal à celui du champion actuel ; testée par `tests/test_quality_gate.py`.
- **Adresse du serveur :** variable `MLFLOW_TRACKING_URI` (par défaut `http://localhost:5000`).
- **Limite :** chaque membre a son propre serveur MLflow (local) ; un serveur partagé serait une amélioration possible.