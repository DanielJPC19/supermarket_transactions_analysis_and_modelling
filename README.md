# Proyecto Final Procesamiento Distribuido de Datos

Análisis y Modelado Analítico de Transacciones de Supermercado

## Información del Estudiante

**Nombre:** Daniel José Plazas Cortés

**Código:** A00400085

## Dudas del proyecto

### Carga de datos
Cada archivo es una sucursal. Ante un nuevo archivo (nueva sucursal), el sistema genera resultados nuevos de manera general, realizando todo el análisis. **El usuario final no realiza la carga de datos**. Este análisis de los nuevos datos se realizan desde el back, y al estar disponibles, podrán ser visibles desde el front.


### Estructura documento transacciones
`fecha, compra, sucursal, numero de clientes, productos comprados`

> Mesaje del profe: 3. La estructura de las transacciones: `fecha | sucursal | id_cliente | listado de productos comprados en ese momento`

---

## Arquitectura del sistema

El sistema está compuesto por tres capas principales:

```
Web Server (Front-end)
        ↕  WebSocket / HTTP
    Back-end  (monolito modular — FastAPI)
    ├── etl/          →  Ingesta y transformación de datos
    ├── dispatcher/   →  Orquestación de jobs Spark + watcher de archivos
    ├── eda_kpis/     →  Cómputo de KPIs y generación de visualizaciones
    └── websocket/    →  (futuro) comunicación en tiempo real
              ↕
    spark_jobs/       →  SparkSession (local[*] o cluster externo)
              ↕
    Spark Master + Driver → Workers
```

Los datos procesados se almacenan como **Parquet particionado** en `data/processed/transactions_enriched/` (simula el Bucket de Datos de la arquitectura). Los KPIs calculados se cachean como JSON en `data/processed/kpis/`.

---

## Requisitos del sistema

| Requisito | Versión mínima |
|-----------|---------------|
| Python | 3.11+ (probado en 3.14.4) |
| Java | 11+ (requerido por Apache Spark) |
| RAM | 4 GB mínimo, 8 GB recomendado |
| Disco | ~2 GB para los datos procesados |

Verificar que Java esté instalado:

```bash
java -version
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/DanielJPC19/supermarket_transactions_analysis_and_modelling.git
cd supermarket_transactions_analysis_and_modelling
```

### 2. Crear y activar el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:

| Librería | Versión | Rol |
|----------|---------|-----|
| `pyspark` | 4.1.1 | Procesamiento distribuido de datos |
| `fastapi` | 0.136.1 | API REST y servidor web |
| `uvicorn` | 0.47.0 | Servidor ASGI |
| `plotly` | 5.24.1 | Generación de visualizaciones interactivas |
| `pandas` | 3.0.3 | Puente Spark → Plotly para charts |
| `python-dotenv` | 1.2.2 | Gestión de variables de entorno |
| `numpy` | 2.4.3 | Cómputo numérico (correlaciones) |

### 4. Configurar variables de entorno

El proyecto usa **dos archivos `.env` independientes**: uno para el backend y otro para el frontend.

#### `.env` — Backend (raíz del proyecto)

Leído por `backend/config.py` vía `python-dotenv`. Agrupa las variables en tres secciones:

```ini
# ── Spark ────────────────────────────────────────────────────────────────────
SPARK_MASTER_URL=local[*]     # local[*] = todos los cores; spark://host:7077 para cluster
SPARK_APP_NAME=SupermercadoETL

# ── Rutas del dataset crudo (relativas a la raíz del proyecto) ───────────────
DATASET_DIR=DataSet/DataSet
TRANSACTIONS_SUBDIR=Transactions
PRODUCTS_SUBDIR=Products

# ── Almacenamiento procesado + comportamiento ETL + API ──────────────────────
PROCESSED_DIR=data/processed
ETL_FORCE_RERUN=false         # true = fuerza re-ejecución aunque el output ya exista
API_HOST=0.0.0.0
API_PORT=8000
```

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `SPARK_MASTER_URL` | Modo de ejecución Spark | `local[*]` |
| `SPARK_APP_NAME` | Nombre de la aplicación Spark | `SupermercadoETL` |
| `DATASET_DIR` | Ruta al directorio del dataset crudo | `DataSet/DataSet` |
| `TRANSACTIONS_SUBDIR` | Subdirectorio con los CSV de transacciones | `Transactions` |
| `PRODUCTS_SUBDIR` | Subdirectorio con los CSV de productos | `Products` |
| `PROCESSED_DIR` | Directorio de datos procesados (Parquet + cache KPIs) | `data/processed` |
| `ETL_FORCE_RERUN` | Forzar re-ejecución del ETL en cada arranque | `false` |
| `API_HOST` | Host donde escucha Uvicorn | `0.0.0.0` |
| `API_PORT` | Puerto de la API | `8000` |

