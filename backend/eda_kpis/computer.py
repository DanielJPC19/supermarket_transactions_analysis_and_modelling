from __future__ import annotations
import logging
from typing import Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from backend.config import TRANSACTIONS_ENRICHED_DIR

logger = logging.getLogger(__name__)


def _load_df(spark: SparkSession) -> DataFrame:
    return spark.read.parquet(str(TRANSACTIONS_ENRICHED_DIR))


def compute_total_ventas(df: DataFrame) -> dict:
    """Sum(cantidad): cada fila tiene cantidad=1, total = unidades vendidas."""
    result = df.agg(F.sum("cantidad").alias("total")).first()
    return {"value": int(result["total"])}


def compute_total_transacciones(df: DataFrame) -> dict:
    """Triplets (fecha, sucursal_id, cliente_id) distintos = visitas reales."""
    count = df.select("fecha", "sucursal_id", "cliente_id").distinct().count()
    return {"value": int(count)}


def compute_top10_productos(df: DataFrame) -> list[dict]:
    rows = (
        df.groupBy("producto_id")
          .agg(F.sum("cantidad").alias("total_cantidad"))
          .orderBy(F.desc("total_cantidad"))
          .limit(10)
          .collect()
    )
    return [
        {"producto_id": int(r["producto_id"]),
         "label": f"Producto {r['producto_id']}",
         "total_cantidad": int(r["total_cantidad"])}
        for r in rows
    ]


def compute_top10_clientes(df: DataFrame) -> list[dict]:
    rows = (
        df.select("fecha", "sucursal_id", "cliente_id")
          .distinct()
          .groupBy("cliente_id")
          .agg(F.count("*").alias("n_transacciones"))
          .orderBy(F.desc("n_transacciones"))
          .limit(10)
          .collect()
    )
    return [
        {"cliente_id": int(r["cliente_id"]),
         "label": f"Cliente {r['cliente_id']}",
         "n_transacciones": int(r["n_transacciones"])}
        for r in rows
    ]


def compute_dias_pico(df: DataFrame) -> list[dict]:
    """Top 30 días por número de transacciones (densidad suficiente para serie)."""
    rows = (
        df.select("fecha", "sucursal_id", "cliente_id")
          .distinct()
          .groupBy("fecha")
          .agg(F.count("*").alias("n_transacciones"))
          .withColumn("dia_semana", F.dayofweek("fecha"))
          .orderBy(F.desc("n_transacciones"))
          .limit(30)
          .collect()
    )
    return [
        {"fecha": str(r["fecha"]),
         "n_transacciones": int(r["n_transacciones"]),
         "dia_semana": int(r["dia_semana"])}
        for r in rows
    ]


def compute_categorias(df: DataFrame) -> list[dict]:
    """Categorías por volumen total. Excluye nulls (50% filas sin categoría)."""
    df_cat = df.filter(F.col("nombre_categoria").isNotNull())
    total_con_cat = int(df_cat.agg(F.sum("cantidad")).first()[0])
    rows = (
        df_cat.groupBy("nombre_categoria")
              .agg(
                  F.sum("cantidad").alias("total_cantidad"),
                  F.countDistinct("producto_id").alias("n_productos"),
              )
              .withColumn("pct", F.round(
                  F.col("total_cantidad") / F.lit(total_con_cat) * 100, 2))
              .orderBy(F.desc("total_cantidad"))
              .collect()
    )
    return [
        {"nombre_categoria": r["nombre_categoria"],
         "total_cantidad": int(r["total_cantidad"]),
         "n_productos": int(r["n_productos"]),
         "pct": float(r["pct"])}
        for r in rows
    ]


def compute_serie_tiempo(df: DataFrame) -> list[dict]:
    """Transacciones distintas por fecha, ordenadas cronológicamente (181 días)."""
    rows = (
        df.select("fecha", "sucursal_id", "cliente_id")
          .distinct()
          .groupBy("fecha")
          .agg(F.count("*").alias("n_transacciones"))
          .orderBy("fecha")
          .collect()
    )
    return [
        {"fecha": str(r["fecha"]), "n_transacciones": int(r["n_transacciones"])}
        for r in rows
    ]


def compute_boxplot_data(df: DataFrame) -> dict:
    """
    Total cantidad por cliente → lista de 131,186 valores (~1MB en driver).
    boxpoints='outliers' en charts.py garantiza que no se envíen todos al browser.
    """
    pdf = (
        df.groupBy("cliente_id")
          .agg(F.sum("cantidad").alias("total_cantidad"))
          .toPandas()
    )
    return {"values": pdf["total_cantidad"].tolist()}


def compute_heatmap_data(df: DataFrame) -> dict:
    """
    Features por cliente para matriz de correlación 4x4.
    toPandas sobre 131,186 clientes con 4 columnas numéricas → ~4MB, manejable.
    """
    pdf = (
        df.groupBy("cliente_id")
          .agg(
              F.countDistinct("fecha", "sucursal_id").alias("frecuencia"),
              F.sum("cantidad").alias("total_cantidad"),
              F.countDistinct("producto_id").alias("productos_distintos"),
              F.countDistinct("categoria_id").alias("categorias_distintas"),
          )
          .drop("cliente_id")
          .toPandas()
    )
    corr = pdf.corr(method="pearson")
    return {
        "labels": list(corr.columns),
        "matrix": corr.values.tolist(),
    }


def compute_all_kpis(spark: SparkSession) -> dict[str, Any]:
    """
    Orquesta todos los cómputos PySpark.
    Carga el Parquet una sola vez y lo cachea en memoria para reutilizar entre queries.
    """
    logger.info("Iniciando cómputo de todos los KPIs")
    df = _load_df(spark)
    df.cache()

    try:
        results = {
            "total_ventas":        compute_total_ventas(df),
            "total_transacciones": compute_total_transacciones(df),
            "top10_productos":     compute_top10_productos(df),
            "top10_clientes":      compute_top10_clientes(df),
            "dias_pico":           compute_dias_pico(df),
            "categorias":          compute_categorias(df),
            "serie_tiempo":        compute_serie_tiempo(df),
            "boxplot_data":        compute_boxplot_data(df),
            "heatmap_data":        compute_heatmap_data(df),
        }
    finally:
        df.unpersist()

    logger.info("Cómputo de KPIs completado")
    return results
