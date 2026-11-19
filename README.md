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

## 📦 Livrables J3 (Industrialisation MLOps) – tag `j3-mlops`
- **API de réachat** BentoML, conteneurisée avec Docker (voir [API](#-api-de-réachat-bentoml--docker))
- **Suivi des modèles** MLflow : 4 modèles dans 3 expériences, registre avec alias `@champion` et quality gate
- **Versionnage des données** DVC et pipeline reproductible (`dvc repro`)
- **Intégration continue** GitHub Actions : tests automatiques + quality gate à chaque pull request
- **Surveillance de la dérive** Evidently (`reports/drift_report.html`)
- **Architecture médaillon** (bronze / silver / gold) et table gold `rappels_enrichis`

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


### Architecture médaillon

Les données sont organisées en trois couches, de la plus brute à la plus utile au métier :

| Couche | Dossier | Contenu |
|---|---|---|
| 🥉 **Bronze** (brut) | `data/raw/` | Données telles que collectées : Instacart, RappelConso, RNM, Open Food Facts (jamais modifiées à la main) |
| 🥈 **Silver** (nettoyé) | `data/processed/` | Tables Parquet typées, nettoyées, dédoublonnées et validées par les contrats Pandera |
| 🥇 **Gold** (prêt à l'usage) | `data/processed/` | Tables métier : `features_reachat.parquet` (API de réachat), `segments_clients.parquet` (segment + `nom_segment`), `rappels_enrichis.parquet` (rappels + Open Food Facts) |

Les dossiers `raw/` et `processed/` gardent leurs noms, car le pipeline DVC s'appuie sur ces chemins : la couche Gold se distingue par le nom de ses tables, pas par un dossier séparé.



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
- `src/` : Scripts Python (collecte, nettoyage, modèles, MLflow, dérive)
- `api/` : API de réachat (BentoML) ; `bentofile.yaml` pour l'image Docker
- `tests/` : tests automatiques (pytest)
- `reports/` : résultats des modèles (graphiques, tableaux, `champion.json`, rapport de dérive)
- `dvc.yaml` / `dvc.lock` : pipeline DVC ; `.github/workflows/ci.yml` : intégration continue

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
make test          # tests automatiques (26 tests)
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
- **Services optionnels :** `docker compose --profile restitution up -d` (PostgreSQL + Adminer) et `docker compose --profile mlops up -d` (MLflow, voir plus bas).
- **Sécurité :** `.env` contient les mots de passe et n'est jamais envoyé sur GitHub (il est dans `.gitignore`) ; seul le modèle `.env.example` est versionné.

## 🗂️ Versionnage des données (DVC)

Git versionne le code, **DVC versionne les données**. Les fichiers lourds restent hors de Git : Git ne garde que de petits fichiers d'empreintes (`data/raw.dvc`, `dvc.lock`), et le contenu est stocké dans un **dossier OneDrive partagé** entre les membres de l'équipe (remote DVC `partage`, celui par défaut). Chaque commit Git correspond ainsi à une version exacte des données et des résultats.

- **Données brutes** (`data/raw/`) : versionnées par `data/raw.dvc`. Elles ne se recalculent pas (copie Kaggle, collectes API), donc on les fige après chaque collecte.
- **Pipeline** (`dvc.yaml`) : `prepare` et `transform_*` (brut → propre), puis `clustering`, `rules` et `classification`. `dvc repro` ne relance que les étapes dont le code ou les entrées ont changé, et `dvc.lock` enregistre les empreintes de chaque entrée et sortie.
- **Résultats** (`reports/`) : produits par le pipeline mais laissés dans Git, pour rester lisibles sur GitHub.

**Première installation (une fois par PC) :**

1. Installer DVC (à part du projet, à cause d'un conflit de versions avec boto3) :
   ```bash
   uv tool install "dvc[s3]"
   ```
2. Avoir le dossier partagé **`Panier-Vert-DVC`** synchronisé sur son PC : sur onedrive.live.com, ouvrir **Partagés**, faire un clic droit sur `Panier-Vert-DVC`, puis **Ajouter un raccourci à Mes fichiers**. Il apparaît dans l'explorateur, sous `OneDrive`.
3. Donner à DVC le chemin de ce dossier **sur son PC** (le chemin diffère d'un PC à l'autre, d'où `--local`) :
   ```bash
   dvc remote add --local partage "C:\Users\<moi>\OneDrive\Panier-Vert-DVC"
   ```
4. Conseillé, si le projet est lui-même dans OneDrive : mettre le cache DVC hors de OneDrive, pour ne pas synchroniser les données en double :
   ```bash
   dvc cache dir --local "C:\Users\<moi>\.dvc-cache\panier-vert"
   ```

Ces réglages vont dans `.dvc/config.local`, qui n'est jamais envoyé sur GitHub.

**Au quotidien :**
```bash
make data-version   # après une collecte : nouvelle version de data/raw (dvc add)
make repro          # rejoue les étapes du pipeline qui ont changé
make push           # envoie les données versionnées dans le dossier partagé
git add data/raw.dvc dvc.lock reports && git commit -m "..." && git push
```

**Récupérer les données d'un coéquipier :**
```bash
git pull            # récupère data/raw.dvc et dvc.lock
make pull           # récupère les données correspondantes (dvc pull)
```

> Attendre que OneDrive ait fini de synchroniser (icône ✓) avant `make pull` chez l'autre, et ne jamais modifier à la main le contenu de `Panier-Vert-DVC`.
>
> Pour revenir à une ancienne version des données : `git checkout <commit>` puis `dvc checkout`.
>
> Le remote `lake` (data lake RustFS local) reste disponible comme sauvegarde personnelle : `dvc push -r lake`.

## ✅ Intégration continue et quality gate (GitHub Actions)

À chaque push et pull request, GitHub lance seul le workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) :

1. **Tests automatiques** : contrats de données, nettoyage et quality gate (`make test`).
2. **Quality gate** : le meilleur modèle de `reports/classification_resultats.csv` est comparé au **champion** enregistré dans `reports/champion.json`, sur la **PR-AUC** (métrique adaptée aux classes déséquilibrées : environ 10 % de réachats). Un modèle moins bon que le champion, au-delà d'une tolérance de 0,005, est **refusé** : le commit passe en rouge et la pull request ne doit pas être fusionnée.

```bash
make gate       # vérifier en local avant de pousser
make champion   # le nouveau modèle est meilleur : il devient le champion
```

Le quality gate est aussi la dernière étape du pipeline DVC : `dvc repro` échoue si le modèle régresse. GitHub n'entraîne pas les modèles (les données restent sur le data lake local) : il vérifie les résultats produits par `dvc repro` et versionnés dans `reports/`.

## 🔌 API de réachat (BentoML + Docker)

L'API sert le modèle XGBoost du J2 : pour un client et un produit qu'il a déjà acheté, elle donne la probabilité qu'il le rachète à sa prochaine commande.

```bash
make modele       # récupère le champion MLflow (@champion), l'enregistre dans BentoML + table des caractéristiques
make api          # lance l'API en local -> http://localhost:3000 (documentation interactive)
make api-docker   # construit l'image Docker de l'API
docker run --rm -p 3000:3000 reachat:latest
```

| Route | Entrée | Sortie |
|---|---|---|
| `POST /predict` | `{"user_id": 23, "product_id": 2138}` | `{"proba_reachat": 0.007, "recommander": false, "seuil": 0.22}` |
| `POST /recommandations` | `{"user_id": 23, "n": 5}` | les 5 produits les plus probables, avec leur nom et leur probabilité (ex. « Original French Vanilla Yogurt », 0.225) |

- **Seuil** : 0,22, choisi sur la validation (F1 maximal) et lu dans le run du champion MLflow.
- **Couple inconnu** : erreur 404 explicite, aucune prédiction inventée.
- **Limite** : l'API ne connaît que les 30 000 clients de l'échantillon d'entraînement.
- **Testé** : temps de réponse de 25 à 190 ms ; résultats identiques en local et dans le conteneur Docker.



## 🧪 Suivi des modèles (MLflow)

```bash
docker compose --profile mlops up -d   # lance MLflow -> http://localhost:5000 (mode « Model training »)
make train                             # entraîne baseline + XGBoost et les trace dans MLflow
```

- **4 modèles tracés, dans 3 expériences :**
  - `prediction_reachat` : baseline (régression logistique) et XGBoost (paramètres, métriques, SHAP, équité par segment, modèle) — `make train` ;
  - `segmentation_clients` : K-means, un run par k testé (inertie, silhouette) + k retenu, graphiques et modèle ; segments numérotés par nombre de commandes croissant (0 = Gros paniers bio et frais du week-end, 1 = Occasionnels petits paniers, 2 = Fidèles réguliers) et nommés automatiquement d'après leur profil — `uv run python -m src.clustering` ;
  - `regles_association` : FP-Growth au niveau rayons et produits (seuils, nombre de règles, lift maximal, top 5) — `uv run python -m src.rules`.
- **Validation croisée :** 5 plis groupés par client (`GroupKFold`) → ROC-AUC moyen **0,832**, proche du test (**0,834**) : modèle stable.
- **Reproductible :** table triée (`user_id`, `product_id`) et graine fixe → mêmes métriques à chaque lancement.
- **Registre :** modèle `reachat_xgb`, alias **`@champion`**.
- **Quality gate :** une nouvelle version ne devient champion que si son ROC-AUC est au moins égal à celui du champion actuel ; testée par `tests/test_quality_gate.py`. Elle complète le quality gate de la CI (PR-AUC, `reports/champion.json`, testé par `tests/test_quality_gate_ci.py`) : MLflow décide du champion servi par l'API, la CI bloque une régression dans une pull request.
- **Adresse du serveur :** variable `MLFLOW_TRACKING_URI` (par défaut `http://localhost:5000`).
- **Limite :** chaque membre a son propre serveur MLflow (local) ; un serveur partagé serait une amélioration possible.


## 📈 Surveillance de la dérive (Evidently)

Le rapport compare l'historique des commandes (`prior`, référence) aux dernières commandes de chaque client (`train`, courant), sur 50 000 commandes tirées au hasard dans chaque jeu.

```bash
make drift   # génère reports/drift_report.html
```

| Variable | Test | Score | Dérive |
|---|---|---|---|
| Délai depuis la commande précédente | Wasserstein | **0,711** | ⚠️ détectée (10,7 → 17,0 jours) |
| Part de produits rachetés | Wasserstein | 0,096 | non |
| Taille du panier | Wasserstein | 0,061 | non |
| Jour de la semaine | Jensen-Shannon | 0,042 | non |
| Heure de commande | Wasserstein | 0,027 | non |

- **Lecture :** les habitudes (heure, jour, panier, réachat) sont stables ; seule la cadence change. C'est probablement un effet de la construction du jeu Instacart (la commande `train` est la dernière de chaque client) : à interpréter avec prudence.
- **À surveiller :** le délai influence le réachat (hypothèse H1, SHAP). Une dérive qui toucherait aussi la part de rachats justifierait de réentraîner le modèle.
- **Technique :** Evidently 0.7 n'est pas compatible avec pandas 3 (utilisé par le projet). `make drift` lance donc le script dans un environnement séparé avec pandas 2, sans modifier celui du projet.
