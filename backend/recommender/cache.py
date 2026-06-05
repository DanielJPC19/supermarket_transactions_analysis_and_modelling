from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from backend.config import (
    RECOMMENDER_CACHE_DIR,
    REC_CUSTOMER_RECS_FILE,
    REC_PRODUCT_COOC_FILE,
    REC_EVAL_METRICS_FILE,
)

_logger = logging.getLogger(__name__)
_REQUIRED_FILES = [REC_CUSTOMER_RECS_FILE, REC_PRODUCT_COOC_FILE, REC_EVAL_METRICS_FILE]

_customer_recs_cache: dict | None = None


def is_cached(filename: str) -> bool:
    return (RECOMMENDER_CACHE_DIR / filename).exists()


def all_cached() -> bool:
    return all(is_cached(f) for f in _REQUIRED_FILES)


def load(filename: str):
    path = RECOMMENDER_CACHE_DIR / filename
    return json.loads(path.read_text())


def load_customer_recs() -> dict:
    """Carga customer_recommendations.json una sola vez y lo mantiene en memoria."""
    global _customer_recs_cache
    if _customer_recs_cache is None:
        path = RECOMMENDER_CACHE_DIR / REC_CUSTOMER_RECS_FILE
        _customer_recs_cache = json.loads(path.read_text())
        _logger.info(
            "customer_recommendations.json cargado en memoria (%d clientes)",
            len(_customer_recs_cache),
        )
    return _customer_recs_cache


def invalidate_customer_recs_cache() -> None:
    global _customer_recs_cache
    _customer_recs_cache = None


def save(filename: str, data) -> None:
    RECOMMENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (RECOMMENDER_CACHE_DIR / filename).write_text(json.dumps(data, ensure_ascii=False))


def invalidate() -> None:
    invalidate_customer_recs_cache()
    if RECOMMENDER_CACHE_DIR.exists():
        shutil.rmtree(RECOMMENDER_CACHE_DIR)
