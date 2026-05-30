# Order Management System

## Contexto

Este proyecto es una API de backend para un sistema de gestión de órdenes con PostgreSQL como base de datos. Está diseñado para exponer endpoints REST para órdenes, clientes, productos e informes. También incluye configuraciones de Docker y pruebas básicas.

El código principal del backend está en `backend/routers/app_postgres.py` y se ejecuta con Flask. Las variables de configuración de PostgreSQL se cargan desde el entorno y el contenedor puede iniciarse con Docker o Podman.

## Arquitectura

La aplicación sigue una arquitectura sencilla basada en:

- `backend/routers/app_postgres.py`: servidor Flask con rutas para:
  - `/api/orders` (GET, POST)
  - `/api/orders/<id>` (GET, PUT, DELETE)
  - `/api/customers` (GET)
  - `/api/products` (GET)
  - `/api/reports/sales-by-customer` (GET)
  - `/api/reports/orders-by-status` (GET)
  - `/api/health` (GET)

- Configuración de base de datos:
  - usa `psycopg2` para conectarse a PostgreSQL
  - lee los datos de conexión desde variables de entorno: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

- Docker:
  - `Dockerfile` construye una imagen Python 3.11-slim
  - `compose.yaml` y `compose.debug.yaml` definen cómo arrancar el servicio en contenedor

- Pruebas:
  - carpeta `tests/apis`
  - contiene pruebas basadas en `pytest`

## Estructura de directorios

```text
.
├── .dockerignore
├── .gitignore
├── .vscode/
├── Dockerfile
├── README.md
├── backend.log
├── backend/
│   ├── data/
│   │   └── setup_postgres.sql
│   └── routers/
│       └── app_postgres.py
├── compose.debug.yaml
├── compose.yaml
├── conftest.py
├── env.exemple
├── fixture/
│   └── order_factory.py
├── frontend.log
├── frontend/
│   └── order_system.html
├── pytest.ini
├── requirements.txt
├── reports/
│   └── qa_test_coverage_report.html
└── tests/
    └── apis/
        └── test_api_orders.py
```

### Descripción de directorios y archivos

