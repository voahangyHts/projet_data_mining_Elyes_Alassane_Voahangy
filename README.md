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

## 🚀 Démarrage rapide (Collecte)
Conformément aux exigences de reproductibilité, la collecte s'exécute avec la commande suivante :
```bash
make collect
