from __future__ import annotations
import asyncio
import hashlib
import json
import logging
from typing import Any

from backend.config import (
    TRANSACTIONS_DIR,
    PROCESSED_DIR,
    ETL_FORCE_RERUN,
    SPARK_MASTER_URL,
    SPARK_APP_NAME,
)
from backend.etl.reader import read_transactions, read_product_category, read_categories
from backend.etl.transformer import run_transformations
from backend.etl.writer import write_transactions_enriched, output_exists
from spark_jobs.session import get_spark_session

logger = logging.getLogger(__name__)

_STATE_FILE = PROCESSED_DIR / ".etl_state.json"


def _compute_fingerprint() -> str:
    entries = [
        {"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime}
        for f in sorted(TRANSACTIONS_DIR.glob("*_Tran.csv"))
    ]
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def _load_fingerprint() -> str | None:
    if not _STATE_FILE.exists():
        return None
    try:
        return json.loads(_STATE_FILE.read_text()).get("fingerprint")
    except (json.JSONDecodeError, KeyError):
        return None


def _save_fingerprint(fp: str) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"fingerprint": fp}))


def etl_needed() -> bool:
    if ETL_FORCE_RERUN:
        logger.info("ETL_FORCE_RERUN=true → ejecutando ETL")
        return True
    if not output_exists():
        logger.info("Output Parquet no existe → ejecutando ETL")
        return True
    if _compute_fingerprint() != _load_fingerprint():
        logger.info("Cambios detectados en Transactions/ → ejecutando ETL")
        return True
    logger.info("Datos procesados actualizados, ETL no necesario")
    return False


def run_etl(loop: asyncio.AbstractEventLoop | None = None) -> None:
    from backend.websocket import manager as ws_manager, db as ws_db

    logger.info("Iniciando ETL pipeline")
    job_id = ws_db.insert_job("ETL")

    def _broadcast(data: dict) -> None:
        if loop is not None:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    _broadcast({"type": "ETL", "status": "running", "job_id": job_id})

    try:
        fp = _compute_fingerprint()
        spark = get_spark_session(SPARK_MASTER_URL, SPARK_APP_NAME)

        df_tx = read_transactions(spark)
        df_pc = read_product_category(spark)
        df_cat = read_categories(spark)

        df_enriched = run_transformations(df_tx, df_pc, df_cat)
        write_transactions_enriched(df_enriched)

        from backend.eda_kpis.cache import invalidate_all as _invalidate_kpis
        _invalidate_kpis()

        _save_fingerprint(fp)
        ws_db.update_job(job_id, "completed")
        _broadcast({"type": "ETL", "status": "completed", "job_id": job_id})
        logger.info("ETL pipeline completado exitosamente")

    except Exception as exc:
        ws_db.update_job(job_id, "failed", str(exc))
        _broadcast({"type": "ETL", "status": "failed", "job_id": job_id, "message": str(exc)})
        logger.error("ETL pipeline falló: %s", exc, exc_info=True)
        raise


async def run_etl_async(loop: asyncio.AbstractEventLoop | None = None) -> None:
    _loop = loop or asyncio.get_event_loop()
    await asyncio.to_thread(run_etl, _loop)
    from backend.eda_kpis.router import run_kpis_sync
    asyncio.create_task(asyncio.to_thread(run_kpis_sync, _loop))
