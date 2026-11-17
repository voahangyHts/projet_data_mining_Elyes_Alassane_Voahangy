"""Collecte RappelConso V2 (rappels de produits) : téléchargement brut.

- 1re exécution : tout l'historique.
- Exécutions suivantes : uniquement les rappels publiés APRÈS le plus récent
  déjà collecté (collecte incrémentale, prévue chaque jour).

Lancement : uv run python -m src.collect_rappelconso
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "rappelconso-v2-gtin-trie/exports/json"
)
DOSSIER = Path("data/raw/rappelconso")
USER_AGENT = "PanierVert-MSPR/0.1 (projet etudiant data mining)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("collect_rappelconso")


def session_robuste() -> requests.Session:
    """Session HTTP qui réessaie automatiquement en cas d'erreur réseau."""
    relances = Retry(
        total=5,                       # 5 nouvelles tentatives au maximum
        backoff_factor=2,              # attentes croissantes : 2 s, 4 s, 8 s...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,   # si le serveur dit "attends", on attend
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=relances))
    session.headers["User-Agent"] = USER_AGENT
    return session


def derniere_date_collectee():
    """Date de publication la plus récente déjà présente dans data/raw."""
    fichiers = sorted(DOSSIER.glob("rappels_*.parquet"))
    if not fichiers:
        return None
    return (
        pl.scan_parquet(fichiers)
        .select(pl.col("date_publication").max())
        .collect()
        .item()
    )


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)

    # 1. Collecte complète ou incrémentale ?
    depuis = derniere_date_collectee()
    parametres = {}
    if depuis:
        parametres["where"] = f"date_publication > '{depuis}'"
        log.info("Collecte incrémentale : rappels publiés après %s", depuis)
    else:
        log.info("Première collecte : tout l'historique")

    # 2. Téléchargement (avec relances automatiques)
    debut = time.perf_counter()
    try:
        reponse = session_robuste().get(URL, params=parametres, timeout=180)
        reponse.raise_for_status()
    except requests.RequestException as erreur:
        log.error("Échec du téléchargement RappelConso : %s", erreur)
        raise SystemExit(1)
    rappels = reponse.json()
    duree = time.perf_counter() - debut
    log.info("%s rappels reçus en %.1f s", f"{len(rappels):,}", duree)

    if not rappels:
        log.info("Aucun nouveau rappel : rien à enregistrer")
        return

    # 3. Enregistrement brut : tout en texte (fidèle à la source) + horodatage
    maintenant = datetime.now(timezone.utc)
    df = (
        pl.from_dicts(rappels, infer_schema_length=None)
        .with_columns(pl.all().cast(pl.String))
        .with_columns(_ingested_at=pl.lit(maintenant))
    )
    chemin = DOSSIER / f"rappels_{maintenant:%Y%m%d_%H%M%S}.parquet"
    df.write_parquet(chemin)
    log.info("%s lignes écrites dans %s", f"{df.height:,}", chemin)


if __name__ == "__main__":
    main()