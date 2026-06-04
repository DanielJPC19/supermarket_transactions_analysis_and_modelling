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
    ├── kmeans/       →  Segmentación de clientes (K-Means PySpark MLlib)
    └── websocket/    →  ConnectionManager + SQLite de estado de jobs
              ↕
    spark_jobs/       →  SparkSession (local[*] o cluster) + jobs standalone
    ├── session.py    →  SparkSession singleton compartida (ETL y KPIs)
    └── kmeans_job.py →  Job K-Means standalone (spark-submit ready)
              ↕
    Spark Master + Driver → Workers
```

Los datos procesados se almacenan como **Parquet particionado** en `data/processed/transactions_enriched/` (simula el Bucket de Datos de la arquitectura). Los KPIs calculados se cachean como JSON en `data/processed/kpis/`. Los resultados de K-Means se almacenan en `data/processed/kmeans/`. El estado de todos los jobs se persiste en `data/jobs.db` (SQLite, separado del bucket).

Antes de cada escritura Parquet, el dispatcher crea un backup en `data/processed/transactions_enriched_backup/` que permite rollback automático (en caso de fallo del ETL) o manual (desde el panel de gestión).

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
| `pyspark` | 4.1.1 | Procesamiento distribuido de datos (ETL, KPIs, K-Means MLlib) |
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
| `PROCESSED_DIR` | Directorio de datos procesados (Parquet + cache KPIs + K-Means) | `data/processed` |
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
3. **ETL (si es necesario)** — lee los CSV crudos, transforma y enriquece los datos con PySpark, y guarda el resultado como Parquet en `data/processed/transactions_enriched/` particionado por `sucursal_id`. Antes de sobreescribir, se crea un backup automático en `transactions_enriched_backup/`. El estado del job se registra en `data/jobs.db` y se transmite por WebSocket en tiempo real.
4. **Cómputo de KPIs** — si el cache de KPIs no está disponible, lanza en background el cómputo de los 9 indicadores y charts con PySpark (~3–8 minutos en local). Los resultados se guardan en `data/processed/kpis/`. El estado también se registra en `data/jobs.db` y se transmite por WebSocket.
5. **Watcher de archivos** — inicia un proceso en background que monitorea `DataSet/DataSet/Transactions/`. Si detecta un nuevo archivo `*_Tran.csv`, re-ejecuta el ETL y el cómputo de KPIs automáticamente.

> **Nota sobre tiempos:** El ETL sobre 1.1 millones de transacciones tarda ~2–4 minutos en `local[*]`. El cómputo de KPIs sobre los ~10.5 millones de filas enriquecidas tarda ~3–8 minutos adicionales. El K-Means evalúa 4 valores de K con MLlib y puede tardar ~5–15 minutos. En ejecuciones posteriores los dos primeros pasos se omiten si los datos no cambiaron.

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
| **ETL** | Activo | Panel de gestión del pipeline: 4 tarjetas de estado + trigger manual + rollback |
| **EDA + KPIs** | Activo | Dashboard analítico completo |
| **K-Means** | Activo | Segmentación de clientes con clustering distribuido |
| **Recomendador** | Próximamente | Sistema de recomendación de productos |

### Sección: Gestión del Pipeline (ETL)

Muestra en tiempo real (via WebSocket) el estado de todos los jobs del sistema, organizados en **cuatro tarjetas**:

| Tarjeta | Job monitoreado | Descripción |
|---------|----------------|-------------|
| Estado del ETL | `ETL` | Ingesta y transformación de datos crudos |
| Estado de KPIs | `KPIs` | Cómputo de indicadores y charts analíticos |
| Estado de K-Means | `KMeans` | Job de segmentación de clientes (spark-submit) |
| Estado del Recomendador | `Recomendador` | Sistema de recomendación (a implementar) |

Cada tarjeta muestra:
- **Badge de estado** en tiempo real: `Ejecutando…` / `Completado` / `Error` / `Rollback`
- **Inicio y fin** del job actual con timestamps en formato local (es-CO)
- **Último éxito**: fecha del último job que completó exitosamente para ese tipo

Acciones disponibles desde el panel:

- **Botón "Ejecutar ETL"** — lanza manualmente el ETL completo en background (equivalente a `POST /etl/trigger`). Deshabilitado mientras haya un ETL en ejecución.
- **Botón "Rollback a versión anterior"** — visible solo cuando hay un backup disponible (después de un ETL exitoso o tras un fallo que fue auto-restaurado). Restaura los datos Parquet previos e inicia el recomputo de KPIs. Ver [sección Rollback](#rollback-del-etl) para más detalles.

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

### Sección: K-Means — Segmentación de Clientes

La segmentación se ejecuta manualmente desde esta sección haciendo click en **"Ejecutar K-Means"**. El job corre como proceso Spark independiente (spark-submit) y emite estado por WebSocket.

**Visualizaciones disponibles** (aparecen al completar el análisis):

| Visualización | Tipo | Descripción |
|---------------|------|-------------|
| Proyección PCA 2D | Scatter | Clientes proyectados en 2 componentes principales, coloreados por cluster |
| Perfiles comparativos | Barras agrupadas | Media de cada feature por cluster, normalizada a [0–1] para comparación relativa |
| Distribución de tamaños | Torta | Proporción de clientes en cada cluster |
| Evaluación de K | Líneas dual-eje | Silhouette Score y WSSSE (curva del codo) para K ∈ {3, 4, 5, 6} |

**Tarjetas de perfil por cluster** — resumen de cada grupo con:
- Número de clientes
- Frecuencia de compra media
- Total unidades media
- Productos distintos media
- Categorías distintas media
- Tamaño de canasta medio

### Comportamiento de actualización

- Al cargar la página, el dashboard hace polling a `/analytics/status` cada 15 s (configurable con `VITE_POLL_INTERVAL_MS`) hasta que el cache de KPIs esté warm.
- Cuando cualquier job completa, el backend notifica vía WebSocket y el dashboard reacciona automáticamente (recarga de charts para KPIs, recarga de resultados para K-Means).
- Máximo de reintentos de polling: 30 (configurable con `VITE_MAX_RETRIES`), equivalente a ~7.5 minutos.

---

## K-Means: Segmentación Distribuida de Clientes

### Pipeline técnico

El job K-Means (`spark_jobs/kmeans_job.py`) es un script **standalone ejecutable via `spark-submit`** que implementa el pipeline completo de segmentación:

```
Parquet (transactions_enriched)
    ↓
