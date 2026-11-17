import pandas as pd
import os

# Création du dossier de sortie
os.makedirs("data/processed", exist_ok=True)

print("Début de la transformation (Elyes)...")

# 1. Transformation Open Food Facts
try:
    df_off = pd.read_csv("produits_laitiers_off.csv")
    if 'product_name' in df_off.columns:
        df_off['product_name_clean'] = df_off['product_name'].astype(str).str.lower().str.strip()
    df_off.to_parquet("data/processed/openfoodfacts_clean.parquet", index=False)
    print("✅ Open Food Facts transformé -> data/processed/openfoodfacts_clean.parquet")
except FileNotFoundError:
    print("⚠️ Fichier produits_laitiers_off.csv introuvable.")

# 2. Transformation RNM (Prix)
try:
    df_rnm = pd.read_csv("prix_rnm_franceagrimer.csv")
    if 'product_name_instacart' in df_rnm.columns:
        df_rnm['product_name_instacart_clean'] = df_rnm['product_name_instacart'].astype(str).str.lower().str.strip()
    df_rnm.to_parquet("data/processed/rnm_clean.parquet", index=False)
    print("✅ RNM transformé -> data/processed/rnm_clean.parquet")
except FileNotFoundError:
    print("⚠️ Fichier prix_rnm_franceagrimer.csv introuvable.")