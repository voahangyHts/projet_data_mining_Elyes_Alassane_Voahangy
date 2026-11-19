"""Comptes et mots de passe du dashboard (sans Streamlit : testable dans la CI).

Les mots de passe ne sont jamais stockés : seulement leur empreinte PBKDF2-SHA256
avec un sel aléatoire, dans le fichier .env (jamais envoyé sur GitHub).

Créer un compte (le mot de passe est demandé sans s'afficher) :
    uv run python -m dashboard.auth <identifiant> <role>
puis copier la ligne affichée dans le fichier .env.
"""
import getpass
import hashlib
import hmac
import os
import secrets
import sys

ROLES = {
    "direction": "Direction",
    "metier": "Métier (CRM / Qualité)",
    "data": "Équipe Data",
}
PREFIXE = "DASHBOARD_COMPTE_"
ITERATIONS = 600_000  # recommandation OWASP pour PBKDF2-SHA256


def hacher(mot_de_passe: str, iterations: int = ITERATIONS) -> str:
    """Empreinte du mot de passe : algorithme$iterations$sel$hash."""
    sel = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), iterations)
    return f"pbkdf2_sha256${iterations}${sel}${h.hex()}"


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    """True si le mot de passe correspond à l'empreinte (comparaison à temps constant)."""
    try:
        algo, iterations, sel, attendu = empreinte.split("$")
        if algo != "pbkdf2_sha256":
            return False
        h = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), int(iterations))
    except ValueError:  # empreinte mal formée ou exemple non rempli
        return False
    return hmac.compare_digest(h.hex(), attendu)


def charger_comptes(environ=None) -> dict:
    """Comptes lus dans les variables DASHBOARD_COMPTE_<IDENTIFIANT>='<role>|<empreinte>'."""
    environ = os.environ if environ is None else environ
    comptes = {}
    for cle, valeur in environ.items():
        if not cle.startswith(PREFIXE) or "|" not in valeur:
            continue
        role, empreinte = valeur.split("|", 1)
        if role in ROLES:
            comptes[cle[len(PREFIXE):].lower()] = {"role": role, "empreinte": empreinte}
    return comptes


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ROLES:
        sys.exit(f"Usage : python -m dashboard.auth <identifiant> <{'|'.join(ROLES)}>")
    identifiant, role = sys.argv[1], sys.argv[2]
    mdp = getpass.getpass("Mot de passe : ")
    if len(mdp) < 12:
        sys.exit("Mot de passe trop court : 12 caractères minimum.")
    if mdp != getpass.getpass("Confirmer : "):
        sys.exit("Les deux mots de passe sont différents.")
    print("\nLigne à copier dans le fichier .env :")
    print(f"{PREFIXE}{identifiant.upper()}='{role}|{hacher(mdp)}'")
