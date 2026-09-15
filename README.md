# BrevioAI

Plataforma para generar resúmenes de documentos, audio MP3 y listas de YouTube. El usuario elige idioma, modelo, categoría, estilo, formato y nivel de detalle. El trabajo corre en segundo plano (Celery) y el resultado se guarda en disco y en MongoDB.

No es un producto de facturación: el router de billing se eliminó. Los créditos (`user_credit`) existen en el perfil, pero no hay compra ni recarga en la aplicación. Las cuentas nuevas empiezan en **0 créditos**.

## Qué hace (y qué no)

**Hace**

- Resumen de **PDF y DOCX** (`POST /brevio/summary-documents`).
- Estimación local de tokens/coste de esos mismos documentos, **sin llamar al LLM** (`POST /brevio/estimate-documents`).
- Resumen de **audio/vídeo** (`POST /brevio/summary-media`) y **YouTube**: transcripción con el proveedor elegido (OpenAI, Gemini, xAI o Whisper local en DEV) y resumen con un modelo independiente. MVP de ficheros: MP3, M4A, WAV, MP4. Ver `docs/PROVIDERS.md`.
- Resumen de **playlists de YouTube** (`POST /brevio/summary-yt-playlist`) vía `yt-dlp` (postprocessor `FFmpegExtractAudio`) y el proveedor de transcripción configurado. Los Dockerfiles de `core/` instalan `ffmpeg`/`ffprobe` vía `apt-get`.
- Pipeline Map-Reduce asíncrono, cuotas de proveedor en Redis (si `PROVIDER_QUOTA_ENABLED=true`) y eventos SSE (`GET /events/stream`).
- Biblioteca de carpetas, historial, descarga on-demand (`.md`, `.docx`, `.pdf`, `.txt`) y claves API de usuario cifradas (AES-256-GCM).
- UI Vue 3 (PrimeVue Aura) en `/summary`, `/store` y `/profile`.
- Sesión con cookies httpOnly (`brevio_access` 15 min por defecto, `brevio_refresh` 7 días), rotación en `POST /auth/refresh` y revocación en `POST /auth/logout`. El JWT **no** viaja en JSON ni en `localStorage`.

**No hace**

- No acepta TXT/Markdown en los endpoints de resumen/estimación HTTP: el validador solo admite PDF y DOCX. El extractor interno sí sabe leer `.txt`/`.md`, pero esos archivos no pasan la API.
- No resume formatos de audio/vídeo fuera del MVP (MP3, M4A, WAV, MP4).
- No hay edición de perfil (nombre/email) ni cambio de contraseña dentro de sesión; el cambio va por OTP de recuperación.
- El enum `LanguageType` lista cientos de idiomas; **los prompts de generación existen solo para 12** (ver más abajo). El frontend solo ofrece esos.
- `docs/API.md` y `docs/ARCHITECTURE_SUMMARY_PIPELINE.md` están desfasados en varios puntos (faltan eventos SSE, carpetas de biblioteca, Google/Ollama, etc.). Este README y el código son la fuente de verdad.

## Arquitectura

Cinco servicios Docker:

| Servicio | Qué es | Puerto en el host |
| --- | --- | --- |
| `frontend` | Vue 3 + Vite (dev) o Nginx (prod) | `3000` en dev, `80` en prod |
| `backend` | FastAPI (`core/brevio_api/__main__.py`) | `8000` |
| `celery` | Worker (`core.brevio_api.celery`), timeout suave 1 h / duro 2 h | — |
| `database` | MongoDB 7.0 | `27017` |
| `redis` | Broker Celery (DB 0) y cuotas de proveedor (DB 2) | `6380` → `6379` en el contenedor |

El frontend **no** usa el `proxy_pass /api/` de `frontend/nginx.conf` (apunta a `localhost:8000` *dentro* del contenedor frontend, que no es el backend). El SPA llama a `VITE_API_URL` (por defecto `http://localhost:8000`) desde el navegador.

