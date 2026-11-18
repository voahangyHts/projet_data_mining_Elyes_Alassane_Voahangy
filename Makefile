# Commandes du projet Panier Vert (à lancer depuis la racine du dépôt)
.PHONY: install prepare test rappelconso rnm off lake modele api api-docker drift

# Installe l'environnement Python à l'identique (Python 3.12, Polars, Pandera...)
install: ; uv sync

# Nettoie les données brutes, vérifie le contrat Pandera et écrit data/processed/
prepare: ; uv run python -m src.prepare

# Lance les tests automatiques (contrat de données et nettoyage)
test: ; uv run python -m pytest -v

# Collecte RappelConso (incrémentale) puis transformation -> data/processed/rappels.parquet
rappelconso: ; uv run python -m src.collect_rappelconso && uv run python -m src.transform_rappelconso


# Scraping des prix RNM - FranceAgriMer puis transformation -> data/processed/rnm_prix.parquet
rnm: ; uv run python -m src.collect_rnm && uv run python -m src.transform_rnm


# Open Food Facts : fiche produit des codes-barres rappelés (incrémental), puis transformation
off: ; uv run python -m src.collect_off && uv run python -m src.transform_off


# Data lake : envoie data/raw et data/processed vers RustFS (lancer d'abord docker compose up -d)
lake: ; uv run python -m src.upload_lake


# API de réachat (BentoML)
modele: ; uv run python -m src.export_modele
api: ; uv run bentoml serve api.service:Reachat
api-docker: ; uv run bentoml build && uv run bentoml containerize reachat:latest


# Rapport de dérive Evidently (environnement séparé : Evidently 0.7 exige pandas 2)
drift: ; uv run --no-project --with "evidently==0.7.23" --with "pandas<3" --with polars --with pyarrow python -m src.drift