#### `frontend/.env` — Frontend (directorio `frontend/`)

Leído por **Vite** durante el build y en desarrollo. Solo las variables con prefijo `VITE_` quedan expuestas en el bundle del navegador.

```ini
# ── Conexión con el backend ───────────────────────────────────────────────────
VITE_API_URL=http://localhost:8000

# ── Comportamiento del dashboard ─────────────────────────────────────────────
VITE_POLL_INTERVAL_MS=15000   # ms entre reintentos mientras el cache no está warm
VITE_MAX_RETRIES=30           # máximo de reintentos automáticos (~7.5 min)
```

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `VITE_API_URL` | URL base del backend FastAPI | `http://localhost:8000` |
| `VITE_POLL_INTERVAL_MS` | Intervalo de polling de estado (ms) | `15000` |
| `VITE_MAX_RETRIES` | Reintentos máximos antes de detener el polling | `30` |

> **Deployment:** Para apuntar el frontend a un backend en otro servidor, cambiar `VITE_API_URL` y reconstruir con `npm run build`. Las variables `VITE_*` se embeben en el bundle estático en tiempo de build.

### 5. Ubicar el dataset

El dataset debe estar en la siguiente estructura (ya incluida en el repo):

```
DataSet/DataSet/
├── Transactions/
│   ├── 102_Tran.csv       # Sucursal 102 — 314,286 transacciones
│   ├── 103_Tran.csv       # Sucursal 103 — 407,130 transacciones
│   ├── 107_Tran.csv       # Sucursal 107 — 254,633 transacciones
│   └── 110_Tran.csv       # Sucursal 110 — 132,938 transacciones
└── Products/
    ├── Categories.csv     # 49 categorías de productos
    └── ProductCategory.csv  # Mapeo producto → categoría (112,010 entradas)
```

**Formato de los archivos de transacciones** (sin encabezado, separador `|`):

```
fecha|sucursal_id|cliente_id|lista_de_producto_ids_separados_por_espacio
2013-01-01|102|530|20 3 1
2013-01-01|102|587|6 29 43 21 34 2 10 32
```

---

## Ejecución

El sistema tiene dos procesos independientes que deben correr en paralelo: el **backend** (FastAPI + PySpark) y el **frontend** (React + Vite).

### Terminal 1 — Backend (API + procesamiento)

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Al arrancar, el servidor ejecuta automáticamente los siguientes pasos en orden:

1. **Verifica si el ETL es necesario** — compara un fingerprint (nombre + tamaño + fecha de modificación) de los archivos en `Transactions/` con el estado guardado. Si hay cambios o es la primera ejecución, lanza el ETL.
2. **ETL (si es necesario)** — lee los CSV crudos, transforma y enriquece los datos con PySpark, y guarda el resultado como Parquet en `data/processed/transactions_enriched/` particionado por `sucursal_id`.
3. **Cómputo de KPIs** — si el cache de KPIs no está disponible, lanza en background el cómputo de los 9 indicadores y charts con PySpark (~3–8 minutos en local). Los resultados se guardan en `data/processed/kpis/`.
4. **Watcher de archivos** — inicia un proceso en background que monitorea `DataSet/DataSet/Transactions/`. Si detecta un nuevo archivo `*_Tran.csv`, re-ejecuta el ETL y el cómputo de KPIs automáticamente.

> **Nota sobre tiempos:** El ETL sobre 1.1 millones de transacciones tarda ~2–4 minutos en `local[*]`. El cómputo de KPIs sobre los ~10.5 millones de filas enriquecidas tarda ~3–8 minutos adicionales. En ejecuciones posteriores, ambos pasos se omiten si los datos no cambiaron.

### Terminal 2 — Frontend (React)

```bash
cd frontend
npm install      # solo la primera vez
npm run dev
```

El dashboard estará disponible en **`http://localhost:5173`**.

