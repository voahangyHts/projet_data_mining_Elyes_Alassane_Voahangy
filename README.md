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

## 📊 Sources de Données
1. **Instacart** : Historique de 3 millions de commandes (CSV stockés dans `data/raw/`)
2. **Open Food Facts** : API REST - `https://fr.openfoodfacts.org/data` (JSON ODbL)
3. **RappelConso** : API Open Data - `https://data.economie.gouv.fr/explore/dataset/rappelconso0/api/`
4. **RNM - FranceAgriMer** : Scraping HTML - `https://rnm.franceagrimer.fr/`

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
Conformément aux exigences de reproductibilité, la collecte s'exécute avec la commande suivante :
```bash
make collect
