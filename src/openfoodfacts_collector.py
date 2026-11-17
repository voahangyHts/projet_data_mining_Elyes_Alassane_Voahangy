import requests
import pandas as pd

# 1. Configuration de l'API Open Food Facts
url = "https://fr.openfoodfacts.org/cgi/search.pl"
parametres = {
    "action": "process",
    "tagtype_0": "categories",
    "tag_contains_0": "contains",
    "tag_0": "produits laitiers", 
    "json": "true",
    "page_size": 200 
}

# NOUVEAU : On ajoute une "carte d'identité" pour ne pas être bloqué (Erreur 403)
headers = {
    "User-Agent": "Projet_Etudiant_DataMining_Panier_Vert - Python/Requests"
}

# 2. Téléchargement des données (GET request avec les headers)
print("Téléchargement en cours...")
reponse = requests.get(url, params=parametres, headers=headers)

# Vérification que la requête a fonctionné (code 200)
if reponse.status_code == 200:
    data_json = reponse.json()
    # Les produits se trouvent dans la liste 'products' du JSON
    df_brut = pd.DataFrame(data_json.get('products', []))
    
    # 3. Nettoyage des données
    colonnes_metier = ['product_name', 'nutriscore_grade', 'ecoscore_grade', 'ingredients_tags']
    colonnes_disponibles = [col for col in colonnes_metier if col in df_brut.columns]
    df_clean = df_brut[colonnes_disponibles].copy()
    
    if 'nutriscore_grade' in df_clean.columns:
        df_clean = df_clean.dropna(subset=['nutriscore_grade'])
        df_clean['nutriscore_grade'] = df_clean['nutriscore_grade'].str.upper()
        
    print(f"Succès ! {len(df_clean)} produits nettoyés et prêts pour l'analyse.")
    print(df_clean.head())
    
    df_clean.to_csv("produits_laitiers_off.csv", index=False)
    
else:
    print(f"Erreur lors du téléchargement : {reponse.status_code}")