> La app React se conecta automáticamente a `http://localhost:8000`. Si el backend está en otro host/puerto, editar `frontend/.env`:
> ```ini
> VITE_API_URL=http://mi-servidor:8000
> ```

### Build de producción del frontend

```bash
cd frontend
npm run build    # genera frontend/dist/
```

Los archivos en `dist/` pueden servirse desde cualquier servidor estático (Nginx, S3, etc.).

---

## Dashboard

Abrir en el navegador: **`http://localhost:8000`**

El dashboard se actualiza automáticamente cada 15 segundos mientras el cómputo de KPIs está en progreso. El indicador en la barra superior muestra el estado:

- 🟡 **Computando KPIs...** — el cómputo está en progreso, los charts aparecerán progresivamente
- 🟢 **Cache actualizado** — todos los datos están disponibles

### Resumen Ejecutivo

| Indicador | Descripción | Tipo de gráfico |
|-----------|-------------|-----------------|
| Total unidades vendidas | Suma de todas las unidades compradas en el período | KPI card numérico |
| Total transacciones | Visitas únicas (fecha + sucursal + cliente) | KPI card numérico |
| Top 10 productos | Productos más comprados por volumen | Barras horizontales |
| Top 10 clientes | Clientes con más transacciones | Barras horizontales |
| Top 30 días pico | Días con mayor actividad, coloreados por día de semana | Barras verticales |
| Categorías rentables | Participación por volumen de cada categoría | Donut + barras |

### Visualizaciones Analíticas

| Visualización | Descripción |
|---------------|-------------|
| Serie de tiempo | Transacciones diarias (Ene–Jun 2013) con media móvil de 7 días superpuesta |
| Boxplot | Distribución de unidades compradas por cliente (131,186 clientes), con media y outliers |
| Heatmap de correlación | Matriz de Pearson 4×4 entre: frecuencia, total cantidad, productos distintos y categorías distintas por cliente |

---

## API REST

La API está disponible en `http://localhost:8000`. Documentación interactiva (Swagger): `http://localhost:8000/docs`.

### Endpoints de estado

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servidor |
| `GET` | `/etl/status` | Si el Parquet procesado existe |
| `POST` | `/etl/trigger` | Fuerza re-ejecución del ETL en background |
| `GET` | `/analytics/status` | Si el cache de KPIs está listo (`cache_warm`) |
| `POST` | `/analytics/compute` | Fuerza recomputo de todos los KPIs en background |

### Endpoints de KPIs (datos crudos JSON)

| Método | Ruta | Respuesta |
|--------|------|-----------|
| `GET` | `/analytics/kpis/total-ventas` | `{"value": 10591793}` |
| `GET` | `/analytics/kpis/total-transacciones` | `{"value": 1108951}` |
| `GET` | `/analytics/kpis/top10-productos` | Lista de 10 objetos con `producto_id`, `label`, `total_cantidad` |
| `GET` | `/analytics/kpis/top10-clientes` | Lista de 10 objetos con `cliente_id`, `label`, `n_transacciones` |
| `GET` | `/analytics/kpis/dias-pico` | Lista de 30 días con `fecha`, `n_transacciones`, `dia_semana` |
| `GET` | `/analytics/kpis/categorias` | Lista de categorías con `nombre_categoria`, `total_cantidad`, `pct` |

> Si el cache no está listo, los endpoints responden `HTTP 503` con un mensaje indicando que el cómputo está en progreso.

### Endpoints de charts (Plotly JSON)

Cada endpoint retorna un objeto JSON de figura Plotly listo para renderizar con `Plotly.newPlot()`.

| Método | Ruta | Chart |
|--------|------|-------|
| `GET` | `/analytics/charts/top10-productos` | Barras horizontales — Top 10 productos |
| `GET` | `/analytics/charts/top10-clientes` | Barras horizontales — Top 10 clientes |
| `GET` | `/analytics/charts/dias-pico` | Barras verticales — Días pico |
| `GET` | `/analytics/charts/categorias` | Donut + barras — Categorías |
| `GET` | `/analytics/charts/serie-tiempo` | Línea con área — Serie temporal diaria |
| `GET` | `/analytics/charts/boxplot` | Boxplot — Distribución por cliente |
| `GET` | `/analytics/charts/heatmap` | Heatmap — Correlación entre variables |

---

