"""Le dashboard doit rester lisible par Python : protège contre les restes de conflit Git.

Aucun fichier n'est exécuté (pas besoin de Streamlit, des données ni de l'API) :
on vérifie seulement la syntaxe et l'absence de marqueurs de conflit.
"""
import ast
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
FICHIERS = sorted(DASHBOARD.rglob("*.py"))
MARQUEURS = ("<<<<<<<", "=======", ">>>>>>>")


@pytest.mark.parametrize("fichier", FICHIERS, ids=lambda f: f.relative_to(DASHBOARD).as_posix())
def test_fichier_du_dashboard_lisible(fichier):
    texte = fichier.read_text(encoding="utf-8")
    ast.parse(texte, filename=str(fichier))  # échoue si la syntaxe est cassée
    for numero, ligne in enumerate(texte.splitlines(), start=1):
        assert not ligne.startswith(MARQUEURS), f"reste de conflit Git ligne {numero}"


def test_toutes_les_pages_sont_trouvees():
    assert len(FICHIERS) >= 6  # app.py, auth.py et les 4 vues