Swagger: [http://localhost:8000/api/docs](http://localhost:8000/api/docs) · ReDoc: `/api/redoc` · OpenAPI: `/api/openapi.json`.

## Requisitos

- Docker y Docker Compose.
- **Producción** (`docker-compose.yml` + `core/Dockerfile`): imagen `python:3.12-slim` con `core/requirements.txt` únicamente (sin PyTorch / Whisper local). No reserva GPU.
- **Desarrollo** (`docker-compose.dev.yml` + `core/Dockerfile.dev`): imagen `nvidia/cuda` + `core/requirements.dev.txt` (incluye producción, tests, PyTorch y `openai-whisper`). Reserva GPU NVIDIA en `backend`/`celery` para Whisper local; hace falta NVIDIA Container Toolkit.
- Un LLM alcanzable desde los contenedores:
  - **Ollama (local, sin API key):** por defecto `OLLAMA_API_URL=http://host.docker.internal:11434/v1`. Hay que tener Ollama (u otro servidor compatible) **en el host**, no va dentro de Compose.
  - **OpenAI-compatible en el host:** `OPENAI_API_URL` apunta a `http://host.docker.internal:8080/v1`.
  - **Cloud:** claves de OpenAI, DeepSeek y/o Google en `.env` y/o en el perfil del usuario.

`host.docker.internal` está mapeado a `host-gateway` en Linux.

## Arranque

1. Clonar el repositorio y entrar en la raíz.

2. Variables de entorno:

   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env
   ```

   Los valores de `.env.example` son **placeholders de desarrollo**, no secretos de producción (`API_KEY=local_api_key_123`, Mongo `root`/`password`, etc.).

   - Catálogo HTTP (`/brevio/languages`, modelos, etc.) exige cabecera `X-API-KEY` igual a `API_KEY`. El frontend la envía desde `VITE_API_KEY`.
   - `CREDENTIAL_ENCRYPTION_KEY` no está activa en `.env.example` (va comentada). Fuera de `ENVIRONMENT=production` el cifrado de claves usa un fallback fijo de desarrollo. En producción hay que definir una clave AES-256 (32 bytes en Base64). Inventario: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).
   - Correo: **solo** Gmail SMTP (`smtp.gmail.com:587`) con `EMAIL_FROM` y `EMAIL_PASSWORD`. Con los placeholders del example el registro **sí crea la cuenta** (el welcome mail se traga el error). La recuperación OTP **sí falla** (HTTP 500) si SMTP no autentica. Si esas variables no existen, `EmailService` lanza al construir y el registro también falla.
   - `BREVIO_BENCHMARK_IDENTITY` / `BREVIO_BENCHMARK_PASSWORD` son para `benchmark.py`; **no se crea ese usuario al levantar Compose**.

3. Desarrollo (hot-reload de Vite en el frontend y `--reload` de Uvicorn en el backend; **Celery no recarga solo**):

   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

   - UI: http://localhost:3000
   - API: http://localhost:8000/api/docs

4. “Producción” local (frontend compilado, Nginx en el puerto 80, backend con `fastapi run`, sin `--reload`):

   ```bash
   docker compose up -d --build
   ```

   - UI: http://localhost:80
   - API: http://localhost:8000/api/docs

   Eso no es un despliegue endurecido: CORS sale de `CORS_ORIGINS` (credenciales activas; no se puede usar `*`), el JWT y Mongo usan los secretos de ejemplo, y el frontend de Compose monta `./frontend:/app` (Nginx sirve `/usr/share/nginx/html` del build, no ese bind mount).

## Modelos y acceso

El catálogo público es `GET /brevio/models` (y `GET /brevio/transcription-providers` para STT). Límites, parámetros y DEV/PROD se documentan en `docs/PROVIDERS.md`. No copies listas de modelos desde este README: el backend es la fuente de verdad.

Reglas reales de `CredentialResolver.ensure_model_access`:

- Modelos **Ollama**: siempre permitidos; no hace falta clave ni créditos.
- Modelos de pago: se permite si el usuario tiene una clave guardada en perfil (BYOK), **o** si existe clave de plataforma en `.env` **y** `user_credit > 0`.
- `DEV_ALLOW_PLATFORM_OVERRIDE` (true por defecto en development) solo cubre una **clave de plataforma ausente**; no omite créditos ni sustituye BYOK. Sin BYOK, sin clave de plataforma y con 0 créditos, el job se rechaza.

Las claves de perfil se validan contra el proveedor al guardarlas y **nunca se vuelven a devolver**.

## Idiomas, categorías, formatos

**Prompts implementados** (los únicos que el frontend ofrece y que el generador acepta): árabe, inglés, chino (incl. `zh-cn` / `zh-tw`), español, francés, alemán, hindi, italiano, japonés, coreano, portugués (PT y BR) y ruso. Cualquier otro valor de `LanguageType` falla en generación.

**UI** (`frontend/src/i18n`): `en`, `es`, `pt`, `fr`, `de`, `it`, `ru`, `zh`, `ja`, `ko`, `ar`, `hi`.

**Categorías:** `simple_summary`, `journalism`, `marketing`, `health`, `technology`, `education`, `architecture`, `finance`, `tourism`, `requirements`, `sciences`, cada una con estilos propios.

**Niveles:** `very_concise`, `concise`, `moderate`, `detailed`, `very_detailed`.

**Formato pedido al modelo:** `html`, `markdown`, `json`, `text`. El artefacto canónico en disco es `summary.md`; la descarga convierte a docx/pdf/txt bajo demanda.

## Autenticación y API

| Área | Auth |
| --- | --- |
| `POST /auth/login`, `/auth/register`, recuperación OTP | público |
| Catálogo `GET /brevio/languages\|models\|categories-styles\|output-formats\|summary-levels\|transcription-providers` y conteo YouTube | `X-API-KEY` |
| Resumen, estimación, descarga, usuarios, carpetas, credenciales, SSE | cookie httpOnly `brevio_access` (o Bearer de fallback) |

Otras rutas montadas (además de las de `docs/API.md`):

- `GET /events/stream` (SSE; `Last-Event-ID` opcional)
- `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/session`
- `GET/POST /users/folders`, `PATCH/DELETE /users/folders/{id}`
- `POST /users/entries/move`, `POST /users/entries/delete`, `PATCH /users/entries/{id}`
- `GET /user-credentials` (todas las del usuario)

`core/brevio_api/routers/token_router.py` existe en el árbol y **no está incluido** en la app.

Los jobs de resumen responden **202** con `task_id` y `folder_entry_id`. El progreso llega por SSE y por `POST /users/entries` con `{ "entries_refs": [...] }`. Estados: `PROCESSING` | `COMPLETED` | `FAILED`.

Los ficheros generados viven en `./data` (volumen en `celery`; en compose de desarrollo también en `backend`).

## Pruebas

Desde la raíz del repo, con las deps de producción **y** desarrollo:

```bash
pip install -r core/requirements.dev.txt
pytest
```

`requirements.dev.txt` incluye `-r requirements.txt` más PyTorch, Whisper local, pytest y mocks. El run de `pytest` está aislado (sin `.env` real, sin Mongo/Redis/LLM de verdad). Los tests marcados `redis` se saltan salvo `BREVIO_RUN_REDIS_TESTS=1`. `benchmark.py` y `frontend/` no se recogen.

Los tests de Python viven junto al código: `core/brevio/tests/` y `core/brevio_api/tests/`.

Frontend:

```bash
cd frontend
npm ci
npm run test:unit -- --run
npx playwright install chromium
npm run test:e2e
```

Playwright levanta un preview en `:4173` y mockea la API; no necesita el backend Docker.

## Parar

```bash
docker compose down
```

Eso para y borra contenedores y la red. **No borra el volumen `db_data` de Mongo.** Para borrarlo: `docker compose down -v`.

## Documentación extra

- Variables de entorno (inventario completo, alias y variables muertas): [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).
- Pipeline interno: [`docs/ARCHITECTURE_SUMMARY_PIPELINE.md`](docs/ARCHITECTURE_SUMMARY_PIPELINE.md) (útil, no actualizado al 100 %).
- Inventario de endpoints: [`docs/API.md`](docs/API.md) (incompleto frente al código).
- Mapa UI ↔ API: [`frontend/docs/BACKEND_FRONTEND_MAP.md`](frontend/docs/BACKEND_FRONTEND_MAP.md).
- Frontend: [`frontend/README.md`](frontend/README.md).
