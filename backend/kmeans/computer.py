from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from backend.config import (
    PROJECT_ROOT,
    SPARK_MASTER_URL,
    TRANSACTIONS_ENRICHED_DIR,
    KMEANS_CACHE_DIR,
)

logger = logging.getLogger(__name__)


def _find_spark_submit() -> str:
    # Prioridad: spark-submit del venv actual → PATH → python fallback
    venv_spark = Path(sys.executable).parent / "spark-submit"
    if venv_spark.exists():
        return str(venv_spark)
    on_path = shutil.which("spark-submit")
    if on_path:
        return on_path
    return ""  # vacío → fallback a python


def run_kmeans_sync(loop: asyncio.AbstractEventLoop) -> None:
    from backend.websocket import manager as ws_manager, db as ws_db

    job_id = ws_db.insert_job("KMeans")

    def _broadcast(data: dict) -> None:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    _broadcast({"type": "KMeans", "status": "running", "job_id": job_id})
    logger.info("Lanzando job K-Means (job_id=%d)", job_id)

    job_script = PROJECT_ROOT / "spark_jobs" / "kmeans_job.py"
    spark_submit = _find_spark_submit()

    if spark_submit:
        cmd = [
            spark_submit,
            "--master", SPARK_MASTER_URL,
            "--driver-memory", "2g",
            str(job_script),
            "--input-dir", str(TRANSACTIONS_ENRICHED_DIR),
            "--output-dir", str(KMEANS_CACHE_DIR),
            "--master", SPARK_MASTER_URL,
        ]
        logger.info("Usando spark-submit: %s", spark_submit)
    else:
        cmd = [
            sys.executable,
            str(job_script),
            "--input-dir", str(TRANSACTIONS_ENRICHED_DIR),
            "--output-dir", str(KMEANS_CACHE_DIR),
            "--master", SPARK_MASTER_URL,
        ]
        logger.info("spark-submit no encontrado → usando python directo")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        if proc.returncode == 0:
            ws_db.update_job(job_id, "completed")
            _broadcast({"type": "KMeans", "status": "completed", "job_id": job_id})
            logger.info("K-Means completado (job_id=%d)", job_id)
        else:
            error_tail = proc.stderr[-800:] if proc.stderr else "Sin stderr"
            ws_db.update_job(job_id, "failed", error_tail)
            _broadcast({
                "type": "KMeans", "status": "failed",
                "job_id": job_id, "message": error_tail,
            })
            logger.error("K-Means falló (job_id=%d):\n%s", job_id, error_tail)
    except Exception as exc:
        msg = str(exc)
        ws_db.update_job(job_id, "failed", msg)
        _broadcast({"type": "KMeans", "status": "failed", "job_id": job_id, "message": msg})
        logger.error("Error al lanzar K-Means: %s", exc, exc_info=True)
