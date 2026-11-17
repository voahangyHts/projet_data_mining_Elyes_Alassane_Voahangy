import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. Configuration du Scraping
# URL générique pour l'exemple (le vrai site RNM nécessite parfois de naviguer dans les menus)
url = "https://rnm.franceagrimer.fr/prix?FRUITS-ET-LEGUMES"
headers = {"User-Agent": "Projet_Etudiant_DataMining_Panier_Vert"}

print("Connexion au site du RNM en cours...")
reponse = requests.get(url, headers=headers)

if reponse.status_code == 200:
    print("Page téléchargée ! Extraction des prix...")
    soup = BeautifulSoup(reponse.text, 'html.parser')
    
    # 2. Extraction du tableau des prix (Simulation de la structure HTML standard)
    # On cherche toutes les lignes <tr> dans le tableau des cotations
    produits_extraits = []
    
    # Note : Le HTML exact du RNM étant très complexe, on simule ici la logique d'extraction
    # Si le vrai tableau a des classes CSS spécifiques, il faudrait adapter : soup.find('table', class_='nom_de_la_classe')
    table = soup.find('table') 
    
    if table:
        lignes = table.find_all('tr')
        for ligne in lignes[1:]: # On ignore la première ligne (en-têtes)
            colonnes = ligne.find_all('td')
            if len(colonnes) >= 2:
                nom_fruit_legume = colonnes[0].text.strip()
                prix_texte = colonnes[1].text.strip()
                produits_extraits.append({"nom_fr": nom_fruit_legume, "prix_moyen_texte": prix_texte})
    else:
        # Données de secours pour que tu puisses tester le nettoyage si le site bloque le scraping
        produits_extraits = [
            {"nom_fr": "Pomme", "prix_moyen_texte": "2,50 €"},
            {"nom_fr": "Banane", "prix_moyen_texte": "1,99 €"},
            {"nom_fr": "Carotte", "prix_moyen_texte": "1,20 €"},
            {"nom_fr": "Tomate", "prix_moyen_texte": "3,15 €"}
        ]
        print("Tableau HTML non trouvé, utilisation des données de secours pour le test de nettoyage.")

    df_prix = pd.DataFrame(produits_extraits)
    
    # 3. Nettoyage des données (Transformation en Float)
    print("Nettoyage des données (Conversion des prix)...")
    # On retire le symbole €, on retire les espaces, et on remplace la virgule par un point
    df_prix['prix_moyen_num'] = df_prix['prix_moyen_texte'].str.replace('€', '').str.strip()
    df_prix['prix_moyen_num'] = df_prix['prix_moyen_num'].str.replace(',', '.')
    # Conversion en type numérique (float) pour pouvoir faire des moyennes plus tard
    df_prix['prix_moyen_num'] = df_prix['prix_moyen_num'].astype(float)
    
    # 4. Uniformisation pour Instacart (Dictionnaire de traduction FR -> EN)
    dictionnaire_traduction = {
        "Pomme": "Apples",
        "Banane": "Bananas",
        "Carotte": "Carrots",
        "Tomate": "Tomatoes"
        # Tu pourras enrichir ce dictionnaire avec les autres produits de ton catalogue
    }
    
    df_prix['product_name_instacart'] = df_prix['nom_fr'].map(dictionnaire_traduction)
    
    # Pause de courtoisie pour ne pas surcharger le serveur du gouvernement
    time.sleep(2)
    
    print(f"Succès ! {len(df_prix)} prix de fruits et légumes récupérés.")
    print(df_prix.head())
    
    # 5. Sauvegarde
    df_prix.to_csv("prix_rnm_franceagrimer.csv", index=False)
    
else:
    print(f"Erreur de connexion : {reponse.status_code}")