from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from backend.config import (
    KMEANS_ASSIGNMENTS_FILE,
    KMEANS_PROFILES_FILE,
    KMEANS_METRICS_FILE,
)
from backend.kmeans import cache
from backend.kmeans import charts
from backend.kmeans.computer import run_kmeans_sync

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kmeans", tags=["kmeans"])

_CHART_MAP = {
    "scatter-clusters":     (KMEANS_ASSIGNMENTS_FILE, charts.chart_scatter_clusters),
    "cluster-profiles":     (KMEANS_PROFILES_FILE,    charts.chart_cluster_profiles),
    "evaluation-metrics":   (KMEANS_METRICS_FILE,     charts.chart_evaluation_metrics),
    "cluster-sizes":        (KMEANS_PROFILES_FILE,    charts.chart_cluster_sizes),
}


@router.get("/status")
async def kmeans_status():
    cached = cache.all_kmeans_cached()
    best_k = None
    if cached:
        metrics = cache.load(KMEANS_METRICS_FILE)
        if metrics:
            best_k = metrics.get("best_k")
    return {"cached": cached, "best_k": best_k}


@router.post("/trigger", status_code=202)
async def trigger_kmeans():
    loop = asyncio.get_event_loop()
    asyncio.create_task(asyncio.to_thread(run_kmeans_sync, loop))
    return {"status": "K-Means job iniciado en background"}


@router.get("/cluster-assignments")
async def get_cluster_assignments():
    data = cache.load(KMEANS_ASSIGNMENTS_FILE)
    if data is None:
        raise HTTPException(503, "K-Means no disponible. Ejecuta POST /kmeans/trigger primero.")
    return JSONResponse(content=data)


@router.get("/cluster-profiles")
async def get_cluster_profiles():
    data = cache.load(KMEANS_PROFILES_FILE)
    if data is None:
        raise HTTPException(503, "K-Means no disponible. Ejecuta POST /kmeans/trigger primero.")
    return JSONResponse(content=data)


@router.get("/evaluation-metrics")
async def get_evaluation_metrics():
    data = cache.load(KMEANS_METRICS_FILE)
    if data is None:
        raise HTTPException(503, "K-Means no disponible. Ejecuta POST /kmeans/trigger primero.")
    return JSONResponse(content=data)


@router.get("/charts/{chart_name}")
async def get_chart(chart_name: str):
    if chart_name not in _CHART_MAP:
        raise HTTPException(404, f"Chart '{chart_name}' no encontrado")

    cache_key = f"chart_{chart_name}.json"
    raw = cache.load(cache_key)
    if raw is not None:
        content = raw if isinstance(raw, str) else json.dumps(raw)
        return Response(content=content, media_type="application/json")

    data_file, chart_fn = _CHART_MAP[chart_name]
    data = cache.load(data_file)
    if data is None:
        raise HTTPException(503, "K-Means no disponible. Ejecuta POST /kmeans/trigger primero.")

    fig_json = chart_fn(data)
    cache.save(cache_key, fig_json)
    return Response(content=fig_json, media_type="application/json")
