from __future__ import annotations
import logging

from backend.config import TRANSACTIONS_DIR
from backend.dispatcher.dispatcher import run_etl_async

logger = logging.getLogger(__name__)


async def watch_and_rerun_etl() -> None:
    """
    Monitorea Transactions/ con watchfiles y re-ejecuta el ETL al detectar
    archivos *_Tran.csv nuevos o modificados.

    Diseñado para correr como asyncio.create_task() en el lifespan de FastAPI.
    Continúa vigilando aunque el ETL falle en una iteración.
    Se cancela automáticamente en el shutdown de FastAPI (CancelledError).
    """
    try:
        from watchfiles import awatch, Change
    except ImportError:
        logger.warning("watchfiles no disponible — watcher de archivos desactivado")
        return

    logger.info("Watcher iniciado en: %s", TRANSACTIONS_DIR)

    async for changes in awatch(str(TRANSACTIONS_DIR)):
        relevant = [
            (ct, p) for ct, p in changes
            if p.endswith("_Tran.csv") and ct in (Change.added, Change.modified)
        ]
        if not relevant:
            continue

        logger.info("Cambios detectados: %s", relevant)
        try:
            await run_etl_async()
            logger.info("Re-ejecución ETL por watcher completada")
        except Exception as exc:
            logger.error("Error en re-ejecución ETL: %s", exc, exc_info=True)
