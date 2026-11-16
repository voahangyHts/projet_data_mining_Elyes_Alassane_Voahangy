# 🛒 Projet Data Mining - Panier Vert

## 👥 Membres de l'équipe
- Elyes
- Alassane
- Voahangy

## 🎯 Sujet et Problématique
Création d'une chaîne de valeur data de bout en bout pour l'enseigne **Panier Vert**. L'objectif est de valoriser les données pour comprendre les clients (segmentation), proposer des offres (règles d'association), estimer les futurs achats (prédiction) et sécuriser le catalogue (alertes qualité).

## 📦 Livrables J1 (Cadrage & Collecte)
- [📝 Note de Cadrage complète (Google Docs)](https://docs.google.com/document/d/1zu0tuSSn_PA3QzpIr4u32soNZXNI1GxXzssuX4ym5qs/edit?usp=sharing))
- [🏗️ Schéma d'Architecture Globale (PDF)](Architecture_Panier_Vert.pdf)

## 📊 Sources de Données
1. **Instacart** : Historique de 3 millions de commandes (CSV)
2. **Open Food Facts** : API REST (Qualité nutritionnelle, licence ODbL)
3. **RappelConso** : API Open Data (Rappels sanitaires)
4. **RNM - FranceAgriMer** : Scraping avec Scrapy (Prix des fruits & légumes)

## 📁 Organisation du dépôt
- `data/raw/` : Données brutes au format Parquet (ne jamais modifier manuellement)
- `data/processed/` : Données nettoyées pour l'analyse
- `notebooks/` : Notebooks d'analyse (EDA, modélisation)
- `src/` : Scripts Python (collecte, api, scraping)

## 🚀 Démarrage rapide (Collecte)
Conformément aux exigences de reproductibilité, la collecte de toutes les sources s'exécute avec la commande suivante :
```bash
make collect
