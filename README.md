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
Frontend React (Vite — puerto 5173)
        ↕  WebSocket ws://localhost:8000/ws/jobs
        ↕  HTTP REST  http://localhost:8000
    Back-end  (monolito modular — FastAPI)
    ├── etl/          →  Ingesta y transformación de datos
    ├── dispatcher/   →  Orquestación de jobs Spark + watcher de archivos
    ├── eda_kpis/     →  Cómputo de KPIs y generación de visualizaciones
    └── websocket/    →  ConnectionManager + SQLite de estado de jobs
              ↕
    spark_jobs/       →  SparkSession (local[*] o cluster externo)
              ↕
    Spark Master + Driver → Workers
```

Los datos procesados se almacenan como **Parquet particionado** en `data/processed/transactions_enriched/` (simula el Bucket de Datos de la arquitectura). Los KPIs calculados se cachean como JSON en `data/processed/kpis/`. El estado de los jobs ETL y KPIs se persiste en `data/jobs.db` (SQLite, separado del bucket).

---

## Requisitos del sistema

| Requisito | Versión mínima |
|-----------|---------------|
| Python | 3.11+ (probado en 3.14.4) |
| Java | 11+ (requerido por Apache Spark) |
| Node.js | 18+ (requerido por el frontend React) |
| RAM | 4 GB mínimo, 8 GB recomendado |
| Disco | ~2 GB para los datos procesados |

Verificar las dependencias de sistema:

```bash
java -version
node --version   # debe ser v18+
npm --version
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

**Backend (Python):**

| Librería | Versión | Rol |
|----------|---------|-----|
| `pyspark` | 4.1.1 | Procesamiento distribuido de datos |
| `fastapi` | 0.136.1 | API REST + WebSocket |
| `uvicorn` | 0.47.0 | Servidor ASGI |
| `plotly` | 5.24.1 | Generación de visualizaciones interactivas |
| `pandas` | 3.0.3 | Puente Spark → Plotly para charts |
| `python-dotenv` | 1.2.2 | Gestión de variables de entorno |
| `numpy` | 2.4.3 | Cómputo numérico (correlaciones) |

**Frontend (Node.js — instalar por separado):**

| Paquete | Rol |
|---------|-----|
| `react` + `react-dom` | Framework UI |
| `vite` | Build tool y dev server |
| `@mui/material` + `@emotion/*` | Componentes Material UI |
| `@mui/icons-material` | Iconografía MUI |
| `plotly.js` | Renderizado de figuras Plotly en el browser |

> Node.js 18+ requerido para el frontend. Verificar: `node --version`

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

1. **Inicializa la base de datos de jobs** — crea `data/jobs.db` (SQLite) si no existe.
2. **Verifica si el ETL es necesario** — compara un fingerprint (nombre + tamaño + fecha de modificación) de los archivos en `Transactions/` con el estado guardado. Si hay cambios o es la primera ejecución, lanza el ETL.
3. **ETL (si es necesario)** — lee los CSV crudos, transforma y enriquece los datos con PySpark, y guarda el resultado como Parquet en `data/processed/transactions_enriched/` particionado por `sucursal_id`. El estado del job se registra en `data/jobs.db` y se transmite por WebSocket en tiempo real.
4. **Cómputo de KPIs** — si el cache de KPIs no está disponible, lanza en background el cómputo de los 9 indicadores y charts con PySpark (~3–8 minutos en local). Los resultados se guardan en `data/processed/kpis/`. El estado también se registra en `data/jobs.db` y se transmite por WebSocket.
5. **Watcher de archivos** — inicia un proceso en background que monitorea `DataSet/DataSet/Transactions/`. Si detecta un nuevo archivo `*_Tran.csv`, re-ejecuta el ETL y el cómputo de KPIs automáticamente.

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

## Dashboard (Frontend React)

Abrir en el navegador: **`http://localhost:5173`** (requiere el backend corriendo en el puerto 8000).

El frontend está construido en **React + Vite** con **Material UI** y se comunica con el backend vía HTTP REST y WebSocket.

### Navegación — Barra lateral

La interfaz cuenta con una barra lateral permanente con las siguientes secciones:

| Sección | Estado | Descripción |
|---------|--------|-------------|
| **ETL** | Activo | Panel de gestión del ETL: estado en tiempo real + botón de trigger |
| **EDA + KPIs** | Activo | Dashboard analítico completo |
| **K-Means** | Próximamente | Segmentación de clientes |
| **Recomendador** | Próximamente | Sistema de recomendación de productos |

### Sección: Gestión del ETL

Muestra en tiempo real (via WebSocket) el estado de los dos jobs del sistema:

- **Estado del ETL** — `running` / `completed` / `failed`, con timestamps de inicio y fin
- **Estado del cómputo de KPIs** — misma información para el job de KPIs
- **Botón "Ejecutar ETL"** — lanza manualmente el ETL completo en background (equivalente a `POST /etl/trigger`)

Los estados se persisten en `data/jobs.db` y se actualizan automáticamente al conectar y durante la ejecución.

### Sección: EDA + KPIs — Resumen Ejecutivo

