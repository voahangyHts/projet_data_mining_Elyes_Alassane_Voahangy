"""Tests de la quality gate : un modèle moins bon ne doit jamais devenir champion."""
from src.classification import peut_promouvoir


def test_premier_modele_promu():
    assert peut_promouvoir(0.80, None)


def test_modele_aussi_bon_promu():
    assert peut_promouvoir(0.834, 0.834)


def test_modele_meilleur_promu():
    assert peut_promouvoir(0.850, 0.834)


def test_modele_moins_bon_refuse():
    assert not peut_promouvoir(0.820, 0.834)
