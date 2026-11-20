# Récit décisionnel SCQA — Projet Panier Vert

## 1. Structure SCQA (Pitch de la 1re minute)

- **Situation (S) :** Panier Vert exploite un réseau de 42 épiceries bio et un service e-commerce représentant **206 209 clients** et **3,42 millions de commandes** historiques, complétés par les données publiques Open Food Facts et RappelConso.
- **Complication (C) :** Les données sont cloisonnées : les campagnes promotionnelles partent de façon indifférenciée sans savoir quel client va racheter quel produit, tandis que les rappels sanitaires menacent la confiance des consommateurs.
- **Question (Q) :** Comment proposer à chaque client le bon produit au bon moment tout en sécurisant la qualité sanitaire et nutritionnelle du catalogue ?
- **Réponse (A — Answer) :** Nous livrons une chaîne décisionnelle de bout en bout reposant sur un **score de réachat servi en API** (`reachat_xgb@champion`, ROC-AUC **0,834**), **3 segments clients** et des règles d'association, restitués dans un **tableau de bord interactif multi-publics**.

---

## 2. Script oral du Pitch (1 minute chrono — Démo 17h00 & Soutenance)

> « Bonjour. Panier Vert, ce sont 42 épiceries bio, plus de 206 000 clients et 3,4 millions de commandes. Aujourd'hui, nos équipes commerciales envoient les mêmes promotions à tout le monde, sans anticiper les besoins réels des paniers, et surveillent manuellement les alertes sanitaires.
>
> Notre question était simple : comment personnaliser les recommandations tout en sécurisant l'offre ?
>
> Notre réponse tient en un outil opérationnel : un modèle de prédiction du réachat affichant un ROC-AUC de 0,834, exposé via une API Dockerisée et connecté à un tableau de bord conçu pour chaque métier. Dès l'ouverture, la direction pilote ses indicateurs clés, le marketing cible ses offres sur 3 profils clients et des ventes croisées prouvées, et l'équipe qualité filtre instantanément les 14 548 rappels alimentaires enrichis avec le Nutri-Score. Je passe la main pour la démonstration en direct. »

---

## 3. Un même résultat, quatre récits selon le public

| Audience | Question métier | Ce que montre notre solution | Décision permise |
| :--- | :--- | :--- | :--- |
| **Direction commerciale** | Quelle est la santé globale de l'activité et de la qualité ? | 4 KPI clés (206 209 clients, taux de réachat 9,8 %, ROC-AUC 0,834, 14 548 rappels suivis) et poids des 3 segments (33 % / 34 % / 33 %). | Arbitrer le budget marketing et prioriser les plans d'action qualité. |
| **Utilisateurs métier (Marketing / CRM & Qualité)** | Qui cibler avec quel produit, et quels articles retirer/surveiller ? | Top 5 des produits recommandés par client (seuil 0,22), ventes croisées à fort lift (ex. mûres → framboises, lift 10,89) et alertes RappelConso (63 % en Nutri-Score D/E). | Lancer des offres ciblées, optimiser l'implantation en rayon et bloquer les références à risque. |
| **Équipe Data** | Le modèle est-il fiable, équitable et stable dans le temps ? | Version `reachat_xgb@champion` (v4), comparaison vs baseline (0,824), explicabilité SHAP, équité par segment et détection de dérive Evidently (délai passé de 10,7 à 17,0 j). | Décider d'un réentraînement et maintenir la qualité en production. |
| **Jury MSPR 5.1** | La démarche est-elle rigoureuse, légale et reproductible ? | Architecture médaillon, conformité RGPD/ODbL, pipeline DVC 8 étapes, CI verte (26 tests), API BentoML et restitution accessible WCAG/RGAA. | Valider l'acquisition des compétences B5C1, B5C6 et B5C8. |
