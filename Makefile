# Commandes du projet Panier Vert (à lancer depuis la racine du dépôt)
.PHONY: install prepare test

# Installe l'environnement Python à l'identique (Python 3.12, Polars, Pandera...)
install: ; uv sync

# Nettoie les données brutes, vérifie le contrat Pandera et écrit data/processed/
prepare: ; uv run python -m src.prepare

# Lance les tests automatiques (contrat de données et nettoyage)
test: ; uv run python -m pytest -v