# Feuille de Route Agile & Gouvernance — Projet Panier Vert

- **Période d'intersession :** 23 novembre 2026 au 14 février 2027 (5 paliers de 2 semaines)
- **Remise finale (code tag `v1.0` + dossier MSPR 5.1 PDF) :** Vendredi 12 février 2027
- **Soutenance finale (J5) :** Lundi 15 février 2027

---

## 1. Équipe et répartition des rôles

Dans une équipe de 3 membres, chacun porte un rôle principal tout en contribuant au code et à la documentation sur l'ensemble de la chaîne :

| Membre | Rôle principal | Périmètre de responsabilité |
| :--- | :--- | :--- |
| **Elyes** | Chef de projet (Scrum Master) & Data Scientist | Animation des rituels, suivi planning/risques, relation encadrant, EDA, segmentation K-means, règles FP-Growth, modèle XGBoost & SHAP, récit SCQA. |
| **Voahangy** | Data Engineer & MLOps / API | Collecte des 4 sources, contrats qualité Pandera, data lake RustFS, serving API BentoML, conteneurisation Docker, socle dashboard Streamlit. |
| **Alassane** | MLOps, Qualité & Conformité | Versioning données/pipelines DVC, CI/CD GitHub Actions, quality gates, surveillance de dérive Evidently, veille qualité RappelConso/OFF, conformité RGPD/AI Act. |
| **Encadrant pédagogique** | Product Owner (Client) | Validation des incréments lors des points de suivi et arbitrages fonctionnels. |

---

## 2. Cadre méthodologique (Scrum allégé) et outils

### Outils retenus
- **Pilotage Agile :** Jira (Backlog produit, Sprints P1–P5, Board en 4 colonnes : `À faire` → `En cours` → `En revue` → `Terminé`).
- **Code & Revue :** GitHub (une branche par ticket, Pull Request relue par au moins un coéquipier, CI verte obligatoire avant fusion).
- **Données & Modèles :** DVC (remote partagé OneDrive) et MLflow (registre de modèles `@champion`).
- **Qualité & CI :** GitHub Actions (`pytest`, quality gates ROC-AUC et PR-AUC).
- **Documentation & Communication :** Markdown dans `docs/`, Google Docs (rédaction collaborative du dossier), Discord / Teams.

### Rituels par palier (2 semaines)
1. **Sprint Planning (1 h — début de palier) :** Sélection des user stories du backlog, découpage en tâches, estimation en points et affectation.
2. **Point synchro / Daily (10 min — 2 à 3 fois/semaine) :** Fait, à faire, points bloquants, mise à jour du board Jira.
3. **Revue de sprint (fin de palier) :** Enregistrement d'une **vidéo de démo de 3 minutes**, pose du tag Git de jalon et mise à jour de `docs/journal_de_bord.md`.
4. **Rétrospective (30 min — fin de palier) :** Ce qui a fonctionné, ce qui a bloqué, et une action concrète d'amélioration pour le palier suivant.

### Convention Git & Definition of Done (« Terminé »)
- **Branches :** `feat/<nom>`, `fix/<nom>`, `data/<nom>`, `docs/<nom>`.
- **Commits :** `feat:`, `fix:`, `data:`, `docs:`, `test:`, `chore:`.
- **Critères de « Terminé » :** Code relu via PR, tests unitaires et quality gates CI verts, documentation/README à jour, fusionné sur `main`.

---

## 3. Calendrier des 5 paliers et jalons officiels

| Palier | Dates | Objectifs principaux | Jalon & Livrable associé |
| :--- | :--- | :--- | :--- |
| **P1** | 23/11 – 06/12/2026 | Automatisation quotidienne et incrémentale de RappelConso, alertes automatiques en cas d'échec pipeline/source, collecte complète à l'échelle et finalisation du dictionnaire de données. | Vidéo démo P1 + mise à jour journal de bord. |
| **P2** | 07/12 – 20/12/2026 | Consolidation du mining : affinage des segments K-means, enrichissement des règles d'association et optimisation des hyperparamètres du modèle v2. | **Point de suivi 1 (Visio 30 min)** + **Tag Git `sprint-1`** le **vendredi 18/12/2026**. |
| *Pause* | *21/12 – 03/01/2027* | *Interruption pédagogique (vacances de fin d'année).* | — |
| **P3** | 04/01 – 17/01/2027 | MLOps complet : serveur MLflow partagé, test automatisé de l'API BentoML dans la CI, suivi de la dérive des prédictions (Evidently), versions d'images Docker figées et publiées. | Vidéo démo P3 + mise à jour journal de bord. |
| **P4** | 18/01 – 31/01/2027 | Dashboard v2 avec **authentification**, tests utilisateurs avec 2 testeurs externes, corrections UX et audit d'accessibilité WCAG 2.2 / RGAA 4.1. | **Point de suivi 2 (Visio 30 min)** + **Tag Git `sprint-2`** le **vendredi 29/01/2027**. |
| **P5** | 01/02 – 14/02/2027 | **Gel des fonctionnalités** dès le 01/02 (seuls les correctifs bloquants sont acceptés), finalisation du dossier écrit MSPR 5.1 (30 p.), support de soutenance et 2 répétitions de la démo live (+ plan B). | **Remise finale + Tag Git `v1.0`** le **vendredi 12/02/2027** ; **Soutenance J5** le **lundi 15/02/2027**. |
