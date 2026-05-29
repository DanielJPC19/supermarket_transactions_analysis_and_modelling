import logging
from pyspark.sql import DataFrame
from backend.config import TRANSACTIONS_ENRICHED_DIR

logger = logging.getLogger(__name__)


def write_transactions_enriched(df: DataFrame) -> None:
    """
    Escribe el DataFrame enriquecido como Parquet particionado por sucursal_id.

    Particionado permite partition pruning en KPIs/EDA por sucursal y sobreescribir
    solo la partición de una nueva sucursal (partitionOverwriteMode=dynamic en session).

    Estructura:
        data/processed/transactions_enriched/
            sucursal_id=102/part-*.parquet
            sucursal_id=103/part-*.parquet
            ...
    """
    output = str(TRANSACTIONS_ENRICHED_DIR)
    logger.info("Escribiendo Parquet en: %s", output)
    (
        df.write
        .mode("overwrite")
        .partitionBy("sucursal_id")
        .parquet(output)
    )
    logger.info("Escritura Parquet completada")


def output_exists() -> bool:
    """Verifica que existen archivos Parquet procesados."""
    path = TRANSACTIONS_ENRICHED_DIR
    if not path.exists():
        return False
    return any(path.rglob("*.parquet"))
