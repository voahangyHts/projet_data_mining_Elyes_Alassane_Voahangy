import requests
import pandas as pd

# 1. Configuration de l'API RappelConso (Gouvernement français)
url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/rappelconso/records"
parametres = {
    "limit": 100, # Nombre d'alertes à récupérer pour le test
    "refine": 'categorie_de_produit:"Alimentation"' # Filtre strictement alimentaire
}

# 2. Téléchargement des données
print("Téléchargement des alertes sanitaires en cours...")
reponse = requests.get(url, params=parametres)

# Vérification du succès (code 200)
if reponse.status_code == 200:
    data_json = reponse.json()
    
    # Les données se trouvent dans la clé 'results' de cette API
    df_brut = pd.DataFrame(data_json.get('results', []))
    
    if not df_brut.empty:
        # 3. Nettoyage et sélection des colonnes utiles au métier
        colonnes_metier = [
            'nom_de_la_marque_du_produit', 
            'noms_des_modeles_ou_references', 
            'motif_du_rappel', 
            'risques_encourus_par_le_consommateur'
        ]
        
        colonnes_disponibles = [col for col in colonnes_metier if col in df_brut.columns]
        df_clean = df_brut[colonnes_disponibles].copy()
        
        # Nettoyage des valeurs textuelles (retirer les retours à la ligne parasites)
        df_clean = df_clean.replace('\r\n', ' ', regex=True)
        
        print(f"Succès ! {len(df_clean)} alertes alimentaires nettoyées.")
        print(df_clean.head())
        
        # Sauvegarde en CSV
        df_clean.to_csv("alertes_rappelconso.csv", index=False)
    else:
        print("Aucune donnée trouvée avec ces filtres.")
        
else:
    print(f"Erreur lors du téléchargement : {reponse.status_code} - {reponse.text}")