"""Contrat de données (Pandera) pour les tables Instacart de Panier Vert."""

import pandera.polars as pa
import polars as pl


class Orders(pa.DataFrameModel):
    """Table orders : une ligne par commande."""

    order_id: pl.Int32 = pa.Field(ge=1, unique=True)
    user_id: pl.Int32 = pa.Field(ge=1)
    eval_set: pl.String = pa.Field(isin=["prior", "train", "test"])
    order_number: pl.Int16 = pa.Field(ge=1, le=100)
    order_dow: pl.Int8 = pa.Field(ge=0, le=6)
    order_hour_of_day: pl.Int8 = pa.Field(ge=0, le=23)
    days_since_prior_order: pl.Float32 = pa.Field(ge=0, le=30, nullable=True)

    class Config:
        strict = True   # aucune colonne en plus ou en moins
        coerce = False  # typage strict : pas de conversion automatique



class OrderProducts(pa.DataFrameModel):
    """Tables order_products (prior et train) : un produit dans une commande."""

    order_id: pl.Int32 = pa.Field(ge=1)
    product_id: pl.Int32 = pa.Field(ge=1)
    add_to_cart_order: pl.Int16 = pa.Field(ge=1)
    reordered: pl.Int8 = pa.Field(isin=[0, 1])

    class Config:
        strict = True
        coerce = False
        unique = ["order_id", "product_id"]  # un produit une seule fois par commande


class Products(pa.DataFrameModel):
    """Table products : une ligne par produit."""

    product_id: pl.Int32 = pa.Field(ge=1, unique=True)
    product_name: pl.String = pa.Field(str_length={"min_value": 1})
    aisle_id: pl.Int16 = pa.Field(ge=1, le=134)
    department_id: pl.Int8 = pa.Field(ge=1, le=21)

    class Config:
        strict = True
        coerce = False


class Aisles(pa.DataFrameModel):
    """Table aisles : les 134 rayons."""

    aisle_id: pl.Int16 = pa.Field(ge=1, le=134, unique=True)
    aisle: pl.String = pa.Field(str_length={"min_value": 1})

    class Config:
        strict = True
        coerce = False


class Departments(pa.DataFrameModel):
    """Table departments : les 21 départements."""

    department_id: pl.Int8 = pa.Field(ge=1, le=21, unique=True)
    department: pl.String = pa.Field(str_length={"min_value": 1})

    class Config:
        strict = True
        coerce = False



class OrdersClean(Orders):
    """Table orders après nettoyage : ajoute l'indicateur de première commande."""

    is_first_order: pl.Boolean