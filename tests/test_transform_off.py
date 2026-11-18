"""Tests des fonctions de nettoyage Open Food Facts (sans Internet)."""
import json

from src.transform_off import ECOSCORES, NUTRISCORES, extraire, liste, note, nova


def test_note_invalide_devient_vide():
    assert note("unknown", NUTRISCORES) is None
    assert note("not-applicable", ECOSCORES) is None


def test_note_valide_gardee_en_minuscules():
    assert note(" A ", NUTRISCORES) == "a"
    assert note("a-plus", ECOSCORES) == "a-plus"


def test_nova_hors_bornes_devient_vide():
    assert nova(4) == 4
    assert nova("2") == 2
    assert nova(7) is None
    assert nova(None) is None


def test_liste_retire_le_prefixe_de_langue():
    assert liste(["en:gluten", "fr:noix"]) == "gluten | noix"
    assert liste([]) is None


def test_extraire_produit_complet():
    produit = {
        "product_name": "  Muesli   Montagnard ",
        "brands": "La Fourche",
        "nutriscore_grade": "a",
        "ecoscore_grade": "unknown",
        "nova_group": 1,
        "allergens_tags": ["en:gluten"],
        "countries_tags": ["en:france"],
    }
    ligne = extraire("1000000000081", json.dumps(produit))
    assert ligne["nom"] == "Muesli Montagnard"
    assert ligne["ecoscore"] is None
    assert ligne["allergenes"] == "gluten"
    assert ligne["vendu_en_france"] is True
    assert ligne["categories"] is None