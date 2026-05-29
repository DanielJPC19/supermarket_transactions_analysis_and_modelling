from __future__ import annotations
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from backend.config import (
    KPIS_CACHE_DIR,
    KPI_TOTAL_VENTAS, KPI_TOTAL_TRANSACCIONES, KPI_TOP10_PRODUCTOS,
    KPI_TOP10_CLIENTES, KPI_DIAS_PICO, KPI_CATEGORIAS,
    CHART_SERIE_TIEMPO, CHART_BOXPLOT, CHART_HEATMAP,
)

logger = logging.getLogger(__name__)

_ALL_FILES = [
    KPI_TOTAL_VENTAS, KPI_TOTAL_TRANSACCIONES, KPI_TOP10_PRODUCTOS,
    KPI_TOP10_CLIENTES, KPI_DIAS_PICO, KPI_CATEGORIAS,
    CHART_SERIE_TIEMPO, CHART_BOXPLOT, CHART_HEATMAP,
]


def _path(filename: str) -> Path:
    return KPIS_CACHE_DIR / filename


def save(filename: str, data: Any) -> None:
    """Serializa data como JSON y lo escribe en KPIS_CACHE_DIR/filename."""
    KPIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = _path(filename)
    target.write_text(json.dumps(data, ensure_ascii=False, default=str))
    logger.info("Cache escrito: %s", target.name)


def load(filename: str) -> Any | None:
    """Lee y deserializa el JSON. Retorna None si no existe o está corrupto."""
    p = _path(filename)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache corrupto (%s): %s", filename, exc)
        return None


def is_cached(filename: str) -> bool:
    return _path(filename).exists()


def invalidate_all() -> None:
    """Borra todo el directorio de cache KPIs. Llamar después de re-ejecutar ETL."""
    if KPIS_CACHE_DIR.exists():
        shutil.rmtree(KPIS_CACHE_DIR)
        logger.info("Cache KPIs invalidado")


def all_kpis_cached() -> bool:
    """True si todos los archivos de cache existen (cache warm)."""
    return all(is_cached(f) for f in _ALL_FILES)
