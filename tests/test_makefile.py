"""Les commandes documentées dans le README doivent exister dans le Makefile.

Protège contre une résolution de conflit qui supprimerait des commandes (déjà arrivé deux fois).
"""
import re
from pathlib import Path

MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"
COMMANDES = [
    "install", "prepare", "test", "gate", "champion", "rappelconso", "rnm", "off", "lake",
    "data-version", "repro", "push", "pull",
    "modele", "api", "api-docker", "train", "drift", "enrichir", "dashboard",
]


def _cibles():
    texte = MAKEFILE.read_text(encoding="utf-8")
    return re.findall(r"^([a-z][a-z-]*):", texte, flags=re.MULTILINE)


def test_toutes_les_commandes_existent():
    manquantes = sorted(set(COMMANDES) - set(_cibles()))
    assert not manquantes, f"commandes absentes du Makefile : {manquantes}"


def test_aucune_commande_en_double():
    cibles = _cibles()
    doublons = sorted({c for c in cibles if cibles.count(c) > 1})
    assert not doublons, f"commandes écrites deux fois : {doublons}"
