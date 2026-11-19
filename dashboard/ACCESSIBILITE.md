# Accessibilité du tableau de bord

Grille appliquée à **toutes les pages** de `dashboard/` (référence : WCAG 2.1 niveau AA).
Pour chaque page, cocher les 6 points avant de fusionner.

| # | Règle | Comment la respecter dans Streamlit / Altair |
|---|---|---|
| 1 | **Contraste** : texte ≥ 4,5:1, éléments graphiques (barres, traits) ≥ 3:1, en thème **clair et sombre** | Utiliser les couleurs validées ci-dessous ; ne pas imposer de couleur au texte des graphiques (le thème Streamlit l'adapte) |
| 2 | **Jamais la couleur seule** pour porter une information | Écrire la valeur sur chaque barre, le nom de la catégorie sur l'axe, le statut en toutes lettres (« ⚠️ Dérive détectée » / « ✓ Stable ») |
| 3 | **Titres explicites** | Un `st.title` par page, un `st.header` par section, un titre de graphique qui dit ce qu'on regarde et sur quelle période |
| 4 | **Unités** | Dans le titre de l'axe : « (jours) », « (%) », « Nombre de produits rappelés », « Score (0 à 1) » ; formats français : `14 548`, `63 %`, `0,834` |
| 5 | **Sources** | Un `st.caption` sous chaque graphique : source, licence, fichier ou commande qui produit les données |
| 6 | **Alternative textuelle** | Un `st.expander("Voir les données du graphique")` avec le tableau ; une phrase « **Lecture :** … » qui donne le message principal |

## Couleurs validées (contraste mesuré)

| Usage | Couleur | Sur fond blanc | Sur fond sombre Streamlit |
|---|---|---|---|
| Barres principales (vert) | `#2E7D32` | 5,1:1 | 3,7:1 |
| Comparaison / neutre (gris) | `#808080` | 3,9:1 | 4,8:1 |
| Alerte (rouge) | `#D32F2F` | 5,0:1 | 3,8:1 |
| Contour des barres claires | `#767676` | 4,5:1 | 4,2:1 |

À éviter : `#1B5E20` (vert foncé, 2,4:1 en sombre), `#B71C1C` (rouge foncé, 2,9:1 en sombre).
Les couleurs officielles du Nutri-Score B, C, D sont trop pâles sur blanc (1,5 à 2,7:1) :
les garder (convention connue) mais avec le contour `#767676` et la lettre écrite.

## Résultat de la vérification

| Page | 1 Contraste | 2 Couleur seule | 3 Titres | 4 Unités | 5 Sources | 6 Alternative |
|---|---|---|---|---|---|---|
| Qualité catalogue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Équipe data | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Pages de Voahangy | à vérifier avec cette grille | | | | | |

Vérifié en navigateur : aucune erreur, structure de titres h1 → h2, chaque barre et
chaque axe ont une étiquette lue par les lecteurs d'écran (générée par Vega).

**Limite connue :** Streamlit déclare toutes les pages en anglais (`<html lang="en">`),
ce qui n'est pas réglable page par page ; un lecteur d'écran peut donc lire le
français avec une prononciation anglaise.