Feature Engineering (groupBy cliente_id)
    ↓
VectorAssembler + StandardScaler (media=0, std=1)
    ↓
KMeans MLlib para K ∈ {3, 4, 5, 6}
    ↓
ClusteringEvaluator (Silhouette Score)
    ↓
Selección del mejor K (max Silhouette)
    ↓
PCA 2D (proyección para visualización)
    ↓
JSON outputs → data/processed/kmeans/
```

### Features de clientes

| Feature | Cálculo | Descripción |
|---------|---------|-------------|
| `frequency` | `countDistinct(fecha, sucursal_id)` por cliente | Número de visitas de compra únicas |
| `total_units` | `sum(cantidad)` por cliente | Total de unidades compradas |
| `unique_products` | `countDistinct(producto_id)` por cliente | Variedad de productos |
| `unique_categories` | `countDistinct(categoria_id)` por cliente | Diversidad de categorías |
| `avg_basket_size` | `total_units / frequency` | Tamaño promedio de la canasta |

### Ejecución directa del job (sin UI)

```bash
# Vía spark-submit (si spark-submit está en PATH o en .venv/bin/)
spark-submit spark_jobs/kmeans_job.py \
    --input-dir data/processed/transactions_enriched \
    --output-dir data/processed/kmeans \
    --master local[*]

# Vía Python (misma semántica, crea SparkSession interna)
python spark_jobs/kmeans_job.py \
    --input-dir data/processed/transactions_enriched \
    --output-dir data/processed/kmeans
```

### Outputs del job

Tres archivos JSON en `data/processed/kmeans/`:

| Archivo | Contenido |
|---------|-----------|
| `cluster_assignments.json` | Máx. 3000 puntos con `cliente_id`, `cluster`, `pca1`, `pca2` y todas las features |
| `cluster_profiles.json` | Media de cada feature por cluster + tamaño del grupo |
| `evaluation_metrics.json` | `best_k`, y para cada K: `silhouette` y `wssse` |

---

## Rollback del ETL

El sistema implementa un mecanismo de backup y restauración del Parquet procesado para proteger los datos ante fallos o cambios no deseados.

### Cómo funciona

```
ETL inicia
    │
    ├─ Crea backup: transactions_enriched/ → transactions_enriched_backup/
    │
    ├─ Spark sobreescribe transactions_enriched/
    │
    ├─ Si el write FALLA:
    │      → Restaura backup automáticamente (auto-rollback)
    │      → Elimina el backup (datos quedan en estado previo)
    │      → ETL marcado como "failed" en WebSocket
    │
    └─ Si el write TIENE ÉXITO:
           → Backup se mantiene disponible para rollback manual
           → ETL marcado como "completed" en WebSocket
           → GET /etl/status retorna rollback_available: true
