from __future__ import annotations
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from backend.config import (
    KMEANS_CACHE_DIR,
    KMEANS_ASSIGNMENTS_FILE,
    KMEANS_PROFILES_FILE,
    KMEANS_METRICS_FILE,
)

logger = logging.getLogger(__name__)

_ALL_FILES = [KMEANS_ASSIGNMENTS_FILE, KMEANS_PROFILES_FILE, KMEANS_METRICS_FILE]


def _path(filename: str) -> Path:
    return KMEANS_CACHE_DIR / filename


def save(filename: str, data: Any) -> None:
    KMEANS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = _path(filename)
    target.write_text(json.dumps(data, ensure_ascii=False, default=str))
    logger.info("Cache K-Means escrito: %s", target.name)


def load(filename: str) -> Any | None:
    p = _path(filename)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache K-Means corrupto (%s): %s", filename, exc)
        return None


def is_cached(filename: str) -> bool:
    return _path(filename).exists()


def all_kmeans_cached() -> bool:
    return all(is_cached(f) for f in _ALL_FILES)


def invalidate() -> None:
    if KMEANS_CACHE_DIR.exists():
        shutil.rmtree(KMEANS_CACHE_DIR)
        logger.info("Cache K-Means invalidado")
