from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.recommender import cache
from backend.recommender.charts import chart_evaluation_metrics, chart_top_products_heatmap
from backend.config import (
    REC_CUSTOMER_RECS_FILE,
    REC_PRODUCT_COOC_FILE,
    REC_EVAL_METRICS_FILE,
    KMEANS_CACHE_DIR,
    KMEANS_FULL_ASSIGNMENTS_FILE,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommender", tags=["recommender"])

_CHART_CACHE_FILE = "chart_{name}.json"


def _kmeans_ready() -> bool:
    return (KMEANS_CACHE_DIR / KMEANS_FULL_ASSIGNMENTS_FILE).exists()


@router.get("/status")
def recommender_status():
    cached = cache.all_cached()
    result = {
        "cached": cached,
        "kmeans_ready": _kmeans_ready(),
        "num_customers": None,
        "precision_at_10": None,
        "recall_at_10": None,
    }
    if cached and cache.is_cached(REC_EVAL_METRICS_FILE):
        metrics = cache.load(REC_EVAL_METRICS_FILE)
        result["precision_at_10"] = metrics.get("precision_at_10")
        result["recall_at_10"]    = metrics.get("recall_at_10")
        result["num_customers"]   = metrics.get("total_customers_with_recs")
    return result


@router.post("/trigger", status_code=202)
async def trigger_recommender():
    if not _kmeans_ready():
        raise HTTPException(
            status_code=412,
            detail="K-Means debe ejecutarse primero (falta full_cluster_assignments.json)",
        )
    from backend.recommender.computer import run_recommender_sync
    loop = asyncio.get_event_loop()
    asyncio.create_task(asyncio.to_thread(run_recommender_sync, loop))
    return {"message": "Job Recomendador iniciado"}


@router.get("/customer/{customer_id}")
def recommend_for_customer(customer_id: str):
    if not cache.is_cached(REC_CUSTOMER_RECS_FILE):
        raise HTTPException(status_code=503, detail="Recomendador no ejecutado aún")
    data: dict = cache.load_customer_recs()
    entry = data.get(str(customer_id))
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Cliente '{customer_id}' no encontrado")
    return {"cliente_id": customer_id, **entry}


@router.get("/product/{product_id}")
def recommend_for_product(product_id: str):
    if not cache.is_cached(REC_PRODUCT_COOC_FILE):
        raise HTTPException(status_code=503, detail="Recomendador no ejecutado aún")
    data: dict = cache.load(REC_PRODUCT_COOC_FILE)
    similar = data.get(str(product_id))
    if similar is None:
        raise HTTPException(status_code=404, detail=f"Producto '{product_id}' no encontrado")
    return {"producto_id": product_id, "similar_products": similar}


@router.get("/evaluation")
def get_evaluation():
    if not cache.is_cached(REC_EVAL_METRICS_FILE):
        raise HTTPException(status_code=503, detail="Recomendador no ejecutado aún")
    return cache.load(REC_EVAL_METRICS_FILE)


@router.get("/charts/{chart_name}")
def get_chart(chart_name: str):
    if not cache.all_cached():
        raise HTTPException(status_code=503, detail="Recomendador no ejecutado aún")

    cache_file = f"chart_{chart_name}.json"
    if cache.is_cached(cache_file):
        return JSONResponse(content=cache.load(cache_file))

    metrics = cache.load(REC_EVAL_METRICS_FILE)

    if chart_name == "evaluation-metrics":
        chart_json = chart_evaluation_metrics(metrics)
    elif chart_name == "top-products-heatmap":
        customer_recs = cache.load_customer_recs()
        chart_json = chart_top_products_heatmap(customer_recs)
    else:
        raise HTTPException(status_code=404, detail=f"Chart '{chart_name}' no existe")

    import json
    chart_data = json.loads(chart_json)
    cache.save(cache_file, chart_data)
    return JSONResponse(content=chart_data)
