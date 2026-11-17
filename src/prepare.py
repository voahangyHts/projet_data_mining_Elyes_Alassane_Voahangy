"""Pipeline de préparation des données Instacart (ticket PAN-5).

Lit les CSV bruts, les type, les nettoie, vérifie l'intégrité et le contrat
Pandera, puis écrit les tables propres en Parquet dans data/processed/.

Lancement : uv run python -m src.prepare
"""

import logging
import time
from pathlib import Path

import polars as pl

from src.schemas import Aisles, Departments, OrderProducts, OrdersClean, Products

# --- Paramètres ------------------------------------------------------------
RAW = Path("data/raw/instacart")
PROCESSED = Path("data/processed")

TYPES_ORDER_PRODUCTS = {
    "order_id": pl.Int32,
    "product_id": pl.Int32,
    "add_to_cart_order": pl.Int16,
    "reordered": pl.Int8,
}
TYPES = {
    "orders": {
        "order_id": pl.Int32,
        "user_id": pl.Int32,
        "order_number": pl.Int16,
        "order_dow": pl.Int8,
        "order_hour_of_day": pl.Int8,
        "days_since_prior_order": pl.Float32,
    },
    "order_products__prior": TYPES_ORDER_PRODUCTS,
    "order_products__train": TYPES_ORDER_PRODUCTS,
    "products": {"product_id": pl.Int32, "aisle_id": pl.Int16, "department_id": pl.Int8},
    "aisles": {"aisle_id": pl.Int16},
    "departments": {"department_id": pl.Int8},
}

# --- Journal (logs) --------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("prepare")


# --- Étapes de préparation -------------------------------------------------
def lire(nom: str) -> pl.DataFrame:
    """Étape 1 - Typer : lit un CSV brut en imposant les types."""
    df = pl.read_csv(RAW / f"{nom}.csv", schema_overrides=TYPES[nom])
    log.info("%s : %s lignes lues", nom, f"{df.height:,}")
    return df


def dedupliquer(df: pl.DataFrame, cles: list[str], nom: str) -> pl.DataFrame:
    """Étape 2 - Dédupliquer : garde une seule ligne par clé métier."""
    avant = df.height
    df = df.unique(subset=cles, keep="first", maintain_order=True)
    if df.height < avant:
        log.warning("%s : %s doublons supprimés", nom, f"{avant - df.height:,}")
    return df


def nettoyer_orders(orders: pl.DataFrame) -> pl.DataFrame:
    """Étape 3 - Manquants : le délai est vide uniquement pour la 1re commande."""
    orders = orders.with_columns(
        is_first_order=pl.col("days_since_prior_order").is_null()
    )
    # Règle métier : délai vide  <=>  premier numéro de commande
    incoherences = orders.filter(
        pl.col("is_first_order") != (pl.col("order_number") == 1)
    ).height
    if incoherences:
        raise ValueError(f"orders : {incoherences} délais vides hors 1re commande")
    log.info("orders : manquants de days_since_prior_order = 1res commandes (conservés)")
    return orders


def nettoyer_texte(df: pl.DataFrame, colonne: str) -> pl.DataFrame:
    """Étape 4 - Nettoyer les textes : supprime les espaces en début et fin."""
    return df.with_columns(pl.col(colonne).str.strip_chars())


def verifier_integrite(enfant: pl.DataFrame, parent: pl.DataFrame, cle: str, noms: str) -> None:
    """Chaque valeur de la clé dans la table enfant doit exister dans la table parent."""
    orphelins = enfant.join(parent.select(cle), on=cle, how="anti").height
    if orphelins:
        raise ValueError(f"Intégrité {noms} : {orphelins:,} lignes avec un {cle} inconnu")
    log.info("Intégrité OK : %s", noms)


def valider_et_ecrire(df: pl.DataFrame, contrat, nom: str) -> None:
    """Vérifie le contrat Pandera puis écrit la table propre en Parquet."""
    contrat.validate(df)
    chemin = PROCESSED / f"{nom}.parquet"
    df.write_parquet(chemin)
    log.info("%s : contrat OK, écrit dans %s", nom, chemin)


# --- Pipeline complet ------------------------------------------------------
def main() -> None:
    debut = time.perf_counter()
    PROCESSED.mkdir(parents=True, exist_ok=True)

    # 1-2. Lire, typer, dédupliquer
    aisles = dedupliquer(lire("aisles"), ["aisle_id"], "aisles")
    departments = dedupliquer(lire("departments"), ["department_id"], "departments")
    products = dedupliquer(lire("products"), ["product_id"], "products")
    orders = dedupliquer(lire("orders"), ["order_id"], "orders")
    cles_op = ["order_id", "product_id"]
    prior = dedupliquer(lire("order_products__prior"), cles_op, "order_products__prior")
    train = dedupliquer(lire("order_products__train"), cles_op, "order_products__train")

    # 3-4. Manquants et textes
    orders = nettoyer_orders(orders)
    aisles = nettoyer_texte(aisles, "aisle")
    departments = nettoyer_texte(departments, "department")
    products = nettoyer_texte(products, "product_name")

    # Intégrité entre les tables
    verifier_integrite(products, aisles, "aisle_id", "products -> aisles")
    verifier_integrite(products, departments, "department_id", "products -> departments")
    for nom, op in [("prior", prior), ("train", train)]:
        verifier_integrite(op, orders, "order_id", f"{nom} -> orders")
        verifier_integrite(op, products, "product_id", f"{nom} -> products")

    # Contrat Pandera + écriture Parquet
    valider_et_ecrire(aisles, Aisles, "aisles")
    valider_et_ecrire(departments, Departments, "departments")
    valider_et_ecrire(products, Products, "products")
    valider_et_ecrire(orders, OrdersClean, "orders")
    valider_et_ecrire(prior, OrderProducts, "order_products__prior")
    valider_et_ecrire(train, OrderProducts, "order_products__train")

    log.info("Préparation terminée en %.1f s", time.perf_counter() - debut)


if __name__ == "__main__":
    main()