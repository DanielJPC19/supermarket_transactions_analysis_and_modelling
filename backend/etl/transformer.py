import logging
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

logger = logging.getLogger(__name__)


def parse_and_explode_products(df: DataFrame) -> DataFrame:
    """
    Explota productos_raw en filas individuales.

    "20 3 1" → split → ["20","3","1"] → explode → 3 filas con producto_id int.
    Regex \s+ maneja espacios múltiples o tabs en datos futuros.
    filter(isNotNull) elimina tokens vacíos generados por trailing spaces.
    """
    return (
        df
        .withColumn("producto_id",
                    F.explode(F.split(F.col("productos_raw"), r"\s+")))
        .drop("productos_raw")
        .withColumn("producto_id", F.col("producto_id").cast(IntegerType()))
        .filter(F.col("producto_id").isNotNull())
    )


def add_quantity(df: DataFrame) -> DataFrame:
    """Cada ocurrencia de un producto en la lista = 1 unidad comprada."""
    return df.withColumn("cantidad", F.lit(1).cast(IntegerType()))


def cast_fecha(df: DataFrame) -> DataFrame:
    """Convierte fecha String → DateType (formato yyyy-MM-dd). Filtra fechas inválidas."""
    return (
        df
        .withColumn("fecha", F.to_date(F.col("fecha"), "yyyy-MM-dd"))
        .filter(F.col("fecha").isNotNull())
    )


def enrich_with_categories(
    df: DataFrame,
    df_product_category: DataFrame,
    df_categories: DataFrame,
) -> DataFrame:
    """
    Enriquece con categoría usando left joins.

    ProductCategory tiene 42,119 productos con múltiples categorías (duplicados
    de datos históricos). Se deduplica seleccionando la categoría mínima por producto
    para garantizar un join 1:1 sin inflar el conteo de filas.

    ~46% de los producto_ids en transacciones (rango 1-449) no tienen entrada
    en ProductCategory (que mapea barcodes grandes 1007+). Esas filas tendrán
    categoria_id=null y nombre_categoria=null — comportamiento esperado.
    """
    # Deduplicar: un producto → una categoría (la mínima por consistencia)
    df_pc_unique = df_product_category.groupBy("producto_id").agg(
        F.min("categoria_id").alias("categoria_id")
    )
    df_with_cat = df.join(df_pc_unique, on="producto_id", how="left")
    return df_with_cat.join(df_categories, on="categoria_id", how="left")


def select_final_columns(df: DataFrame) -> DataFrame:
    """Schema de salida del ETL."""
    return df.select(
        "fecha",
        "sucursal_id",
        "cliente_id",
        "producto_id",
        "cantidad",
        "categoria_id",
        "nombre_categoria",
    )


def run_transformations(
    df_transactions: DataFrame,
    df_product_category: DataFrame,
    df_categories: DataFrame,
) -> DataFrame:
    """Orquesta los 5 pasos de transformación en orden."""
    logger.info("Iniciando transformaciones ETL")
    df = parse_and_explode_products(df_transactions)
    df = add_quantity(df)
    df = cast_fecha(df)
    df = enrich_with_categories(df, df_product_category, df_categories)
    df = select_final_columns(df)
    logger.info("Transformaciones completadas")
    return df