| Indicador | Descripción | Tipo de gráfico |
|-----------|-------------|-----------------|
| Total unidades vendidas | Suma de todas las unidades compradas en el período | KPI card numérico |
| Total transacciones | Visitas únicas (fecha + sucursal + cliente) | KPI card numérico |
| Clientes únicos | Total de clientes distintos | KPI card estático |
| Productos únicos | Total de productos distintos | KPI card estático |
| Top 10 productos | Productos más comprados por volumen | Barras horizontales |
| Top 10 clientes | Clientes con más transacciones | Barras horizontales |
| Top 30 días pico | Días con mayor actividad, coloreados por día de semana | Barras verticales |
| Categorías rentables | Categorías con ≥ 3% del volumen total; el resto agrupado como "Otros" | Torta (solo colores + hover) |

### Sección: EDA + KPIs — Visualizaciones Analíticas

| Visualización | Descripción |
|---------------|-------------|
| Serie de tiempo | Transacciones diarias (Ene–Jun 2013) con media móvil de 7 días superpuesta |
| Boxplot | Distribución de unidades compradas por cliente (131,186 clientes), con media y outliers |
| Heatmap de correlación | Matriz de Pearson 4×4 entre: frecuencia, total cantidad, productos distintos y categorías distintas por cliente |

### Comportamiento de actualización

- Al cargar la página, el dashboard hace polling a `/analytics/status` cada 15 s (configurable con `VITE_POLL_INTERVAL_MS`) hasta que el cache de KPIs esté warm.
- Cuando el job de KPIs completa, el backend notifica vía WebSocket y el dashboard recarga los charts automáticamente sin intervención del usuario.
- Máximo de reintentos de polling: 30 (configurable con `VITE_MAX_RETRIES`), equivalente a ~7.5 minutos.

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

### WebSocket — Estado de jobs en tiempo real

| Protocolo | Ruta | Descripción |
|-----------|------|-------------|
| `WS` | `/ws/jobs` | Stream de estado de jobs ETL y KPIs |

Al conectar, el servidor envía el historial reciente de jobs (últimas 20 entradas de `data/jobs.db`). Cada evento posterior tiene la forma:

```json
{"type": "ETL", "status": "running", "job_id": 5}
{"type": "ETL", "status": "completed", "job_id": 5}
{"type": "KPIs", "status": "failed", "job_id": 6, "message": "..."}
```

Valores posibles de `status`: `running` · `completed` · `failed`

Valores posibles de `type`: `ETL` · `KPIs`

La conexión se reconecta automáticamente cada 3 s si se pierde.

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
| `GET` | `/analytics/charts/categorias` | Torta — Categorías (umbral 3%, "Otros" agrupa el resto) |
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
│   ├── main.py                     # Entry point: lifespan, CORS, WebSocket endpoint
│   ├── config.py                   # Constantes centralizadas (paths, env vars, JOBS_DB_PATH)
│   ├── etl/                        # Módulo ETL
│   │   ├── reader.py               # Lee CSV crudos con schema explícito
│   │   ├── transformer.py          # Parsea, explota productos, enriquece con categorías
│   │   └── writer.py               # Escribe Parquet particionado por sucursal_id
│   ├── dispatcher/                 # Módulo Dispatcher Spark
│   │   ├── dispatcher.py           # Fingerprint, ETL needed, notificaciones WS
│   │   └── watcher.py              # Watcher async de nuevos archivos (watchfiles)
│   ├── eda_kpis/                   # Módulo EDA + KPIs
│   │   ├── computer.py             # 9 cómputos PySpark (KPIs + datasets para charts)
│   │   ├── charts.py               # 7 figuras Plotly (fig.to_json())
│   │   ├── cache.py                # Lectura/escritura JSON en disco
│   │   └── router.py               # APIRouter /analytics/* + run_kpis_sync() + notif. WS
│   └── websocket/                  # Módulo WebSocket
│       ├── manager.py              # ConnectionManager (broadcast a clientes conectados)
│       └── db.py                   # SQLite: init_db, insert_job, update_job, get_recent_jobs
├── frontend/                       # App React — dashboard independiente
│   ├── .env                        # VITE_API_URL, VITE_POLL_INTERVAL_MS, VITE_MAX_RETRIES
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                # Entry React
│       ├── App.jsx                 # Layout MUI: sidebar + sección ETL + sección EDA
│       ├── App.css                 # Estilos mínimos custom
│       ├── api/
│       │   └── analytics.js        # Capa fetch hacia /analytics/*
│       ├── hooks/
│       │   └── useJobStatus.js     # WebSocket hook: conecta a /ws/jobs, reconexión automática
│       └── components/
│           ├── Sidebar.jsx         # MUI Drawer — navegación principal
│           ├── KpiCard.jsx         # MUI Card con número formateado (es-CO)
│           ├── PlotlyChart.jsx     # Fetch + Plotly.newPlot() directo (sin react-plotly.js)
│           └── StatusBadge.jsx     # MUI Chip: running/completed/failed
├── spark_jobs/
│   └── session.py                  # SparkSession singleton (local[*] o cluster)
├── DataSet/DataSet/                # Datos crudos
│   ├── Transactions/               # *_Tran.csv por sucursal
│   └── Products/                   # Categories.csv, ProductCategory.csv
└── data/                           # Datos generados (no versionar)
    ├── jobs.db                     # SQLite — historial de jobs ETL y KPIs
    └── processed/
        ├── .etl_state.json         # Fingerprint del último ETL exitoso
        ├── transactions_enriched/  # Parquet particionado por sucursal_id
        └── kpis/                   # Cache JSON de KPIs y charts Plotly
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