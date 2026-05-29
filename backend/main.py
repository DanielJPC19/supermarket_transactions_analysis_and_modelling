from __future__ import annotations
import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.dispatcher.dispatcher import etl_needed, run_etl_async
from backend.dispatcher.watcher import watch_and_rerun_etl
from backend.eda_kpis import cache
from backend.eda_kpis.router import router as analytics_router, run_kpis_sync
from backend.etl.writer import output_exists
from backend.config import TRANSACTIONS_ENRICHED_DIR
from backend.websocket import manager, db
from spark_jobs.session import stop_spark_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_watcher_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _watcher_task

    # ── STARTUP ──────────────────────────────────────────────────────────
    db.init_db()
    logger.info("Startup: verificando estado ETL")
    if etl_needed():
        logger.info("Ejecutando ETL inicial")
        try:
            await run_etl_async()
        except Exception as exc:
            logger.error("ETL inicial falló: %s", exc, exc_info=True)

    if not cache.all_kpis_cached():
        logger.info("Cache KPIs no warm → lanzando cómputo en background")
        loop = asyncio.get_event_loop()
        asyncio.create_task(asyncio.to_thread(run_kpis_sync, loop))
    else:
        logger.info("Cache KPIs ya warm")

    _watcher_task = asyncio.create_task(watch_and_rerun_etl())
    logger.info("Watcher de Transactions/ iniciado")

    yield  # FastAPI sirve requests aquí

    # ── SHUTDOWN ─────────────────────────────────────────────────────────
    logger.info("Shutdown: liberando recursos")
    if _watcher_task and not _watcher_task.done():
        _watcher_task.cancel()
        try:
            await _watcher_task
        except asyncio.CancelledError:
            pass
    stop_spark_session()
    logger.info("Recursos liberados")


app = FastAPI(
    title="Supermercado Analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/etl/status")
async def etl_status():
    return {
        "processed_data_available": output_exists(),
        "output_path": str(TRANSACTIONS_ENRICHED_DIR),
    }


@app.post("/etl/trigger")
async def trigger_etl():
    loop = asyncio.get_event_loop()
    asyncio.create_task(run_etl_async(loop))
    return {"status": "ETL job iniciado en background"}


@app.websocket("/ws/jobs")
async def ws_jobs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Enviar historial reciente al conectar
        await websocket.send_text(json.dumps(db.get_recent_jobs()))
        while True:
            await websocket.receive_text()  # mantiene viva la conexión
    except WebSocketDisconnect:
        manager.disconnect(websocket)
