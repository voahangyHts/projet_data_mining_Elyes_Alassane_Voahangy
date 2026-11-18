"""Envoi des données locales vers le data lake RustFS (S3).

data/raw/...       -> compartiment « raw »
data/processed/... -> compartiment « processed »
Incrémental : un fichier déjà présent avec la même taille n'est pas renvoyé.
Prérequis : le data lake tourne (docker compose up -d) et le fichier .env existe.
"""
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import EndpointConnectionError
from dotenv import load_dotenv

ZONES = {"raw": Path("data/raw"), "processed": Path("data/processed")}
EXTENSIONS = {".parquet", ".csv"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


def client_s3():
    """Connexion à RustFS avec les identifiants du fichier .env."""
    load_dotenv()
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1",
    )


def deja_presents(s3, compartiment):
    """Fichiers déjà dans le compartiment : {chemin: taille en octets}."""
    presents = {}
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=compartiment)
    for page in pages:
        for objet in page.get("Contents", []):
            presents[objet["Key"]] = objet["Size"]
    return presents


def main():
    s3 = client_s3()
    try:
        s3.list_buckets()
    except EndpointConnectionError:
        log.error("RustFS injoignable : lancer d'abord « docker compose up -d »")
        raise SystemExit(1)

    for compartiment, dossier in ZONES.items():
        presents = deja_presents(s3, compartiment)
        fichiers = sorted(
            p for p in dossier.rglob("*") if p.suffix in EXTENSIONS
        )
        envoyes = 0
        for chemin in fichiers:
            # data/raw/off/produits_x.parquet -> off/produits_x.parquet
            cle = chemin.relative_to(dossier).as_posix()
            if presents.get(cle) == chemin.stat().st_size:
                continue  # déjà dans le data lake, identique
            s3.upload_file(str(chemin), compartiment, cle)
            envoyes += 1
        log.info(
            "%s : %d fichiers locaux, %d envoyés, %d déjà présents",
            compartiment, len(fichiers), envoyes, len(fichiers) - envoyes,
        )


if __name__ == "__main__":
    main()