```

### Rollback manual desde la UI

Después de un ETL exitoso, el botón **"Rollback a versión anterior"** aparece en el panel de gestión. Al hacer click:

1. `POST /etl/rollback` restaura el backup a `transactions_enriched/`
2. Se invalida el cache de KPIs (fuerza recomputo desde los datos restaurados)
3. Se dispara el recomputo de KPIs en background
4. WebSocket emite `{type: "ETL", status: "rolled_back"}`
5. El botón de rollback desaparece (backup consumido)

### Casos de uso del rollback

| Situación | Comportamiento |
|-----------|---------------|
| ETL falla durante la escritura Parquet | Auto-restauración silenciosa; datos previos intactos; estado: `failed` |
| ETL exitoso produce resultados inesperados | Rollback manual desde la UI; estado: `rolled_back` |
| Nuevo CSV introduce datos corruptos | Rollback manual tras detectar anomalías en los KPIs |

> **Importante:** Solo se mantiene **un nivel** de rollback (la versión inmediatamente anterior). Al iniciar el siguiente ETL, el backup anterior se descarta y se crea uno nuevo con los datos actuales.

---

## API REST

La API está disponible en `http://localhost:8000`. Documentación interactiva (Swagger): `http://localhost:8000/docs`.

### Endpoints de estado y control

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servidor |
| `GET` | `/etl/status` | Estado del Parquet procesado + `rollback_available` |
| `POST` | `/etl/trigger` | Fuerza re-ejecución del ETL en background |
| `POST` | `/etl/rollback` | Restaura el backup Parquet e inicia recomputo de KPIs |
| `GET` | `/analytics/status` | Si el cache de KPIs está listo (`cache_warm`) |
| `POST` | `/analytics/compute` | Fuerza recomputo de todos los KPIs en background |
| `GET` | `/kmeans/status` | Si los resultados K-Means existen (`cached`) + `best_k` |
| `POST` | `/kmeans/trigger` | Lanza el job K-Means (spark-submit) en background |

### WebSocket — Estado de jobs en tiempo real

| Protocolo | Ruta | Descripción |
|-----------|------|-------------|
| `WS` | `/ws/jobs` | Stream de estado de todos los jobs del sistema |

Al conectar, el servidor envía el historial reciente de jobs (últimas 20 entradas de `data/jobs.db`). Cada evento posterior tiene la forma:

```json
{"type": "ETL",        "status": "running",     "job_id": 5}
{"type": "ETL",        "status": "completed",    "job_id": 5}
{"type": "KPIs",       "status": "failed",       "job_id": 6, "message": "..."}
{"type": "KMeans",     "status": "running",      "job_id": 7}
{"type": "KMeans",     "status": "completed",    "job_id": 7}
{"type": "ETL",        "status": "rolled_back",  "job_id": 8}
```

Valores posibles de `status`: `running` · `completed` · `failed` · `rolled_back`

Valores posibles de `type`: `ETL` · `KPIs` · `KMeans` · `Recomendador`

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

### Endpoints de charts analíticos (Plotly JSON)

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

