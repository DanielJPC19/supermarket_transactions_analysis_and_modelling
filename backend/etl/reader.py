import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from backend.config import TRANSACTIONS_DIR, PRODUCT_CATEGORY_FILE, CATEGORIES_FILE

logger = logging.getLogger(__name__)

# Schema: fecha|sucursal_id|cliente_id|productos_raw  (sin header, sep |)
# fecha se lee como String para controlar el cast en transformer
_TRANSACTIONS_SCHEMA = StructType([
    StructField("fecha",         StringType(),  nullable=False),
    StructField("sucursal_id",   IntegerType(), nullable=False),
    StructField("cliente_id",    IntegerType(), nullable=False),
    StructField("productos_raw", StringType(),  nullable=False),
])

# ProductCategory.csv tiene header "v.Code_pr|v.code"
_PRODUCT_CATEGORY_SCHEMA = StructType([
    StructField("producto_id",  IntegerType(), nullable=False),
    StructField("categoria_id", IntegerType(), nullable=False),
])

# Categories.csv sin header
_CATEGORIES_SCHEMA = StructType([
    StructField("categoria_id",    IntegerType(), nullable=False),
    StructField("nombre_categoria", StringType(), nullable=False),
])


def read_transactions(spark: SparkSession) -> DataFrame:
    """
    Lee todos los *_Tran.csv de Transactions/ como un único DataFrame.
    El glob captura automáticamente nuevas sucursales.
    mode=DROPMALFORMED descarta .DS_Store y filas malformadas sin romper el job.
    """
    path = str(TRANSACTIONS_DIR / "*_Tran.csv")
    logger.info("Leyendo transacciones: %s", path)
    df = spark.read.csv(
        path,
        schema=_TRANSACTIONS_SCHEMA,
        sep="|",
        header=False,
        mode="DROPMALFORMED",
        enforceSchema=True,
    )
    logger.info("Transacciones leídas: %d filas", df.count())
    return df


def read_product_category(spark: SparkSession) -> DataFrame:
    """Lee ProductCategory.csv (con header, sep |)."""
    path = str(PRODUCT_CATEGORY_FILE)
    logger.info("Leyendo ProductCategory: %s", path)
    return spark.read.csv(
        path,
        schema=_PRODUCT_CATEGORY_SCHEMA,
        sep="|",
        header=True,
        mode="DROPMALFORMED",
        enforceSchema=True,
    )


def read_categories(spark: SparkSession) -> DataFrame:
    """Lee Categories.csv (sin header, sep |, CRLF manejado automáticamente)."""
    path = str(CATEGORIES_FILE)
    logger.info("Leyendo Categories: %s", path)
    return spark.read.csv(
        path,
        schema=_CATEGORIES_SCHEMA,
        sep="|",
        header=False,
        mode="DROPMALFORMED",
        enforceSchema=True,
    )
