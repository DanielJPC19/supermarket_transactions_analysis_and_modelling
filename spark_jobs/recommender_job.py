"""
Recomendador de productos — Filtrado Colaborativo Basado en Clusters.

Uso:
    spark-submit spark_jobs/recommender_job.py \
        --input-dir  data/processed/transactions_enriched \
        --kmeans-dir data/processed/kmeans \
        --output-dir data/processed/recommender

    python spark_jobs/recommender_job.py \
        --input-dir  data/processed/transactions_enriched \
        --kmeans-dir data/processed/kmeans \
        --output-dir data/processed/recommender

Algoritmo:
  1. Split temporal 80/20 por fecha → train / test
  2. score(cluster C, producto P) = count_distinct_buyers(C,P,train) / cluster_size(C)
  3. top-10 por cliente: scores del cluster - productos ya vistos en train
  4. Evaluación: Precision@10 y Recall@10 contra test
  5. Co-ocurrencia: confidence(A→B) = cocount(A,B) / count(A) — top-20 por producto
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("recommender_job")

TOP_N = 10
MIN_BUYERS = 3       # mínimo de compradores en el cluster para incluir el producto
MIN_SUPPORT = 5      # mínimo de co-ocurrencias para reglas de asociación
TRAIN_RATIO = 0.8


# ── Carga de datos ────────────────────────────────────────────────────────────

def load_transactions(spark, input_dir: str):
    from pyspark.sql import functions as F

    df = spark.read.parquet(input_dir).select(
        "cliente_id", "producto_id", "fecha", "sucursal_id"
    )
    df = df.filter(F.col("cliente_id").isNotNull() & F.col("producto_id").isNotNull())
    return df


def load_cluster_assignments(spark, kmeans_dir: str):
    """Lee full_cluster_assignments.json → DataFrame [cliente_id IntegerType, cluster IntegerType]."""
    from pyspark.sql.types import IntegerType, StructField, StructType

    full_path = Path(kmeans_dir) / "full_cluster_assignments.json"
    if not full_path.exists():
        raise FileNotFoundError(
            f"No se encontró {full_path}. Ejecuta K-Means primero."
        )
    raw: dict = json.loads(full_path.read_text())
    # Schema explícito IntegerType para coincidir con el Parquet (evitar inferencia LongType)
    schema = StructType([
        StructField("cliente_id", IntegerType(), False),
        StructField("cluster",    IntegerType(), False),
    ])
    rows_list = [(int(k), int(v)) for k, v in raw.items()]
    return spark.createDataFrame(rows_list, schema)


# ── Split temporal ────────────────────────────────────────────────────────────

def temporal_split(transactions_df):
    """Divide transacciones en train (80%) y test (20%) por fecha."""
    from pyspark.sql import functions as F

    dates = (
        transactions_df.select("fecha").distinct()
        .orderBy("fecha")
        .collect()
    )
    cutoff_idx = max(1, int(len(dates) * TRAIN_RATIO))
    cutoff_date = dates[cutoff_idx]["fecha"]
    logger.info(
        "Split temporal: train < %s (%d días train, %d días test)",
        cutoff_date, cutoff_idx, len(dates) - cutoff_idx,
    )
    train = transactions_df.filter(F.col("fecha") < cutoff_date)
    test  = transactions_df.filter(F.col("fecha") >= cutoff_date)
    return train, test, str(dates[0]["fecha"]), str(dates[cutoff_idx - 1]["fecha"]), str(cutoff_date), str(dates[-1]["fecha"])


# ── Cluster scores ────────────────────────────────────────────────────────────

def build_cluster_scores(train_df, clusters_df):
    """
    score(cluster, producto) = distinct_buyers_in_cluster / cluster_size.
    Filtra productos con < MIN_BUYERS compradores en el cluster.
    """
    from pyspark.sql import functions as F

    cluster_sizes = clusters_df.groupBy("cluster").agg(
        F.count("cliente_id").alias("cluster_size")
    )

    train_with_cluster = train_df.join(clusters_df, on="cliente_id", how="inner")

    buyers_per_cluster_product = (
        train_with_cluster
        .groupBy("cluster", "producto_id")
        .agg(F.countDistinct("cliente_id").alias("num_buyers"))
        .filter(F.col("num_buyers") >= MIN_BUYERS)
    )

    scores = (
        buyers_per_cluster_product
        .join(cluster_sizes, on="cluster")
        .withColumn("score", F.col("num_buyers") / F.col("cluster_size"))
        .select("cluster", "producto_id", "score", "num_buyers")
    )

    return scores, cluster_sizes


# ── Generación de recomendaciones ─────────────────────────────────────────────

def generate_recommendations(clusters_df, cluster_scores_df, train_df):
    """Top-N productos por cliente: cluster scores - productos ya comprados en train."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    seen_in_train = train_df.select("cliente_id", "producto_id").distinct()

    # Candidatos: cada cliente recibe los scores de su cluster
    candidates = (
        clusters_df
        .join(cluster_scores_df.select("cluster", "producto_id", "score"), on="cluster")
        # Excluir productos ya comprados en train
        .join(seen_in_train, on=["cliente_id", "producto_id"], how="left_anti")
    )

    window = Window.partitionBy("cliente_id").orderBy(F.col("score").desc())
    recommendations = (
        candidates
        .withColumn("rank", F.row_number().over(window))
        .filter(F.col("rank") <= TOP_N)
    )

    return recommendations