## Estructura del proyecto

```
proyecto/
├── .env                            # Variables de entorno backend (Spark, paths, API)
├── requirements.txt                # Dependencias Python
├── backend/                        # Monolito modular — FastAPI
│   ├── main.py                     # Entry point: lifespan, CORS, rutas API
│   ├── config.py                   # Constantes centralizadas (paths, env vars)
│   ├── etl/                        # Módulo ETL
│   │   ├── reader.py               # Lee CSV crudos con schema explícito
│   │   ├── transformer.py          # Parsea, explota productos, enriquece con categorías
│   │   └── writer.py               # Escribe Parquet particionado por sucursal_id
│   ├── dispatcher/                 # Módulo Dispatcher Spark
│   │   ├── dispatcher.py           # Fingerprint, lógica ETL needed, orquestación
│   │   └── watcher.py              # Watcher async de nuevos archivos (watchfiles)
│   ├── eda_kpis/                   # Módulo EDA + KPIs
│   │   ├── computer.py             # 9 cómputos PySpark (KPIs + datasets para charts)
│   │   ├── charts.py               # 7 figuras Plotly (fig.to_json())
│   │   ├── cache.py                # Lectura/escritura JSON en disco
│   │   └── router.py               # APIRouter /analytics/* + run_kpis_sync()
│   └── websocket/                  # Módulo WebSocket Manager (en desarrollo)
├── frontend/                       # App React — dashboard independiente
│   ├── .env                        # VITE_API_URL=http://localhost:8000
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                # Entry React
│       ├── App.jsx                 # Layout principal + polling de estado
│       ├── App.css                 # Estilos del dashboard
│       ├── api/
│       │   └── analytics.js        # Capa fetch hacia /analytics/*
│       └── components/
│           ├── KpiCard.jsx         # Card con número formateado
│           ├── PlotlyChart.jsx     # Fetch + render de figura Plotly
│           ├── StatusBadge.jsx     # Indicador verde/amarillo/rojo
│           └── Navbar.jsx          # Barra superior con estado
├── spark_jobs/
│   └── session.py                  # SparkSession singleton (local[*] o cluster)
├── DataSet/DataSet/                # Datos crudos
│   ├── Transactions/               # *_Tran.csv por sucursal
│   └── Products/                   # Categories.csv, ProductCategory.csv
└── data/processed/                 # Datos generados (no versionar)
    ├── .etl_state.json             # Fingerprint del último ETL exitoso
    ├── transactions_enriched/      # Parquet particionado por sucursal_id
    └── kpis/                       # Cache JSON de KPIs y charts Plotly
```

---

## Incorporación de nuevas sucursales

El sistema detecta y procesa automáticamente nuevos archivos de transacciones. Para agregar una nueva sucursal:

1. Copiar el archivo CSV de la nueva sucursal al directorio `DataSet/DataSet/Transactions/`. El nombre debe seguir el patrón `{id_sucursal}_Tran.csv` (ej. `115_Tran.csv`).
2. El watcher de archivos detecta el cambio en segundos y lanza automáticamente el ETL completo + recomputo de KPIs.
3. El dashboard se actualiza al terminar el cómputo (~5–10 minutos según el volumen de datos).

También se puede forzar manualmente:

```bash
curl -X POST http://localhost:8000/etl/trigger
```

---

## Deployment con cluster Spark

Para usar un cluster Spark real en lugar del modo local, cambiar en `.env`:

```ini
SPARK_MASTER_URL=spark://spark-master:7077
```

El resto del código no requiere cambios. La `SparkSession` en `spark_jobs/session.py` usa el `SPARK_MASTER_URL` configurado.

Para YARN o Kubernetes:

```ini
SPARK_MASTER_URL=yarn
# o
SPARK_MASTER_URL=k8s://https://kubernetes-api-server:6443
```

---

## Datos del dataset

| Métrica | Valor |
|---------|-------|
| Período temporal | 2013-01-01 → 2013-06-30 (6 meses) |
| Sucursales | 4 (102, 103, 107, 110) |
| Transacciones únicas | ~1,108,987 |
| Filas procesadas (post-ETL) | ~10,591,793 |
| Clientes únicos | 131,186 |
| Productos únicos | 449 |
| Categorías con nombre | 20 |
| Filas sin categoría | ~50% (productos sin mapeo en ProductCategory) |