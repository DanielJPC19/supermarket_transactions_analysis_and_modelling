from __future__ import annotations
import logging
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

_session: SparkSession | None = None


def get_spark_session(master_url: str = "local[*]", app_name: str = "SupermercadoETL") -> SparkSession:
    """
    Retorna la SparkSession activa o crea una nueva (singleton por proceso).

    En local[*] usa todos los cores disponibles.
    En producción apunta a spark://host:7077 vía master_url.
    """
    global _session
    if _session is None or _session._sc._jsc is None:
        logger.info("Creando SparkSession | master=%s | app=%s", master_url, app_name)
        _session = (
            SparkSession.builder
            .master(master_url)
            .appName(app_name)
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.driver.memory", "2g")
            .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
            .getOrCreate()
        )
        _session.sparkContext.setLogLevel("WARN")
        logger.info("SparkSession creada correctamente")
    return _session


def stop_spark_session() -> None:
    """Detiene la SparkSession y libera la JVM. Llamar en shutdown de FastAPI."""
    global _session
    if _session is not None:
        logger.info("Deteniendo SparkSession")
        _session.stop()
        _session = None
