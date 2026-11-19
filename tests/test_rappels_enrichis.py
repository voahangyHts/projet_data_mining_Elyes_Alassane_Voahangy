"""Tests de la jointure rappels + Open Food Facts (sans les vraies données)."""
import polars as pl

from src.rappels_enrichis import enrichir


def _rappels():
    return pl.DataFrame({
        "id": [1, 2, 3],
        "gtin": ["3017620422003", "0000000000000", None],
        "libelle": ["Pâte à tartiner", "Produit inconnu", "Fromage à la coupe"],
    })


def _off():
    return pl.DataFrame({
        "code": ["3017620422003"],
        "nom": ["Nutella"],
        "marques": ["Ferrero"],
        "categories": ["spreads"],
        "nutriscore": ["e"],
        "ecoscore": [None],
        "nova": [3],
        "allergenes": ["nuts | milk"],
        "vendu_en_france": [True],
    })


def test_tous_les_rappels_sont_gardes():
    assert enrichir(_rappels(), _off()).height == 3


def test_rappel_retrouve_est_enrichi():
    ligne = enrichir(_rappels(), _off()).filter(pl.col("id") == 1).row(0, named=True)
    assert ligne["trouve_off"] is True
    assert ligne["nutriscore"] == "e"


def test_rappel_inconnu_ou_sans_code_reste_vide():
    table = enrichir(_rappels(), _off()).filter(pl.col("id") != 1)
    assert table["trouve_off"].to_list() == [False, False]
    assert table["nutriscore"].null_count() == 2
