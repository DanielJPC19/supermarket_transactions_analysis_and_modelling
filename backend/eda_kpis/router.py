from __future__ import annotations
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.config import (
    SPARK_MASTER_URL, SPARK_APP_NAME,
    KPI_TOTAL_VENTAS, KPI_TOTAL_TRANSACCIONES, KPI_TOP10_PRODUCTOS,
    KPI_TOP10_CLIENTES, KPI_DIAS_PICO, KPI_CATEGORIAS,
    CHART_SERIE_TIEMPO, CHART_BOXPLOT, CHART_HEATMAP,
)
from backend.eda_kpis import cache
from backend.eda_kpis import computer
from backend.eda_kpis import charts
from spark_jobs.session import get_spark_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

_CHART_CACHE_KEYS = {
    "top10-productos": ("kpi", KPI_TOP10_PRODUCTOS, charts.chart_top10_productos),
    "top10-clientes":  ("kpi", KPI_TOP10_CLIENTES,  charts.chart_top10_clientes),
    "dias-pico":       ("kpi", KPI_DIAS_PICO,        charts.chart_dias_pico),
    "categorias":      ("kpi", KPI_CATEGORIAS,       charts.chart_categorias),
    "serie-tiempo":    ("direct", CHART_SERIE_TIEMPO, None),
    "boxplot":         ("direct", CHART_BOXPLOT,      None),
    "heatmap":         ("direct", CHART_HEATMAP,      None),
}


def _require_cached(filename: str) -> Any:
    data = cache.load(filename)
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="KPIs no disponibles aún. El cómputo puede tardar ~5 minutos. "
                   "Consulta GET /analytics/status para verificar el estado.",
        )
    return data


def run_kpis_sync(loop: asyncio.AbstractEventLoop | None = None) -> None:
    from backend.websocket import manager as ws_manager, db as ws_db

    logger.info("Iniciando cómputo de KPIs y charts")
    job_id = ws_db.insert_job("KPIs")

    def _broadcast(data: dict) -> None:
        if loop is not None:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    _broadcast({"type": "KPIs", "status": "running", "job_id": job_id})

    try:
        spark = get_spark_session(SPARK_MASTER_URL, SPARK_APP_NAME)
        results = computer.compute_all_kpis(spark)

        cache.save(KPI_TOTAL_VENTAS,        results["total_ventas"])
        cache.save(KPI_TOTAL_TRANSACCIONES, results["total_transacciones"])
        cache.save(KPI_TOP10_PRODUCTOS,     results["top10_productos"])
        cache.save(KPI_TOP10_CLIENTES,      results["top10_clientes"])
        cache.save(KPI_DIAS_PICO,           results["dias_pico"])
        cache.save(KPI_CATEGORIAS,          results["categorias"])

        cache.save(CHART_SERIE_TIEMPO, charts.chart_serie_tiempo(results["serie_tiempo"]))
        cache.save(CHART_BOXPLOT,      charts.chart_boxplot(results["boxplot_data"]))
        cache.save(CHART_HEATMAP,      charts.chart_heatmap(results["heatmap_data"]))

        ws_db.update_job(job_id, "completed")
        _broadcast({"type": "KPIs", "status": "completed", "job_id": job_id})
        logger.info("KPIs y charts persistidos en cache correctamente")

    except Exception as exc:
        ws_db.update_job(job_id, "failed", str(exc))
        _broadcast({"type": "KPIs", "status": "failed", "job_id": job_id, "message": str(exc)})
        logger.error("Cómputo de KPIs falló: %s", exc, exc_info=True)
        raise


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def analytics_status():
    return {
        "cache_warm": cache.all_kpis_cached(),
        "cache_dir": str(cache.KPIS_CACHE_DIR),
    }


# ── KPIs numéricos ────────────────────────────────────────────────────────────

@router.get("/kpis/total-ventas")
async def kpi_total_ventas():
    return _require_cached(KPI_TOTAL_VENTAS)


@router.get("/kpis/total-transacciones")
async def kpi_total_transacciones():
    return _require_cached(KPI_TOTAL_TRANSACCIONES)


@router.get("/kpis/top10-productos")
async def kpi_top10_productos():
    return _require_cached(KPI_TOP10_PRODUCTOS)


@router.get("/kpis/top10-clientes")
async def kpi_top10_clientes():
    return _require_cached(KPI_TOP10_CLIENTES)


@router.get("/kpis/dias-pico")
async def kpi_dias_pico():
    return _require_cached(KPI_DIAS_PICO)


@router.get("/kpis/categorias")
async def kpi_categorias():
    return _require_cached(KPI_CATEGORIAS)


# ── Charts Plotly ─────────────────────────────────────────────────────────────

@router.get("/charts/{chart_name}")
async def get_chart(chart_name: str):
    if chart_name not in _CHART_CACHE_KEYS:
        raise HTTPException(404, f"Chart '{chart_name}' no encontrado")

    mode, cache_key, chart_fn = _CHART_CACHE_KEYS[chart_name]

    raw = cache.load(cache_key if mode == "direct" else f"chart_{chart_name}.json")
    if raw is not None:
        content = raw if isinstance(raw, str) else __import__("json").dumps(raw)
        return Response(content=content, media_type="application/json")

    if mode == "kpi":
        data = cache.load(cache_key)
        if data is None:
            raise HTTPException(503, "KPIs no disponibles aún. Consulta GET /analytics/status")
        fig_json = chart_fn(data)
        cache.save(f"chart_{chart_name}.json", fig_json)
        return Response(content=fig_json, media_type="application/json")

    raise HTTPException(503, "Chart analítico no disponible aún. Espera que el cómputo termine.")


# ── Trigger manual ────────────────────────────────────────────────────────────

@router.post("/compute")
async def trigger_compute():
    loop = asyncio.get_event_loop()
    asyncio.create_task(asyncio.to_thread(run_kpis_sync, loop))
    return {"status": "Cómputo de KPIs iniciado en background"}
