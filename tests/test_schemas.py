"""Tests du contrat de données et du nettoyage (ticket PAN-5)."""

import pandera.errors
import polars as pl
import pytest

from src.prepare import nettoyer_orders
from src.schemas import OrderProducts, Orders

TYPES_ORDERS = {
    "order_id": pl.Int32,
    "user_id": pl.Int32,
    "eval_set": pl.String,
    "order_number": pl.Int16,
    "order_dow": pl.Int8,
    "order_hour_of_day": pl.Int8,
    "days_since_prior_order": pl.Float32,
}


def commandes_valides() -> pl.DataFrame:
    """Deux commandes d'un même client, conformes au contrat."""
    return pl.DataFrame(
        {
            "order_id": [1, 2],
            "user_id": [10, 10],
            "eval_set": ["prior", "train"],
            "order_number": [1, 2],
            "order_dow": [0, 6],
            "order_hour_of_day": [8, 23],
            "days_since_prior_order": [None, 7.0],
        },
        schema=TYPES_ORDERS,
    )


def test_commandes_valides_acceptees():
    Orders.validate(commandes_valides())


def test_jour_hors_bornes_rejete():
    df = commandes_valides().with_columns(pl.lit(9).cast(pl.Int8).alias("order_dow"))
    with pytest.raises(pandera.errors.SchemaError):
        Orders.validate(df)


def test_mauvais_type_rejete():
    df = commandes_valides().with_columns(pl.col("order_dow").cast(pl.Int64))
    with pytest.raises(pandera.errors.SchemaError):
        Orders.validate(df)


def test_doublon_commande_produit_rejete():
    df = pl.DataFrame(
        {"order_id": [1, 1], "product_id": [5, 5], "add_to_cart_order": [1, 2], "reordered": [0, 1]},
        schema={"order_id": pl.Int32, "product_id": pl.Int32, "add_to_cart_order": pl.Int16, "reordered": pl.Int8},
    )
    with pytest.raises(pandera.errors.SchemaError):
        OrderProducts.validate(df)


def test_delai_vide_hors_premiere_commande_rejete():
    df = commandes_valides().with_columns(
        pl.lit(None, dtype=pl.Float32).alias("days_since_prior_order")
    )
    with pytest.raises(ValueError):
        nettoyer_orders(df)