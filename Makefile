# Commandes du projet Panier Vert (à lancer depuis la racine du dépôt)
.PHONY: install prepare test rappelconso rnm

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