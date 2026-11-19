"""Tests de l'authentification du dashboard (sans Streamlit ni vrai mot de passe)."""
from dashboard.auth import charger_comptes, hacher, verifier


def test_bon_mot_de_passe_accepte():
    assert verifier("panier-vert-2026", hacher("panier-vert-2026", iterations=1_000))


def test_mauvais_mot_de_passe_refuse():
    assert not verifier("mauvais", hacher("panier-vert-2026", iterations=1_000))


def test_empreinte_salee_jamais_identique():
    # même mot de passe -> deux empreintes différentes (sel aléatoire), et pas de mot de passe en clair
    a, b = hacher("panier-vert-2026", iterations=1_000), hacher("panier-vert-2026", iterations=1_000)
    assert a != b and "panier-vert-2026" not in a


def test_empreinte_invalide_refusee():
    assert not verifier("x", "<empreinte générée par dashboard.auth>")


def test_comptes_lus_avec_role_valide_seulement():
    env = {
        "DASHBOARD_COMPTE_DIRECTION": "direction|pbkdf2_sha256$1$aa$bb",
        "DASHBOARD_COMPTE_PIRATE": "admin|pbkdf2_sha256$1$aa$bb",   # rôle inconnu : ignoré
        "AUTRE_VARIABLE": "direction|x",                            # mauvais préfixe : ignoré
    }
    comptes = charger_comptes(env)
    assert list(comptes) == ["direction"] and comptes["direction"]["role"] == "direction"
