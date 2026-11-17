"""Collecte Open Food Facts : la fiche produit de chaque code-barres rappelé.

Brut -> data/raw/off/produits_<horodatage>.parquet
(la réponse JSON est conservée telle quelle).
Incrémental : les codes déjà interrogés ne sont pas redemandés.
"""
import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://world.openfoodfacts.org/api/v2/product/{code}"
CHAMPS = ",".join([
    "code", "product_name", "brands", "categories_tags",
    "nutriscore_grade", "nova_group", "ecoscore_grade",
    "allergens_tags", "countries_tags",
])
USER_AGENT = "PanierVert-MSPR/1.0 (projet etudiant)"
PAUSE = 0.2   # la réponse prend déjà ~1,2 s : on reste vers 40 requêtes/min
LOT = 200     # un fichier écrit tous les 200 codes
MAX_ECHECS = 10
RAPPELS = Path("data/processed/rappels.parquet")
DOSSIER = Path("data/raw/off")
COLONNES = ["code", "http_code", "status", "json_produit"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


def creer_session():
    """Session HTTP qui relance seule en cas de saturation (429, 503...)."""
    relances = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=relances))
    session.headers["User-Agent"] = USER_AGENT
    return session


def codes_a_interroger():
    """Codes-barres des rappels, moins ceux déjà présents dans data/raw/off."""
    codes = (
        pl.read_parquet(RAPPELS)["gtin"]
        .drop_nulls()
        .unique()
        .sort()
        .to_list()
    )
    deja = set()
    fichiers = list(DOSSIER.glob("produits_*.parquet"))
    if fichiers:
        deja = set(pl.read_parquet(fichiers)["code"].to_list())
    restants = [c for c in codes if c not in deja]
    log.info(
        "%d codes dans les rappels, %d déjà interrogés, %d restants",
        len(codes), len(deja), len(restants),
    )
    return restants


def interroger(session, code):
    """Demande la fiche d'un code. 404 = produit inconnu (ce n'est pas une erreur)."""
    reponse = session.get(
        URL.format(code=code), params={"fields": CHAMPS}, timeout=30
    )
    if reponse.status_code not in (200, 404):
        reponse.raise_for_status()
    donnees = reponse.json()
    produit = donnees.get("product")
    return {
        "code": code,
        "http_code": str(reponse.status_code),
        "status": str(donnees.get("status")),
        "json_produit": json.dumps(produit, ensure_ascii=False) if produit else None,
    }


def ecrire(lignes):
    """Écrit un lot brut (tout en texte) + la date d'ingestion en UTC."""
    maintenant = datetime.now(timezone.utc)
    df = pl.DataFrame(
        lignes, schema={c: pl.String for c in COLONNES}
    ).with_columns(pl.lit(maintenant).alias("_ingested_at"))
    chemin = DOSSIER / f"produits_{maintenant:%Y%m%dT%H%M%S%f}.parquet"
    df.write_parquet(chemin)
    log.info("%d lignes écrites dans %s", df.height, chemin)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limite", type=int, default=None,
        help="nombre maximum de codes à interroger (pour tester)",
    )
    args = parser.parse_args()

    DOSSIER.mkdir(parents=True, exist_ok=True)
    codes = codes_a_interroger()
    if args.limite:
        codes = codes[: args.limite]

    session = creer_session()
    lot, trouves, echecs = [], 0, 0
    for i, code in enumerate(codes, start=1):
        try:
            ligne = interroger(session, code)
        except (requests.RequestException, ValueError) as erreur:
            echecs += 1
            log.warning("Code %s : échec (%s)", code, erreur)
            if echecs >= MAX_ECHECS:
                log.error("Trop d'échecs : arrêt (les lots écrits sont gardés)")
                break
            continue
        lot.append(ligne)
        trouves += ligne["status"] == "1"
        if len(lot) == LOT:
            ecrire(lot)
            lot = []
            log.info("%d/%d codes interrogés, %d trouvés", i, len(codes), trouves)
        time.sleep(PAUSE)

    if lot:
        ecrire(lot)
    log.info("Terminé : %d produits trouvés sur Open Food Facts", trouves)
    if echecs:
        log.warning("%d codes en échec : ils seront retentés au prochain lancement", echecs)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
    