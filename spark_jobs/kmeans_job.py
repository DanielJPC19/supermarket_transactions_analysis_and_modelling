"""
K-Means customer segmentation job — ejecutable via spark-submit o python directo.

Uso:
    spark-submit spark_jobs/kmeans_job.py \
        --input-dir data/processed/transactions_enriched \
        --output-dir data/processed/kmeans

    python spark_jobs/kmeans_job.py \
        --input-dir data/processed/transactions_enriched \
        --output-dir data/processed/kmeans
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
logger = logging.getLogger("kmeans_job")

K_VALUES = [3, 4, 5, 6]
RANDOM_SEED = 42
MAX_ITER = 20
MAX_SCATTER_POINTS = 3000
FEATURE_COLS = ["frequency", "total_units", "unique_products", "unique_categories", "avg_basket_size"]


def build_customer_features(spark, input_dir: str):
    from pyspark.sql import functions as F

    df = spark.read.parquet(input_dir)

    features = df.groupBy("cliente_id").agg(
        F.countDistinct("fecha", "sucursal_id").alias("frequency"),
        F.sum("cantidad").alias("total_units"),
        F.countDistinct("producto_id").alias("unique_products"),
        F.countDistinct("categoria_id").alias("unique_categories"),
    )

    features = features.withColumn(
        "avg_basket_size",
        F.col("total_units") / F.col("frequency"),
    ).filter(F.col("frequency") >= 1)

    return features


def assemble_and_scale(features_df):
    from pyspark.ml.feature import VectorAssembler, StandardScaler

    assembler = VectorAssembler(
        inputCols=FEATURE_COLS,
        outputCol="features_raw",
        handleInvalid="skip",
    )
    assembled = assembler.transform(features_df)

    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withMean=True,
        withStd=True,
    )
    scaler_model = scaler.fit(assembled)
    return scaler_model.transform(assembled)


def train_and_evaluate(scaled_df):
    from pyspark.ml.clustering import KMeans
    from pyspark.ml.evaluation import ClusteringEvaluator

    evaluator = ClusteringEvaluator(
        featuresCol="features",
        predictionCol="cluster",
        metricName="silhouette",
        distanceMeasure="squaredEuclidean",
    )

    results = {}
    models = {}

    for k in K_VALUES:
        logger.info("Entrenando KMeans k=%d", k)
        km = KMeans(
            featuresCol="features",
            predictionCol="cluster",
            k=k,
            seed=RANDOM_SEED,
            maxIter=MAX_ITER,
        )
        model = km.fit(scaled_df)
        predictions = model.transform(scaled_df)
        silhouette = float(evaluator.evaluate(predictions))
        wssse = float(model.summary.trainingCost)
        logger.info("k=%d  silhouette=%.4f  wssse=%.2f", k, silhouette, wssse)
        results[k] = {"silhouette": silhouette, "wssse": wssse}
        models[k] = model

    best_k = max(results, key=lambda k: results[k]["silhouette"])
    logger.info("Mejor K: %d (silhouette=%.4f)", best_k, results[best_k]["silhouette"])
    return best_k, models[best_k], results


def apply_pca(scaled_df, predictions_df):
    from pyspark.ml.feature import PCA
    from pyspark.ml.functions import vector_to_array
    from pyspark.sql import functions as F

    pca = PCA(k=2, inputCol="features", outputCol="pca_features")
    pca_model = pca.fit(scaled_df)

    with_pca = pca_model.transform(predictions_df)
    with_pca = with_pca.withColumn("pca1", vector_to_array(F.col("pca_features"))[0])
    with_pca = with_pca.withColumn("pca2", vector_to_array(F.col("pca_features"))[1])

    return with_pca


def save_results(with_pca, best_k: int, eval_results: dict, output_dir: Path) -> None:
    from pyspark.sql import functions as F

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- cluster_assignments.json (max MAX_SCATTER_POINTS para el frontend) ---
    select_cols = ["cliente_id", "cluster", "pca1", "pca2"] + FEATURE_COLS
    sampled = with_pca.select(*select_cols)

    total = sampled.count()
    if total > MAX_SCATTER_POINTS:
        fraction = MAX_SCATTER_POINTS / total
        sampled = sampled.sample(fraction=fraction, seed=RANDOM_SEED)

    assignments = []
    for row in sampled.toLocalIterator():
        assignments.append({
            "cliente_id": str(row["cliente_id"]),
            "cluster": int(row["cluster"]),
            "pca1": float(row["pca1"]),
            "pca2": float(row["pca2"]),
            "frequency": float(row["frequency"]),
            "total_units": float(row["total_units"]),
            "unique_products": float(row["unique_products"]),
            "unique_categories": float(row["unique_categories"]),
            "avg_basket_size": float(row["avg_basket_size"]),
        })

    (output_dir / "cluster_assignments.json").write_text(
        json.dumps(assignments, ensure_ascii=False)
    )
    logger.info("Guardados %d puntos en cluster_assignments.json", len(assignments))

    # --- cluster_profiles.json ---
    profile_agg = with_pca.groupBy("cluster").agg(
        F.count("cliente_id").alias("size"),
        F.avg("frequency").alias("mean_frequency"),
        F.avg("total_units").alias("mean_total_units"),
        F.avg("unique_products").alias("mean_unique_products"),
        F.avg("unique_categories").alias("mean_unique_categories"),
        F.avg("avg_basket_size").alias("mean_avg_basket_size"),
    ).orderBy("cluster")

    profiles = []
    for row in profile_agg.toLocalIterator():
        profiles.append({
            "cluster": int(row["cluster"]),
            "size": int(row["size"]),
            "mean_frequency": round(float(row["mean_frequency"]), 2),
            "mean_total_units": round(float(row["mean_total_units"]), 2),
            "mean_unique_products": round(float(row["mean_unique_products"]), 2),
            "mean_unique_categories": round(float(row["mean_unique_categories"]), 2),
            "mean_avg_basket_size": round(float(row["mean_avg_basket_size"]), 2),
        })

    (output_dir / "cluster_profiles.json").write_text(
        json.dumps(profiles, ensure_ascii=False)
    )
    logger.info("Guardados %d perfiles en cluster_profiles.json", len(profiles))

    # --- evaluation_metrics.json ---
    metrics = {
        "best_k": best_k,
        "results": [
            {"k": k, "silhouette": round(v["silhouette"], 6), "wssse": round(v["wssse"], 4)}
            for k, v in sorted(eval_results.items())
        ],
    }
    (output_dir / "evaluation_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False)
    )
    logger.info("Guardadas métricas de evaluación en evaluation_metrics.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="K-Means customer segmentation")
    parser.add_argument("--input-dir",  required=True, help="Parquet de transactions_enriched")
    parser.add_argument("--output-dir", required=True, help="Directorio de salida JSON")
    parser.add_argument("--master",     default="local[*]", help="Spark master URL")
    args = parser.parse_args()

    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName("SupermercadoKMeans")
        .master(args.master)
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        logger.info("Cargando datos desde %s", args.input_dir)
        features_df = build_customer_features(spark, args.input_dir)
        features_df.cache()

        logger.info("Ensamblando features y escalando")
        scaled_df = assemble_and_scale(features_df)
        scaled_df.cache()

        logger.info("Entrenando K-Means para k ∈ %s", K_VALUES)
        best_k, best_model, eval_results = train_and_evaluate(scaled_df)

        logger.info("Aplicando PCA 2D al mejor modelo (k=%d)", best_k)
        predictions = best_model.transform(scaled_df)
        with_pca = apply_pca(scaled_df, predictions)

        output_dir = Path(args.output_dir)
        logger.info("Guardando resultados en %s", output_dir)
        save_results(with_pca, best_k, eval_results, output_dir)

        logger.info("K-Means completado exitosamente")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