### Endpoints de K-Means

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/kmeans/status` | `{"cached": bool, "best_k": int\|null}` |
| `POST` | `/kmeans/trigger` | Lanza el job K-Means en background (202 Accepted) |
| `GET` | `/kmeans/cluster-assignments` | Lista de puntos (máx. 3000) con `cliente_id`, `cluster`, `pca1`, `pca2` y features |
| `GET` | `/kmeans/cluster-profiles` | Media de features por cluster + tamaño |
| `GET` | `/kmeans/evaluation-metrics` | `best_k` y métricas (silhouette, wssse) para cada K evaluado |
| `GET` | `/kmeans/charts/scatter-clusters` | Scatter PCA 2D coloreado por cluster |
| `GET` | `/kmeans/charts/cluster-profiles` | Barras agrupadas — perfiles comparativos |
| `GET` | `/kmeans/charts/evaluation-metrics` | Curva del codo + Silhouette Score |
| `GET` | `/kmeans/charts/cluster-sizes` | Torta — distribución de clientes por cluster |

---

## Estructura del proyecto

```
proyecto/
├── .env                                # Variables de entorno backend (Spark, paths, API)
├── requirements.txt                    # Dependencias Python
├── backend/                            # Monolito modular — FastAPI
│   ├── main.py                         # Entry point: lifespan, CORS, WebSocket, rollback endpoint
│   ├── config.py                       # Constantes centralizadas (paths, env vars, JOBS_DB_PATH)
│   ├── etl/                            # Módulo ETL
│   │   ├── reader.py                   # Lee CSV crudos con schema explícito
│   │   ├── transformer.py              # Parsea, explota productos, enriquece con categorías
│   │   └── writer.py                   # Escribe Parquet particionado por sucursal_id
│   ├── dispatcher/                     # Módulo Dispatcher Spark
│   │   ├── dispatcher.py               # Fingerprint, backup/restore, ETL, notificaciones WS
│   │   └── watcher.py                  # Watcher async de nuevos archivos (watchfiles)
│   ├── eda_kpis/                       # Módulo EDA + KPIs
│   │   ├── computer.py                 # 9 cómputos PySpark (KPIs + datasets para charts)
│   │   ├── charts.py                   # 7 figuras Plotly (fig.to_json())
│   │   ├── cache.py                    # Lectura/escritura JSON en disco
│   │   └── router.py                   # APIRouter /analytics/* + run_kpis_sync() + notif. WS
│   ├── kmeans/                         # Módulo K-Means
│   │   ├── cache.py                    # Cache JSON en data/processed/kmeans/
│   │   ├── charts.py                   # 4 figuras Plotly (scatter, perfiles, evaluación, tamaños)
│   │   ├── computer.py                 # Dispatcher: lanza spark-submit + notificaciones WS
│   │   └── router.py                   # APIRouter /kmeans/* (status, trigger, charts, datos)
│   └── websocket/                      # Módulo WebSocket
│       ├── manager.py                  # ConnectionManager (broadcast a clientes conectados)
│       └── db.py                       # SQLite: init_db, insert_job, update_job, get_recent_jobs
├── frontend/                           # App React — dashboard independiente
│   ├── .env                            # VITE_API_URL, VITE_POLL_INTERVAL_MS, VITE_MAX_RETRIES
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                    # Entry React
│       ├── App.jsx                     # Layout: sidebar + secciones ETL / EDA / K-Means
│       ├── App.css                     # Estilos mínimos custom
│       ├── api/
│       │   └── analytics.js            # Capa fetch: /analytics/*, /etl/*, /kmeans/*
│       ├── hooks/
│       │   └── useJobStatus.js         # WebSocket hook: jobStatus + lastSuccessful por tipo
│       └── components/
│           ├── Sidebar.jsx             # MUI Drawer — navegación + badges de estado
│           ├── KpiCard.jsx             # MUI Card con número formateado (es-CO)
│           ├── PlotlyChart.jsx         # Fetch + Plotly.newPlot() con fetchFn configurable
│           ├── KmeansSection.jsx       # Sección K-Means: botón, cluster cards, 4 gráficos
│           └── StatusBadge.jsx         # MUI Chip: running/completed/failed/rolled_back
├── spark_jobs/
│   ├── session.py                      # SparkSession singleton (local[*] o cluster)
│   └── kmeans_job.py                   # Job standalone K-Means (spark-submit ready)
├── DataSet/DataSet/                    # Datos crudos
│   ├── Transactions/                   # *_Tran.csv por sucursal
│   └── Products/                       # Categories.csv, ProductCategory.csv
└── data/                               # Datos generados (no versionar)
    ├── jobs.db                         # SQLite — historial de todos los jobs
    └── processed/
        ├── .etl_state.json             # Fingerprint del último ETL exitoso
        ├── transactions_enriched/      # Parquet particionado por sucursal_id
        ├── transactions_enriched_backup/ # Backup pre-ETL (para rollback)
        ├── kpis/                       # Cache JSON de KPIs y charts analíticos
        └── kmeans/                     # Cache JSON de resultados K-Means
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

El resto del código no requiere cambios. La `SparkSession` en `spark_jobs/session.py` usa el `SPARK_MASTER_URL` configurado. El job K-Means también recibe el master URL como argumento y lo pasa a su propia `SparkSession`.

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
