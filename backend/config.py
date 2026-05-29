from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Raíz del proyecto: backend/config.py → backend/ → proyecto/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Spark ────────────────────────────────────────────────────────────────────
SPARK_MASTER_URL: str = os.getenv("SPARK_MASTER_URL", "local[*]")
SPARK_APP_NAME: str = os.getenv("SPARK_APP_NAME", "SupermercadoETL")

# ── Dataset crudo ────────────────────────────────────────────────────────────
DATASET_DIR: Path = PROJECT_ROOT / os.getenv("DATASET_DIR", "DataSet/DataSet")
TRANSACTIONS_DIR: Path = DATASET_DIR / os.getenv("TRANSACTIONS_SUBDIR", "Transactions")
_products_dir: Path = DATASET_DIR / os.getenv("PRODUCTS_SUBDIR", "Products")
PRODUCT_CATEGORY_FILE: Path = _products_dir / "ProductCategory.csv"
CATEGORIES_FILE: Path = _products_dir / "Categories.csv"

# ── Datos procesados (Bucket de Datos) ───────────────────────────────────────
PROCESSED_DIR: Path = PROJECT_ROOT / os.getenv("PROCESSED_DIR", "data/processed")
TRANSACTIONS_ENRICHED_DIR: Path = PROCESSED_DIR / "transactions_enriched"

# ── ETL ──────────────────────────────────────────────────────────────────────
ETL_FORCE_RERUN: bool = os.getenv("ETL_FORCE_RERUN", "false").lower() == "true"

# ── API ──────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ── KPIs Cache ───────────────────────────────────────────────────────────────
KPIS_CACHE_DIR: Path = PROCESSED_DIR / "kpis"

# ── Jobs DB (estado de jobs ETL/KPIs — separado del bucket de datos) ─────────
JOBS_DB_PATH: Path = PROJECT_ROOT / "data" / "jobs.db"

KPI_TOTAL_VENTAS        = "total_ventas.json"
KPI_TOTAL_TRANSACCIONES = "total_transacciones.json"
KPI_TOP10_PRODUCTOS     = "top10_productos.json"
KPI_TOP10_CLIENTES      = "top10_clientes.json"
KPI_DIAS_PICO           = "dias_pico.json"
KPI_CATEGORIAS          = "categorias_rentables.json"
CHART_SERIE_TIEMPO      = "chart_serie_tiempo.json"
CHART_BOXPLOT           = "chart_boxplot.json"
CHART_HEATMAP           = "chart_heatmap.json"
