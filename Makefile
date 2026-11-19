# Commandes du projet Panier Vert (à lancer depuis la racine du dépôt)
.PHONY: install prepare test gate champion rappelconso rnm off lake data-version repro push pull

# Installe l'environnement Python à l'identique (Python 3.12, Polars, Pandera...)
install: ; uv sync

# Nettoie les données brutes, vérifie le contrat Pandera et écrit data/processed/
prepare: ; uv run python -m src.prepare

# Lance les tests automatiques (contrat de données et nettoyage)
test: ; uv run python -m pytest -v

# Quality gate : refuse un modèle moins bon que le champion (reports/champion.json)
gate: ; uv run python -m src.quality_gate

# Si le nouveau modèle est meilleur, il devient le champion (puis commiter champion.json)
champion: ; uv run python -m src.quality_gate --promouvoir

# Collecte RappelConso (incrémentale) puis transformation -> data/processed/rappels.parquet
rappelconso: ; uv run python -m src.collect_rappelconso && uv run python -m src.transform_rappelconso


# Scraping des prix RNM - FranceAgriMer puis transformation -> data/processed/rnm_prix.parquet
rnm: ; uv run python -m src.collect_rnm && uv run python -m src.transform_rnm


# Open Food Facts : fiche produit des codes-barres rappelés (incrémental), puis transformation
off: ; uv run python -m src.collect_off && uv run python -m src.transform_off


# Data lake : envoie data/raw et data/processed vers RustFS (lancer d'abord docker compose up -d)
lake: ; uv run python -m src.upload_lake


# --- Versionnage des données avec DVC (outil installé à part : uv tool install "dvc[s3]") ---
# Nouvelle version des données brutes (après une collecte) -> met à jour data/raw.dvc
data-version: ; dvc add data/raw

# Rejoue uniquement les étapes du pipeline dont les entrées ont changé (dvc.yaml)
repro: ; dvc repro

# Envoie / récupère les versions de données dans le dossier OneDrive partagé (remote « partage »)
push: ; dvc push
pull: ; dvc pull