- **backend/**: Código del servidor Flask con la lógica de la API
  - `routers/`: Rutas y controladores REST
  - `data/`: Scripts de configuración de base de datos
- **frontend/**: Interfaz HTML del sistema de órdenes
- **tests/**: Pruebas automatizadas con pytest
  - `apis/`: Pruebas de endpoints API
- **fixture/**: Fábricas de datos para pruebas
- **reports/**: Reportes de cobertura y QA
- **conftest.py**: Configuración global de pytest
- **pytest.ini**: Configuración de pytest
- **compose.yaml** y **compose.debug.yaml**: Orquestación con Docker Compose
- **env.exemple**: Plantilla de variables de entorno

## Cómo ejecutar el backend

### 1. Preparar variables de entorno

Copia el ejemplo de env:

```bash
cp env.exemple .env
```

Edita `.env` y configura los valores correctos de tu base de datos PostgreSQL:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=M1l02025
```

> Si usas Docker con `network_mode: host`, el contenedor buscará PostgreSQL en `localhost:5432` del host.

### 2. Ejecutar localmente con Python

Instala las dependencias si no lo has hecho:

```bash
python3 -m pip install -r requirements.txt
```

Ejecuta el backend:

```bash
python3 backend/routers/app_postgres.py
```

La API quedará corriendo en `http://0.0.0.0:5000`.

### 3. Ejecutar con Docker

Construye la imagen:

```bash
docker build -t ordermanagementsystem .
```

Ejecuta el contenedor:

```bash
docker run --rm -p 5000:5000 \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_NAME=postgres \
  -e DB_USER=postgres \
  -e DB_PASSWORD=M1l02025 \
  ordermanagementsystem
```

Si tu entorno no tiene un daemon Docker disponible, puedes usar Podman:

```bash
podman run --rm -p 5000:5000 \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_NAME=postgres \
  -e DB_USER=postgres \
  -e DB_PASSWORD=M1l02025 \
  ordermanagementsystem
```

### 4. Ejecutar con Docker Compose

Si tienes Docker Compose funcional:

```bash
docker compose -f compose.yaml up --build
```

Para debug:

```bash
docker compose -f compose.debug.yaml up --build
```

> Si no funciona `docker compose` por falta de daemon, usa Podman o ejecuta localmente.

## Cómo ejecutar los casos de prueba

El proyecto incluye pruebas con `pytest`. Para ejecutarlas:

```bash
python3 -m pip install pytest
pytest tests/apis/test_api_orders.py
```

Estas pruebas cubren el uso de la API de órdenes. Si quieres ejecutar toda la carpeta de pruebas:

```bash
pytest tests
```

### Generar un reporte HTML de los tests

Puedes generar un reporte HTML legible usando el plugin `pytest-html`. Pasos recomendados:

- Instalar `pytest-html` (solo la primera vez):

```bash
python3 -m pip install pytest-html
```

- Ejecutar pytest y generar el HTML (archivo `reports/test_run_report.html`):

```bash
pytest --html=reports/test_run_report.html --self-contained-html -v
```

- Abrir el reporte en tu navegador:

```bash
xdg-open reports/test_run_report.html    # Linux
open reports/test_run_report.html        # macOS
```

También se añadió un reporte de ejecución reciente en `reports/test_run_report.html` que resume los tests y muestra los mensajes impresos durante la ejecución.

## Sección de defecto

### Defecto detectado

Durante la corrección del proyecto se encontró un defecto en `backend/routers/app_postgres.py` y en la configuración Docker:

- En `app_postgres.py` el diccionario `DB_CONFIG` estaba dañado porque se insertó texto no válido de un comando `pm2` dentro del código.
- Faltaban imports importantes: `Flask`, `CORS` y `datetime`.
- El `Dockerfile` intentaba ejecutar `main.py`, un archivo que no existe en este proyecto.
- `requirements.txt` no contenía paquetes necesarios para PostgreSQL, `.env` y CORS.
- El servidor Flask se iniciaba sin `host='0.0.0.0'`, lo que bloqueaba el acceso externo desde el contenedor.

### Explicación del defecto

Ese error provocaba que el backend no pudiera iniciar correctamente desde Docker y que la conexión a PostgreSQL fallara porque la configuración de la base de datos no era válida. La aplicación tampoco era accesible desde el contenedor si se ejecutaba por defecto en `127.0.0.1`.

### Solución aplicada

Se corrigió lo siguiente:

- Se restauró `DB_CONFIG` con los valores correctos leídos desde variables de entorno.
- Se agregaron las importaciones necesarias en `backend/routers/app_postgres.py`.
- Se modificó el `Dockerfile` para ejecutar `backend/routers/app_postgres.py`.
- Se incluyeron las dependencias `psycopg2-binary`, `python-dotenv` y `flask-cors` en `requirements.txt`.
- Se cambió `app.run(...)` para usar `host='0.0.0.0'`.

### Defecto adicional detectado

- `tests/apis/test_api_orders.py::test_02_post_order_persists_in_db` y `test_03_get_orders_shows_inserted_data` dependen de `fixture/order_factory.py`.
- El factory de datos estaba generando campos `UnitPrice` y `Status` en lugar de `unit_price` y `status`, lo cual no coincide con el contrato del backend para `POST /api/orders`.
- Esta discrepancia se considera un defecto de integración entre las pruebas/fixture y el backend, y puede provocar que las pruebas o el flujo de creación de órdenes fallen al validar el payload.

## Notas finales

- El backend se expone en `http://0.0.0.0:5000`.
- Revisa el reporte de QA y cobertura de pruebas en `reports/qa_test_coverage_report.html`.
- Asegúrate de tener PostgreSQL corriendo y accesible desde el host que use el contenedor.
- Si quieres una versión de producción, reemplaza el servidor de Flask de desarrollo por un WSGI como `gunicorn`.
