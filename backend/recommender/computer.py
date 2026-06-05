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
    KMEANS_FULL_ASSIGNMENTS_FILE,
    RECOMMENDER_CACHE_DIR,
)

logger = logging.getLogger(__name__)


def _find_spark_submit() -> str:
    venv_spark = Path(sys.executable).parent / "spark-submit"
    if venv_spark.exists():
        return str(venv_spark)
    on_path = shutil.which("spark-submit")
    if on_path:
        return on_path
    return ""


def run_recommender_sync(loop: asyncio.AbstractEventLoop) -> None:
    from backend.websocket import manager as ws_manager, db as ws_db

    job_id = ws_db.insert_job("Recomendador")

    def _broadcast(data: dict) -> None:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    _broadcast({"type": "Recomendador", "status": "running", "job_id": job_id})
    logger.info("Lanzando job Recomendador (job_id=%d)", job_id)

    # Verificar dependencia: KMeans debe haber corrido primero
    full_assignments = KMEANS_CACHE_DIR / KMEANS_FULL_ASSIGNMENTS_FILE
    if not full_assignments.exists():
        msg = "K-Means debe ejecutarse antes del Recomendador (falta full_cluster_assignments.json)"
        ws_db.update_job(job_id, "failed", msg)
        _broadcast({"type": "Recomendador", "status": "failed", "job_id": job_id, "message": msg})
        logger.error(msg)
        return

    job_script = PROJECT_ROOT / "spark_jobs" / "recommender_job.py"
    spark_submit = _find_spark_submit()

    if spark_submit:
        cmd = [
            spark_submit,
            "--master", SPARK_MASTER_URL,
            "--driver-memory", "2g",
            str(job_script),
            "--input-dir",  str(TRANSACTIONS_ENRICHED_DIR),
            "--kmeans-dir", str(KMEANS_CACHE_DIR),
            "--output-dir", str(RECOMMENDER_CACHE_DIR),
            "--master", SPARK_MASTER_URL,
        ]
        logger.info("Usando spark-submit: %s", spark_submit)
    else:
        cmd = [
            sys.executable,
            str(job_script),
            "--input-dir",  str(TRANSACTIONS_ENRICHED_DIR),
            "--kmeans-dir", str(KMEANS_CACHE_DIR),
            "--output-dir", str(RECOMMENDER_CACHE_DIR),
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
        # Escribir log completo a disco — el tail puede ocultar errores largos de Java
        log_path = RECOMMENDER_CACHE_DIR / "last_run.log"
        RECOMMENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"exit_code={proc.returncode}\n\n--- STDERR ---\n{proc.stderr or ''}\n\n--- STDOUT ---\n{proc.stdout or ''}"
        )

        if proc.returncode == 0:
            from backend.recommender.cache import invalidate_customer_recs_cache
            invalidate_customer_recs_cache()
            ws_db.update_job(job_id, "completed")
            _broadcast({"type": "Recomendador", "status": "completed", "job_id": job_id})
            logger.info("Recomendador completado (job_id=%d)", job_id)
        else:
            # exit_code=137 → OOM kill (SIGKILL del kernel); log completo queda en last_run.log
            exit_note = f"[exit_code={proc.returncode}] "
            error_tail = exit_note + (proc.stderr[-4000:] if proc.stderr else "Sin stderr")
            ws_db.update_job(job_id, "failed", error_tail)
            _broadcast({
                "type": "Recomendador", "status": "failed",
                "job_id": job_id, "message": error_tail,
            })
            logger.error(
                "Recomendador falló (job_id=%d, exit=%d). Log completo: %s\n%s",
                job_id, proc.returncode, log_path, error_tail,
            )
    except Exception as exc:
        msg = str(exc)
        ws_db.update_job(job_id, "failed", msg)
        _broadcast({"type": "Recomendador", "status": "failed", "job_id": job_id, "message": msg})
        logger.error("Error al lanzar Recomendador: %s", exc, exc_info=True)
