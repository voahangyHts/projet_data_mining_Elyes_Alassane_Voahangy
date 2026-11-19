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

class Rappels(pa.DataFrameModel):
    """Rappels RappelConso (alimentation) : une ligne par couple (rappel, produit)."""

    id: pl.Int64 = pa.Field(ge=1)
    numero_version: pl.Int16 = pa.Field(ge=1, nullable=True)
    gtin: pl.String = pa.Field(str_matches=r"^\d{8,14}$", nullable=True)
    sous_categorie_produit: pl.String = pa.Field(nullable=True)
    marque_produit: pl.String = pa.Field(nullable=True)
    libelle: pl.String = pa.Field(nullable=True)
    motif_rappel: pl.String = pa.Field(nullable=True)
    risques_encourus: pl.String = pa.Field(nullable=True)
    date_publication: pl.Datetime
    date_fin_procedure: pl.Date = pa.Field(nullable=True)
    lien_fiche: pl.String = pa.Field(nullable=True)
    ingested_at: pl.Datetime

    class Config:
        strict = True
        coerce = False
        unique = ["id", "gtin"]



class PrixRnm(pa.DataFrameModel):
    """Prix RNM - FranceAgriMer : une ligne par produit, marché, date, stade et libellé."""

    produit_code: pl.String = pa.Field(str_matches=r"^[A-Z-]+$")
    mot_cle_instacart: pl.String = pa.Field(str_length={"min_value": 2})
    marche: pl.String = pa.Field(str_length={"min_value": 1})
    date_cotation: pl.Date = pa.Field(nullable=True)
    stade: pl.String = pa.Field(nullable=True)
    unite: pl.String = pa.Field(nullable=True)
    commentaire_marche: pl.String = pa.Field(nullable=True)
    libelle: pl.String = pa.Field(str_length={"min_value": 1})
    prix_moyen: pl.Float64 = pa.Field(ge=0)
    variation: pl.Float64 = pa.Field(nullable=True)
    mini: pl.Float64 = pa.Field(ge=0, nullable=True)
    maxi: pl.Float64 = pa.Field(ge=0, nullable=True)
    url: pl.String
    ingested_at: pl.Datetime

    class Config:
        strict = True
        coerce = False
        unique = ["produit_code", "marche", "date_cotation", "stade", "libelle"]
        
class OffProduits(pa.DataFrameModel):
    """Fiche Open Food Facts d'un code-barres rappelé."""

    code: pl.String = pa.Field(str_matches=r"^\d{8,14}$", unique=True)
    nom: pl.String = pa.Field(nullable=True)
    marques: pl.String = pa.Field(nullable=True)
    categories: pl.String = pa.Field(nullable=True)
    nutriscore: pl.String = pa.Field(
        isin=["a", "b", "c", "d", "e"], nullable=True
    )
    ecoscore: pl.String = pa.Field(
        isin=["a-plus", "a", "b", "c", "d", "e", "f"], nullable=True
    )
    nova: pl.Int64 = pa.Field(ge=1, le=4, nullable=True)
    allergenes: pl.String = pa.Field(nullable=True)
    vendu_en_france: pl.Boolean
    ingested_at: pl.Datetime

    class Config:
        strict = True
        coerce = False


class RappelsEnrichis(Rappels):
    """Table « or » : rappel RappelConso + fiche Open Food Facts (jointure par code-barres)."""

    trouve_off: pl.Boolean
    nom_off: pl.String = pa.Field(nullable=True)
    marques_off: pl.String = pa.Field(nullable=True)
    categories: pl.String = pa.Field(nullable=True)
    nutriscore: pl.String = pa.Field(
        isin=["a", "b", "c", "d", "e"], nullable=True
    )
    ecoscore: pl.String = pa.Field(
        isin=["a-plus", "a", "b", "c", "d", "e", "f"], nullable=True
    )
    nova: pl.Int64 = pa.Field(ge=1, le=4, nullable=True)
    allergenes: pl.String = pa.Field(nullable=True)
    vendu_en_france: pl.Boolean = pa.Field(nullable=True)

    class Config:
        strict = True
        coerce = False
        unique = ["id", "gtin"]
