"""Collecte RNM - FranceAgriMer : prix des fruits et légumes (scraping).

Pour chaque produit, lit le tableau des prix de sa page
https://rnm.franceagrimer.fr/prix?<PRODUIT> et enregistre les lignes brutes.
robots.txt vérifié le 16/11/2026 : les pages /prix sont autorisées.
Source : RNM - FranceAgriMer (Licence ouverte).

Lancement : uv run python -m src.collect_rnm
"""

import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://rnm.franceagrimer.fr/prix?"
DOSSIER = Path("data/raw/rnm")
USER_AGENT = "PanierVert-MSPR/0.1 (projet etudiant data mining)"
PAUSE = 2  # secondes entre deux pages : politesse envers le site

# Produits frais suivis (codes des pages RNM)
PRODUITS = [
    "TOMATE", "POMME", "POIRE", "BANANE", "CAROTTE", "CONCOMBRE",
    "COURGETTE", "OIGNON", "AIL", "CITRON", "ORANGE", "CLEMENTINE",
    "KIWI", "AVOCAT", "FRAISE", "FRAMBOISE", "RAISIN", "ABRICOT",
]

# "Cadran Belgique : ... du 16/11/26 (cours Production) unité : € HT le kg*"
LIGNE_MARCHE = re.compile(
    r"^(?P<marche>.+?) du (?P<date_cotation>\d{2}/\d{2}/\d{2})"
    r" \(cours (?P<stade>[^)]*)\)\s*unité\s*:\s*(?P<unite>.+)$"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("collect_rnm")


def session_robuste() -> requests.Session:
    """Session HTTP qui réessaie automatiquement en cas d'erreur réseau."""
    relances = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=relances))
    session.headers["User-Agent"] = USER_AGENT
    return session


def lire_page(session: requests.Session, code: str) -> list[dict]:
    """Extrait toutes les lignes de prix de la page d'un produit."""
    url = BASE + code
    reponse = session.get(url, timeout=30)
    reponse.raise_for_status()
    soup = BeautifulSoup(reponse.text, "html.parser")

    lignes = []
    for table in soup.find_all("table"):
        premiere = table.find("tr")
        if premiere is None:
            continue
        entete = [c.get_text(" ", strip=True).lower()
                  for c in premiere.find_all(["th", "td"])]
        if not entete or entete[0] != "produit":
            continue                      # pas le tableau des prix

        marche = {}                       # marché en cours de lecture
        for tr in table.find_all("tr")[1:]:
            cellules = [c.get_text(" ", strip=True)
                        for c in tr.find_all(["th", "td"])]
            if len(cellules) == 1 and cellules[0]:
                # ligne "marché" : on la mémorise pour les prix qui suivent
                m = LIGNE_MARCHE.match(cellules[0])
                marche = m.groupdict() if m else {"marche": cellules[0]}
            elif len(cellules) >= 5 and cellules[0]:
                # ligne "prix" : on l'associe au marché en cours
                lignes.append({
                    "produit_code": code,
                    "marche": marche.get("marche"),
                    "date_cotation": marche.get("date_cotation"),
                    "stade": marche.get("stade"),
                    "unite": marche.get("unite"),
                    "libelle": cellules[0],
                    "prix_moyen": cellules[1],
                    "variation": cellules[2],
                    "mini": cellules[3],
                    "maxi": cellules[4],
                    "url": url,
                })
    return lignes


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    session = session_robuste()
    toutes, sans_prix, echecs = [], [], []

    for code in PRODUITS:
        try:
            lignes = lire_page(session, code)
        except requests.RequestException as erreur:
            log.error("%s : échec du téléchargement (%s)", code, erreur)
            echecs.append(code)
        else:
            if lignes:
                log.info("%s : %d prix extraits", code, len(lignes))
                toutes.extend(lignes)
            else:
                log.warning("%s : aucun tableau de prix sur la page", code)
                sans_prix.append(code)
        time.sleep(PAUSE)

    if sans_prix:
        log.warning("Produits sans prix : %s", ", ".join(sans_prix))
    if not toutes:
        # Jamais de valeurs inventées : on s'arrête avec une erreur.
        log.error("Aucun prix extrait : la structure du site a peut-être changé")
        raise SystemExit(1)

    maintenant = datetime.now(timezone.utc)
    df = (
        pl.from_dicts(toutes, infer_schema_length=None)
        .with_columns(pl.all().cast(pl.String))
        .with_columns(_ingested_at=pl.lit(maintenant))
    )
    chemin = DOSSIER / f"prix_{maintenant:%Y%m%d_%H%M%S}.parquet"
    df.write_parquet(chemin)
    log.info("%s prix (%d produits) écrits dans %s",
             f"{df.height:,}", df["produit_code"].n_unique(), chemin)
    if echecs:
        raise SystemExit(1)   # signale un échec partiel (pour l'alerte)


if __name__ == "__main__":
    main()