# ── Evaluación ────────────────────────────────────────────────────────────────

def evaluate(recommendations_df, test_df):
    """Calcula Precision@10 y Recall@10 promedio sobre todos los clientes evaluables."""
    from pyspark.sql import functions as F

    relevant = (
        test_df
        .groupBy("cliente_id")
        .agg(F.collect_set("producto_id").alias("relevant_products"))
    )

    recs_grouped = (
        recommendations_df
        .groupBy("cliente_id")
        .agg(F.collect_set("producto_id").alias("recommended_products"))
    )

    joined = recs_grouped.join(relevant, on="cliente_id", how="inner")

    metrics_df = (
        joined
        .withColumn(
            "hits",
            F.size(F.array_intersect(F.col("recommended_products"), F.col("relevant_products")))
        )
        .withColumn("precision", F.col("hits") / F.lit(TOP_N))
        .withColumn(
            "recall",
            F.when(
                F.size(F.col("relevant_products")) > 0,
                F.col("hits") / F.size(F.col("relevant_products"))
            ).otherwise(0.0)
        )
        .filter(F.size(F.col("relevant_products")) > 0)
    )

    rows = metrics_df.agg(
        F.avg("precision").alias("avg_precision"),
        F.avg("recall").alias("avg_recall"),
        F.count("cliente_id").alias("num_users"),
    ).collect()

    if not rows or rows[0]["num_users"] == 0:
        return {"precision_at_10": 0.0, "recall_at_10": 0.0, "num_users_evaluated": 0}

    agg = rows[0]
    return {
        "precision_at_10": round(float(agg["avg_precision"] or 0), 6),
        "recall_at_10":    round(float(agg["avg_recall"] or 0), 6),
        "num_users_evaluated": int(agg["num_users"]),
    }


# ── Co-ocurrencia (recomendación por producto) ────────────────────────────────

def build_cooccurrence(train_df):
    """
    confidence(A→B) = cocount(A,B) / count(A).
    Devuelve top-20 productos co-ocurrentes por producto.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    # Crear basket_id como clave de transacción
    items = train_df.withColumn(
        "basket_id",
        F.concat_ws("_", F.col("fecha").cast("string"), F.col("sucursal_id"), F.col("cliente_id"))
    ).select("basket_id", "producto_id").distinct()

    # Filtrar canastas demasiado grandes (protege contra O(k²) en el self-join)
    basket_sizes = items.groupBy("basket_id").agg(F.count("*").alias("bsize"))
    valid_baskets = basket_sizes.filter(F.col("bsize").between(2, 50)).select("basket_id")
    items = items.join(valid_baskets, on="basket_id", how="inner")

    n_valid = valid_baskets.count()
    logger.info("Co-ocurrencia: %d/%d canastas válidas (tamaño 2-50)", n_valid, total_baskets)
    if n_valid == 0:
        logger.warning("Sin canastas válidas para co-ocurrencia — product_cooccurrence.json quedará vacío")

    # Muestrear canastas: limita el self-join a ~5M pares intermedios
    # 50k × avg-15² / 2 ≈ 5.6M pares → 176 MB con 16 tasks concurrentes (cabe en 2g)
    MAX_BASKETS_COOC = 50_000
    total_baskets = items.select("basket_id").distinct().count()
    if total_baskets > MAX_BASKETS_COOC:
        frac = MAX_BASKETS_COOC / total_baskets
        sampled = items.select("basket_id").distinct().sample(fraction=frac, seed=42)
        items = items.join(sampled, on="basket_id", how="inner")
        logger.info("Co-ocurrencia: muestreadas %d/%d canastas (frac=%.4f)", MAX_BASKETS_COOC, total_baskets, frac)

    # Cachear items antes del self-join: evita 3 evaluaciones del plan completo
    # (items_a, items_b y item_counts harían cada uno un escaneo full de 37M filas)
    items.cache()

    # Self-join sobre basket para obtener pares
    items_a = items.alias("a")
    items_b = items.alias("b")

    pairs = (
        items_a.join(items_b, on="basket_id")
        .filter(F.col("a.producto_id") < F.col("b.producto_id"))
        .groupBy(
            F.col("a.producto_id").alias("product_a"),
            F.col("b.producto_id").alias("product_b"),
        )
        .agg(F.count("*").alias("cocount"))
        .filter(F.col("cocount") >= MIN_SUPPORT)
    )

    item_counts = items.groupBy("producto_id").agg(F.count("*").alias("item_count"))

    # Confidence A→B y B→A
    conf_ab = (
        pairs
        .join(item_counts.alias("cnt_a"), pairs.product_a == F.col("cnt_a.producto_id"))
        .withColumn("confidence", F.col("cocount") / F.col("cnt_a.item_count"))
        .select(
            F.col("product_a").alias("source"),
            F.col("product_b").alias("target"),
            F.col("cocount").alias("support"),
            F.col("confidence"),
        )
    )

    conf_ba = (
        pairs
        .join(item_counts.alias("cnt_b"), pairs.product_b == F.col("cnt_b.producto_id"))
        .withColumn("confidence", F.col("cocount") / F.col("cnt_b.item_count"))
        .select(
            F.col("product_b").alias("source"),
            F.col("product_a").alias("target"),
            F.col("cocount").alias("support"),
            F.col("confidence"),
        )
    )

    all_conf = conf_ab.union(conf_ba)

    window = Window.partitionBy("source").orderBy(F.col("confidence").desc())
    top_cooc = (
        all_conf
        .withColumn("rank", F.row_number().over(window))
        .filter(F.col("rank") <= 20)
    )

    return top_cooc


# ── Guardado de resultados ────────────────────────────────────────────────────

def save_results(
    recommendations_df,
    cooccurrence_df,
    clusters_df,
    eval_metrics: dict,
    train_start: str, train_end: str,
    test_start: str, test_end: str,
    output_dir: Path,
) -> None:
    from pyspark.sql import functions as F

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- customer_recommendations.json ---
    logger.info("Guardando recomendaciones por cliente...")

    # recommendations_df ya tiene cluster (heredado de clusters_df en generate_recommendations)
    recs_with_cluster = recommendations_df.select("cliente_id", "cluster", "producto_id", "score", "rank")

    customer_recs: dict = {}
    for row in recs_with_cluster.orderBy("cliente_id", "rank").toLocalIterator():
        cid = str(row["cliente_id"])
        if cid not in customer_recs:
            customer_recs[cid] = {
                "cluster": int(row["cluster"]) if row["cluster"] is not None else -1,
                "recommendations": [],
            }
        if len(customer_recs[cid]["recommendations"]) < TOP_N:
            customer_recs[cid]["recommendations"].append({
                "producto_id": int(row["producto_id"]),
                "score": round(float(row["score"]), 6),
                "rank": int(row["rank"]),
            })

    file_path = output_dir / "customer_recommendations.json"
    file_path.write_text(json.dumps(customer_recs, ensure_ascii=False))
    file_size_mb = file_path.stat().st_size / 1e6
    logger.info("Guardado customer_recommendations.json (%d clientes, %.1f MB)", len(customer_recs), file_size_mb)
    recommendations_df.unpersist()  # libera caché antes de materializar co-ocurrencia

    # --- product_cooccurrence.json ---
    logger.info("Guardando co-ocurrencia por producto...")

    product_cooc: dict = {}
    for row in cooccurrence_df.orderBy("source", "rank").toLocalIterator():
        src = str(row["source"])
        if src not in product_cooc:
            product_cooc[src] = []
        product_cooc[src].append({
            "producto_id": int(row["target"]),
            "confidence": round(float(row["confidence"]), 6),
            "support": int(row["support"]),
        })

    (output_dir / "product_cooccurrence.json").write_text(
        json.dumps(product_cooc, ensure_ascii=False)
    )
    logger.info("Guardado product_cooccurrence.json (%d productos)", len(product_cooc))
    if not product_cooc:
        logger.warning("product_cooccurrence.json está VACÍO — ningún producto superó MIN_SUPPORT=%d", MIN_SUPPORT)

    # --- evaluation_metrics.json ---
    metrics = {
        **eval_metrics,
        "top_n": TOP_N,
        "min_buyers": MIN_BUYERS,
        "train_ratio": TRAIN_RATIO,
        "train_start": train_start,
        "train_end": train_end,
        "test_start": test_start,
        "test_end": test_end,
        "total_customers_with_recs": len(customer_recs),
    }
    (output_dir / "evaluation_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False)
    )
    logger.info(
        "Métricas: Precision@10=%.4f  Recall@10=%.4f  usuarios=%d",
        metrics["precision_at_10"], metrics["recall_at_10"], metrics["num_users_evaluated"],
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Recomendador — Filtrado Colaborativo por Clusters")
    parser.add_argument("--input-dir",  required=True, help="Parquet transactions_enriched")
    parser.add_argument("--kmeans-dir", required=True, help="Directorio kmeans (full_cluster_assignments.json)")
    parser.add_argument("--output-dir", required=True, help="Directorio de salida JSON")
    parser.add_argument("--master",     default="local[*]", help="Spark master URL")
    args = parser.parse_args()

    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName("SupermercadoRecomendador")
        .master(args.master)
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    # shuffle.partitions via conf.set(): el builder lo ignora cuando getOrCreate devuelve sesión existente
    spark.conf.set("spark.sql.shuffle.partitions", "16")
    spark.sparkContext.setLogLevel("WARN")

    try:
        logger.info("Cargando transacciones desde %s", args.input_dir)
        transactions_df = load_transactions(spark, args.input_dir)
        # No cachear transactions_df: se lee del Parquet una sola vez para el split

        logger.info("Cargando asignaciones de cluster desde %s", args.kmeans_dir)
        clusters_df = load_cluster_assignments(spark, args.kmeans_dir)
        clusters_df.cache()  # Pequeño (131k filas), reutilizado varias veces

        logger.info("Dividiendo datos 80/20 por fecha")
        train_df, test_df, train_start, train_end, test_start, test_end = temporal_split(transactions_df)
        # No cachear train/test: son usados secuencialmente, no en paralelo

        logger.info("Calculando scores por cluster (min_buyers=%d)", MIN_BUYERS)
        cluster_scores_df, _ = build_cluster_scores(train_df, clusters_df)
        cluster_scores_df.cache()

        logger.info("Generando top-%d recomendaciones por cliente", TOP_N)
        recommendations_df = generate_recommendations(clusters_df, cluster_scores_df, train_df)
        recommendations_df.cache()

        logger.info("Evaluando Precision@%d y Recall@%d", TOP_N, TOP_N)
        eval_metrics = evaluate(recommendations_df, test_df)
        logger.info(
            "Precision@10=%.4f  Recall@10=%.4f  usuarios=%d",
            eval_metrics["precision_at_10"], eval_metrics["recall_at_10"], eval_metrics["num_users_evaluated"],
        )
        cluster_scores_df.unpersist()  # ya no se necesita; libera memoria antes de co-ocurrencia

        logger.info("Calculando co-ocurrencia (min_support=%d)", MIN_SUPPORT)
        cooccurrence_df = build_cooccurrence(train_df)
        # No cachear cooccurrence_df: es pequeño (~449×20 filas) y se itera una sola vez

        output_dir = Path(args.output_dir)
        logger.info("Guardando resultados en %s", output_dir)
        save_results(
            recommendations_df, cooccurrence_df, clusters_df,
            eval_metrics,
            train_start, train_end, test_start, test_end,
            output_dir,
        )

        logger.info("Recomendador completado exitosamente")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
