# Variables de entorno de BrevioAI

Este documento es el inventario de **todas** las constantes que el código, Docker Compose, Vite, pytest y los scripts de benchmark leen del entorno. No basta con copiar un `.env` antiguo: varios nombres coexistían (uno canónico y otro legado) y otros estaban en `.env.example` **sin que nadie los leyera**.

Fuentes de verdad:

| Archivo | Qué configura |
| --- | --- |
| [`.env.example`](../.env.example) → `.env` | **Producción**: `docker compose -f docker-compose.yml` (interpolación + `env_file`). |
| [`.env.dev.example`](../.env.dev.example) → `.env.dev` | **Desarrollo**: `docker compose --env-file .env.dev -f docker-compose.dev.yml`. |
| [`frontend/.env.example`](../frontend/.env.example) → `frontend/.env` | Build Vite de producción (`VITE_*` en el bundle). |
| `frontend/.env.development` | Vite `npm run dev` / frontend de compose.dev. |
| [`core/shared/utils/environment.py`](../core/shared/utils/environment.py) | Parseo único de flags, alias JWT/TPM y helpers compartidos. |

`core/brevio_api/.env.example` está **obsoleto** (usaba `SECRET_KEY`, `ALGORITHM`, `TOKENS_PER_MINUTE`). No lo copies.

## Cómo se cargan

1. **Producción** — Compose lee `.env` por defecto para `${PUERTOS}` y lo monta como `env_file` en backend/celery/database/redis. `VITE_*` llegan al build del frontend como build-args.
2. **Desarrollo** — pasar `--env-file .env.dev` (interpolación); los servicios usan `env_file: .env.dev`. Proyecto Compose `brevioai-dev` (aislado de `brevioai`).
3. **Frontend Compose prod** — el contenedor nginx no necesita `env_file`; el SPA ya lleva `VITE_*` embebidos.
4. **Frontend Compose dev** — monta `./frontend`; Vite mode=development carga `frontend/.env.development`.
5. **Python** llama `load_dotenv()` en varios módulos; en Docker suele ser redundante porque Compose ya inyectó las variables.
6. **pytest** (`conftest.py`) **anula** `load_dotenv` y fija un entorno aislado.
7. **Benchmarks** cargan el `.env` de la raíz a propósito (producción o exportar `BREVIO_API_URL`).

Booleanos aceptados en todo el código de aplicación: `1`, `true`, `yes` (verdadero) y `0`, `false`, `no` (falso). Mayúsculas irrelevantes. Antes `SUMMARY_LOCAL_USER_ACCESS=1` se interpretaba como falso; ahora es verdadero.

## Volúmenes locales

El contenedor de API/Celery corre como uid `10001` (`brevio`). El bind mount `./data` debe ser escribible por ese uid; Compose arranca un servicio one-shot `data-init` que hace `chown -R 10001:10001 ./data`. Si ves `Permission denied` / `Error saving media file` al subir documentos, revisa la propiedad de `./data`.

---

## 1. Docker Compose y runtime Python

Estas variables las usa Compose para puertos/hosts y/o el proceso Python dentro del contenedor.

| Variable | Default en código / Compose | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `PYTHONUNBUFFERED` | `1` en el example | No | intérprete CPython | Logs sin buffer (imprescindible en Docker). No hay `os.getenv` en el repo; la usa Python. |
| `PYTHONPATH` | `/app` en el example | En Docker sí | intérprete | Permite `import core...` porque el código vive en `/app/core`. |
| `LOG_LEVEL` | `DEBUG` | No | `core/brevio_api/__main__.py` `setup_logging()` | Nivel de logging de la API. En producción usa `INFO` o `WARNING`. |
| `FRONTEND_PORT` | `80` | No | `docker-compose.yml` | Puerto **host** del Nginx de producción. |
| `FRONTEND_DEV_PORT` | `3000` | No | `docker-compose.dev.yml` | Puerto host y `--port` de Vite. |
| `BACKEND_PORT` | `8000` | No | ambos compose | Puerto host de FastAPI. Dentro del contenedor sigue siendo `8000`. |
| `MONGO_PORT` | `27017` | No | ambos compose | Puerto host de Mongo. |
| `REDIS_PORT` | `6380` | No | ambos compose | Puerto host → `6379` del contenedor Redis. |

El frontend **no** usa `FRONTEND_PORT` en Node; solo Compose.

---

## 2. MongoDB

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `MONGO_INITDB_ROOT_USERNAME` | `root` (example) | Al crear el volumen | imagen oficial `mongo:7.0` | Usuario root **solo** la primera vez que se crea `db_data`. |
| `MONGO_INITDB_ROOT_PASSWORD` | `password` (example) | Igual | imagen Mongo | Contraseña root inicial. Cambiarla en `.env` **después** de crear el volumen no rota la password. |
| `MONGO_INITDB_DATABASE` | `brevio` (example) | No | imagen Mongo | Base creada al init. La app usa el path de `MONGODB_URI`. |
| `MONGODB_URI` | ninguno (falla) | **Sí** (API/Celery) | `core/brevio_api/core/database.py` | URI completa. En Compose: host `database`, auth `admin`. |
| `SERVER_SELECTION_TIMEOUT_MS` | `30000` | No | `AsyncDB` | Timeout de selección de servidor Mongo. |
| `CONNECT_TIMEOUT_MS` | `20000` | No | `AsyncDB` | Timeout de conexión TCP. |
| `SOCKET_TIMEOUT_MS` | `60000` | No | `AsyncDB` | Timeout de socket. |

`MONGODB_URI` debe coincidir con usuario/password/db de `MONGO_INITDB_*` en un volumen nuevo. Ejemplo Compose:

`mongodb://root:password@database:27017/brevio?authSource=admin`

Fuera de Docker (pytest, scripts locales) el host suele ser `127.0.0.1`.

---

## 3. Redis, Celery y eventos SSE

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | En Docker sí | `core/brevio_api/celery.py` via `resolve_redis_url()` | Broker. Compose: `redis://redis:6379/0` (DB 0). Credenciales ACL se inyectan si `REDIS_PASSWORD` está definido. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | En Docker sí | `celery.py` | Backend de resultados Celery. |
| `REDIS_PASSWORD` | vacío (dev abierto) | **Sí en production** | `deploy/redis/entrypoint.sh`, `resolve_redis_url()`, `assert_secure_runtime_config` | Activa ACL: usuario `REDIS_USERNAME` (default `brevio`), `default` off. Mín. 16 chars en production. |
| `REDIS_USERNAME` | `brevio` | No | ACL + URL injection | Usuario de aplicación (no admin). |
| `EVENTS_REDIS_URL` | ninguno → usa `CELERY_BROKER_URL` si es Redis | No | `events_redis_url()` | Redis Streams SSE. |
| `EVENTS_SSE_HEARTBEAT_SECONDS` | `15` | No | `events_router.py` `heartbeat_seconds()` | Comentarios SSE periódicos. Mínimo 1. |
| `PROVIDER_QUOTA_REDIS_URL` | `CELERY_BROKER_URL` o `redis://localhost:6379/2` | Si las cuotas están activas | `ProviderQuotaManager` | **Debe** ser otra DB que la de Celery (`/2` en Compose) para no mezclar streams/listas. |

pytest fuerza `CELERY_BROKER_URL=memory://` para no hablar con Redis.

---

## 4. Entorno, seguridad y autenticación

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `ENVIRONMENT` | `development` | No | `current_environment()`, cookies, cifrado, políticas de acceso | Valores típicos: `development`, `production`, `test`. Se normaliza a minúsculas. `production` oculta Ollama/Whisper local, exige `CREDENTIAL_ENCRYPTION_KEY` y, si no hay `COOKIE_SECURE`, pone cookies `Secure`. |
| `API_KEY` | `DEFAULT_SECRET_KEY` | De facto sí | `dotenv.py` → header `X-API-KEY` | Catálogo HTTP (`/brevio/languages`, modelos, etc.). Debe coincidir con `VITE_API_KEY` del frontend. |
| `SECRET_TOKEN_KEY` | `default_secret_key` | **Sí en producción** | `jwt_secret_key()` → `TokenService` | Firma JWT. Alias legado: `SECRET_KEY` (solo si `SECRET_TOKEN_KEY` está vacío). |
| `TOKEN_ALGORITHM` | `HS256` | No | `jwt_algorithm()` | Algoritmo JWT. Alias legado: `ALGORITHM`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | No | `TokenService` (en construcción, no al importar) | TTL del access token y cookie `brevio_access`. Mínimo 1. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | No | `TokenService` | TTL del refresh token y cookie `brevio_refresh`. Mínimo 1. |
| `COOKIE_SECURE` | derivado de `ENVIRONMENT==production` | No | `auth_cookies.cookie_secure()` | Si está definida, manda. Si no, `true` solo en production. En HTTP local debe ser `false`. |
| `REFRESH_COOKIE_PATH` | `/auth` | No | `auth_cookies.refresh_cookie_path()` | Path de la cookie `brevio_refresh` **visto por el navegador**. Detrás de nginx `/api/` debe ser `/api/auth` (si queda en `/auth`, el refresh nunca recibe la cookie). |
| `CORS_ORIGINS` | localhost:3000, 127.0.0.1:3000, localhost, localhost:80 | No | `cors_allow_origins()` | Lista CSV. Hay `allow_credentials=True`, así que **no** puede ser `*`. |
| `CREDENTIAL_ENCRYPTION_KEY` | (dev fallback fijo) | **Sí en production** | `EncryptionService` | AES-256-GCM, 32 bytes en Base64 URL-safe. Sin ella en production el servicio **no arranca**. |
| `CREDENTIAL_ENCRYPTION_KEY_PREVIOUS` | vacío | No | `EncryptionService.decrypt` | Clave anterior solo para decrypt (rotación). Tras rotar, re-guardar BYOK re-cifra con la clave actual. |
| `DEV_ALLOW_PLATFORM_OVERRIDE` | `true` | No | `PlatformAccessPolicy` | En **development**, permite resolver credencial de plataforma cuando falta clave de usuario. En **production** siempre es falso (la flag no abre el fallback). No omite créditos. |

### Alias JWT (corregidos)

| Canónico (usar este) | Legado (solo si el canónico está vacío) | Variable Python histórica |
| --- | --- | --- |
| `SECRET_TOKEN_KEY` | `SECRET_KEY` | `SECRET_KEY` en `dotenv.py` |
| `TOKEN_ALGORITHM` | `ALGORITHM` | `ALGORITHM` en `dotenv.py` |

El `.env.example` antiguo de `core/brevio_api/` documentaba los nombres **legado**, que el código no leía. Eso ya no aplica.

---

## 5. Pipeline de resumen (LLM)

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `TEMPERATURE` | `0.2` | No | `SummaryService`, `ConfigModel`, benchmarks | Temperatura de completions. |
| `MAX_TOKEN_PER_MINUTE` | `200000` | No | `tokens_per_minute()` → `SummaryService` y `ConfigModel` | Token bucket **local al proceso**, no el TPM de Google. Alias legado: `TOKENS_PER_MINUTE` (solo si el canónico está vacío). Si ambos existen, gana `MAX_TOKEN_PER_MINUTE`. |
| `MAX_TOKEN_WAIT` | `300` | No | `SummaryService._check_token_limit` | Segundos máximos de espera si el bucket local está vacío. |
| `MAX_TOKENS` | `4096` | No | **solo** `ConfigModel.max_tokens` si fallan las capacidades del modelo | El pipeline vivo usa `ModelCapabilities.native_max_output_tokens`. No limita Reduce/Format. |
| `BREVIO_KEEP_PARTIALS` | `false` | No | `SummaryService`, `SummaryArtifactManager` | Si true, no borra `summary.md.partial` tras commit (debug). |
| `BREVIO_ENABLE_FORMAT_PHASE` | `false` | No | `SummaryService._format_phase_enabled` | La fase FORMAT es opt-in. Apagada por defecto porque reescribe el REDUCE y puede recortar cobertura. |
| `BREVIO_MIN_TOKENS_FOR_POSTPROCESS` | capacidades del modelo (`min_tokens_for_postprocess`, típico 2000) | No | `SummaryService._min_tokens_for_postprocess` | Umbral para saltar FORMAT aunque la fase esté habilitada. |
| `BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK` | `false` (o el YAML de cuotas) | No | `allow_map_original_text_fallback()` | Si un chunk MAP falla, meter el texto original en REDUCE. Degrada calidad. La env **pisa** el YAML. |
| `JOB_MAX_PROVIDER_REQUESTS` | derivado de chunks × reintentos | No | `job_budget.py` | Tope absoluto de HTTP al proveedor por job. El YAML `job_max_provider_requests` tiene prioridad. |

### Qué **no** es una env del pipeline (aunque tests o docs viejos lo dijeran)

Estas cadenas aparecen en tests o en `docs/ARCHITECTURE_SUMMARY_PIPELINE.md` histórico. **Ningún `os.getenv` de producción las lee:**

| Nombre | Dónde vive realmente |
| --- | --- |
| `REDUCE_BATCH_TOKENS` | `ModelCapabilities.reduce_batch_tokens` |
| `MAX_COMPRESSION_ROUNDS` | no existe en código |
| `TARGET_COMPRESSION_RATIO` | no existe en código (`INTERMEDIATE_COMPRESSION_RATIO` es constante Python) |

---

## 6. Cuotas distribuidas de proveedor

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `PROVIDER_QUOTA_ENABLED` | `false` en código; `true` en `.env.example` y `docker-compose.dev.yml` | En multi-worker sí | `provider_quota_enabled()` | Fail-closed: sin YAML o sin Redis la llamada al proveedor no sale. Un solo proceso aún tiene pacing local. |
| `PROVIDER_QUOTA_CONFIG_PATH` | ninguno → lista de policies vacía | Si enabled=true | `load_quota_policies()` | Ruta al YAML (`core/brevio/config/provider_quotas.example.yaml` en Compose). |
| `PROVIDER_QUOTA_REDIS_URL` | ver sección Redis | Si enabled=true | `ProviderQuotaManager` | Estado RPM / in-flight / cooldown compartido. |

RPM/TPM/max_in_flight **no** van en `.env`: van en el YAML de cuotas.

---

## 7. Proveedores de resumen (LLM)

Patrón dinámico, no una lista cerrada:

- `{PROVIDER}_API_KEY` — `CredentialResolver._get_platform_key` (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY` / alias `GEMINI_API_KEY`, `XAI_API_KEY`, `ANTHROPIC_API_KEY`, …). Ollama **no** usa la key del env: fuerza `ollama-local-key`.
- `{PROVIDER}_API_URL` — `get_provider_base_url()` si está definida; si no, defaults:

| Provider | Default de URL |
| --- | --- |
| openai | `https://api.openai.com/v1` |
| deepseek | `https://api.deepseek.com` |
| google | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| xai | `https://api.x.ai/v1` |
| anthropic | `https://api.anthropic.com` |
| ollama | `http://host.docker.internal:11434/v1` |

| Variable | Default | Efecto |
| --- | --- | --- |
| `OPENAI_API_KEY` / `OPENAI_API_URL` | key vacía; URL default OpenAI o example local | Plataforma pay-per-use / proxy local. |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_API_URL` | — | Igual. |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_URL` | — | Gemini OpenAI-compatible. `GEMINI_API_KEY` es alias de plataforma. |
| `XAI_API_KEY` / `XAI_API_URL` | — | Grok Chat Completions + STT. |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_API_URL` | — | Messages API nativa (no Chat Completions). |
| `OLLAMA_API_URL` | default arriba | Servidor local. Debe ser alcanzable desde el contenedor (`host.docker.internal`). |
| `OLLAMA_API_KEY` | ignorada para Ollama | pytest la rellena; el resolver no la usa. |
| `ENABLED_SUMMARY_PROVIDERS` | vacío = todos los del catálogo que pase la política | CSV allowlist (`openai,deepseek,google,xai,anthropic,ollama`). |
| `SUMMARY_LOCAL_USER_ACCESS` | true fuera de production; false en production | Si true, los modelos Ollama se listan también en production. |

Prioridad de credencial: BYOK del usuario → Ollama dummy → key de plataforma en env. Los créditos se exigen aparte en `ensure_model_access`.

---

## 8. Transcripción y FFmpeg

| Variable | Default | Quién la lee | Efecto |
| --- | --- | --- | --- |
| `ENABLED_TRANSCRIPTION_PROVIDERS` | vacío = implementados que pase política | `TranscriptionAccessPolicy` | CSV. Aliases: `openai`/`openai_whisper`; `google`/`gemini`; `xai`/`grok`; `local_whisper`/`whisper`/`local`. |
| `WHISPER_LOCAL_USER_ACCESS` | true fuera de production | `local_user_access(...)` | Whisper local seleccionable en production solo si true. |
| `TRANSCRIPTION_DEFAULT_PROVIDER` | local_whisper fuera de prod si está permitido; si no openai | `default_media_provider()` | Debe ser un id seleccionable. |
| `WHISPER_LOCAL_MODEL` | `small` | `local_whisper_provider.py` | Nombre del modelo faster-whisper/openai-whisper local. |
| `WHISPER_LOCAL_TIMEOUT` | `600` | local provider | Timeout en segundos. |
| `FFMPEG_TIMEOUT` | `300` | `MediaPreprocessor` | Timeout de extracción/normalización. |
| `OPENAI_TRANSCRIPTION_TIMEOUT` | `120` | `openai_provider.py` | Timeout Whisper API / gpt-transcribe. |
| `OPENAI_TRANSCRIPTION_API_URL` | `https://api.openai.com/v1` | openai transcription | Override del base URL. BYOK de OpenAI no usa `OPENAI_API_URL` del resumen a menos que coincidan por casualidad. |
| `GOOGLE_TRANSCRIPTION_TIMEOUT` | `180` | `google_provider.py` | Timeout Files API + generateContent. |
| `XAI_TRANSCRIPTION_TIMEOUT` | `180` | `xai_provider.py` | Timeout POST `/v1/stt`. |

La transcripción OpenAI resuelve la key con `CredentialResolver` (BYOK o `OPENAI_API_KEY` de plataforma), no una env distinta.

---

## 9. Correo

| Variable | Default | Obligatoria | Quién la lee | Efecto |
| --- | --- | --- | --- | --- |
| `EMAIL_FROM` | ninguno | Al construir `EmailService` | `email_service.py` | Gmail SMTP `smtp.gmail.com:587`. Si falta, **falla el registro**. |
| `EMAIL_PASSWORD` | ninguno | Igual | igual | App password de Gmail. Placeholders del example: el welcome mail se traga el error; la recuperación OTP responde 500. |

No hay `SMTP_HOST`/`SMTP_PORT`: están hardcodeados a Gmail.

---

## 10. Precios y créditos de plataforma

Leídas **una vez** al importar `core/shared/utils/pricing_registry.py` (todas las filas del registro comparten el mismo bloque comercial).

| Variable | Default | Efecto |
| --- | --- | --- |
| `PRICING_EFFECTIVE_FROM` | `date.today()` ISO | Fecha efectiva del snapshot. |
| `PRICING_VERSION` | `2026-09-09` | Versión documental. |
| `PLATFORM_CURRENCY` | `EUR` | Moneda de cobro interno. |
| `USD_TO_PLATFORM_RATE` | `0.92` | FX USD → moneda plataforma. |
| `COMMERCIAL_MARGIN` | `0.18` | Margen sobre coste proveedor. |
| `CREDIT_UNIT_VALUE` | `0.01` | Valor de 1 crédito en moneda plataforma. |
| `MINIMUM_CREDITS` | `1` | Mínimo de créditos a cobrar en modelos de pago. Ollama fuerza `0` en código. |
| `CREDIT_RESERVATION_TTL_SECONDS` | `21600` | TTL de reservas PENDING (Mongo `expires_at`; reconciler libera/asienta). |
| `CREDIT_RESERVATION_SAFETY_MARGIN` | `1.0` | Multiplicador ≥1 sobre `maximum_credits` al reservar. |
| `CREDIT_DEFAULT_JOB_RESERVATION` | `50` | Reserva por defecto si no hay estimación (media/youtube). |
| `CREDIT_OVERRUN_POLICY` | `clamp` | `clamp` limita consumo a lo reservado; `reject` falla el settle. |

`CreditAccount.balance` (int) es la autoridad comercial. `User.user_credit` se migra de forma idempotente al crear la cuenta y **no** autoriza Jobs tras FASE 3.

### FASE 5 — Planes y límites de producto

| Variable | Default | Efecto |
| --- | --- | --- |
| `COMMERCIAL_PLANS_PATH` | `core/brevio/config/commercial_plans.yaml` | Fuente única de planes FREE/PRO/BUSINESS y límites. |

Periodo por defecto: `calendar_month` UTC (ver YAML `period_mode`). Cambio de plan: `plan_change_usage_policy=keep_period_counters` (detalle en `docs/MIGRATION_PLANS_FASE5.md`). Los créditos de periodo (`credits_used`) vienen del settlement; en admit se usa hold atómico vía `credits_budget` (FASE 6). BYOK no salta límites de producto.

Catálogo HTTP: `GET /plans` (**público**, sin sesión). **No hay Stripe** ni precios comerciales en el YAML/código actuales; ver `docs/PLANS_AND_BILLING.md`.

### FASE 6 — Capacity + fairness

| Variable | Default | Efecto |
| --- | --- | --- |
| `GLOBAL_MAX_CONCURRENT_JOBS` | `8` | Techo global de Jobs en ejecución. |
| `GLOBAL_MAX_QUEUED_JOBS` | `500` | Techo global WAITING en scheduler. |
| `CAPACITY_MAX_QUEUED_JOBS_PER_USER` | `50` | Techo por usuario en cola fair. |
| `CAPACITY_LEASE_TTL_SECONDS` | `180` | TTL lease Redis (refresco con heartbeat). |
| `CAPACITY_REDIS_URL` | heartbeat/quota URL | Slots operativos. |
| `SCHEDULER_DISPATCH_INTERVAL_SECONDS` | `2` | Tick Celery beat del dispatcher. |

Fairness: soft `scheduler_priority` + weighted deficit round-robin (`scheduler_weight`). Redis down → fail-closed. Provider quota no se duplica. Detalle: `docs/MIGRATION_CAPACITY_FASE6.md`.

### FASE 7 — Rate limiting + anti-abuse

| Variable | Default | Efecto |
| --- | --- | --- |
| `RATE_LIMIT_ENABLED` | `true` | Activa/desactiva API rate limits. |
| `ANTI_ABUSE_ENABLED` | `true` | Violaciones → cooldown. |
| `ANTI_ABUSE_REDIS_URL` | capacity/heartbeat URL | Redis operativo anti-abuse. |
| `TRUSTED_PROXY` | private CIDRs | Quién puede fijar `X-Forwarded-For`. |
| `AUTH_RATE_LIMIT` / `*_WINDOW` | `10`/`60` | Auth login/register/OTP/… |
| `AUTH_REFRESH_RATE_LIMIT` / `*_WINDOW` | `120`/`60` | `/auth/refresh` (no abuse cooldown) |
| `JOB_CREATE_RATE_LIMIT` | `20`/`60` | Creación de Jobs. |
| `UPLOAD_RATE_LIMIT` | `30`/`60` | Uploads. |
| `YOUTUBE_RATE_LIMIT` | `15`/`60` | YouTube/costosos. |
| `ANTI_ABUSE_VIOLATION_THRESHOLD` | `20` | Violaciones antes de cooldown. |
| `ANTI_ABUSE_COOLDOWN_SECONDS` | `300` | TTL cooldown. |

Endpoints caros: fail-closed si Redis cae. Detalle: `docs/MIGRATION_ANTI_ABUSE_FASE7.md`.

---

## 11. Frontend (Vite)

Archivo: `frontend/.env` (no el de la raíz). Prefijo `VITE_` = se embeben en el bundle.

| Variable | Default | Quién la lee | Efecto |
| --- | --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000` | `frontend/src/services/http.ts`, Playwright `e2e/helpers.ts` | `baseURL` de Axios. El navegador llama a este origen; Nginx `proxy_pass /api/` del contenedor frontend **no** se usa. |
| `VITE_API_KEY` | vacío → no manda key | `http.ts` | Header `X-API-KEY`. Debe igualar `API_KEY` del backend. |
| `VITE_OUT_DIR` | `dist` | `frontend/vite.config.ts` (`process.env`, no `import.meta.env`) | Directorio de build. Útil si `dist/` no es escribible. |

Vite también expone `import.meta.env.BASE_URL` (ruta pública, no se configura en `.env` salvo `VITE_BASE` estándar de Vite). Playwright usa `process.env.CI` para `forbidOnly`.

Build de producción (`frontend/Dockerfile`): si no hay `frontend/.env` en el contexto, el SPA cae a `http://localhost:8000`.

---

## 12. Benchmarks y scripts

Cargan el `.env` de la raíz.

| Variable | Default | Quién la lee | Efecto |
| --- | --- | --- | --- |
| `BREVIO_API_URL` | `http://localhost:8000` | `benchmarks/.../cli.py`, `scripts/run_document_summaries.py` | Base URL de la API viva. No la usa Docker. |
| `BREVIO_BENCHMARK_IDENTITY` | vacío | client/cli/script | Login del usuario de benchmark. **Compose no crea ese usuario.** |
| `BREVIO_BENCHMARK_PASSWORD` | vacío | igual | Password. |
| `API_KEY` | — | `run_document_summaries.py` | Misma key de catálogo. |
| `BREVIO_BENCHMARK_DOCS_DIR` | `/home/psych/Descargas/libros` (constante del CLI) | cli | Corpus por defecto. |
| `BREVIO_BENCHMARK_OUTPUT` | `benchmark` | cli | Directorio de resultados. |
| `BREVIO_LOGS_JSON` | `core/brevio_api/logs/logs.json` | cli | Telemetría para cruzar con el job. |
| `BREVIO_AUDIT_DIR` | ninguno | `runner.py` | Override del directorio de auditoría. |
| `TEMPERATURE` | `0.2` | runner/runtime | Se **registra** en el snapshot; no cambia el job (eso lo hace el worker). |
| `OLLAMA_API_URL` | default Ollama | `runtime.py` | Sonda `/api/show` y `/api/ps` (se le quita el sufijo `/v1`). |

---

## 13. Tests

| Variable | Default | Efecto |
| --- | --- | --- |
| `BREVIO_RUN_REDIS_TESTS` | unset → skip | Ejecuta tests marcados `redis`. |
| `PROVIDER_QUOTA_TEST_REDIS_URL` | `redis://127.0.0.1:6379/14` o `/15` | Redis efímero para tests de cuota. |
| `CI` | unset | Playwright `forbidOnly`. |
| `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_DATASETS_OFFLINE`, `TOKENIZERS_PARALLELISM` | fijadas por `conftest.py` (legacy) | Ya no hay stack HuggingFace en prod; tokens vía tiktoken. |

`conftest.py` también fija `ENVIRONMENT=test`, Mongo dummy, keys falsas, `SECRET_TOKEN_KEY`, Celery in-memory, `PROVIDER_QUOTA_ENABLED=false`, etc.

---

## 14. Checklist de producción

1. `ENVIRONMENT=production`
2. `SECRET_TOKEN_KEY` aleatorio largo; no uses el default.
3. `API_KEY` distinto del example; `VITE_API_KEY` igual en el build del frontend.
4. `CREDENTIAL_ENCRYPTION_KEY` (32 bytes Base64). Sin esto la API no arranca.
5. `COOKIE_SECURE=true` (o déjalo inferir de production) y HTTPS.
6. `CORS_ORIGINS` con los orígenes reales del SPA.
7. `TRUSTED_PROXY` con el CIDR real del hop que habla con el backend.
   - Compose de producción fija `app_network` en `172.28.0.0/16` → usar `TRUSTED_PROXY=172.28.0.0/16` cuando el único proxy es el nginx del servicio `frontend`.
   - Si hay Cloudflare / LB delante, sustituye por los CIDRs de **ese** hop (no están en el repo; no inventarlos).
   - Nunca `*`, `0.0.0.0/0` ni `::/0`.
8. `REDIS_PASSWORD` (≥16 chars) + opcional `REDIS_USERNAME=brevio`. El entrypoint ACL desactiva el usuario `default`. Las URLs Redis del `.env` pueden ir sin password; `resolve_redis_url()` inyecta credenciales.
9. Mongo con credenciales propias; `MONGODB_URI` coherente.
10. `LOG_LEVEL=INFO`
11. `PROVIDER_QUOTA_ENABLED=true`, YAML real, `PROVIDER_QUOTA_REDIS_URL` en una DB distinta a Celery.
12. Keys reales `OPENAI_` / `DEEPSEEK_` / `GOOGLE_` según proveedores que ofrezcas.
13. `EMAIL_FROM` + `EMAIL_PASSWORD` (app password Gmail) o el registro/OTP fallará.
14. `UPLOAD_MAGIC_BYTES_ENABLED=true` (default) y límites de upload.
15. No dejes `DEV_ALLOW_PLATFORM_OVERRIDE` como muleta: en production no abre el fallback.
16. No publiques `BREVIO_BENCHMARK_PASSWORD` ni placeholders de Mongo.
17. Tras cada release: ejecutar `pip-audit` contra `core/requirements.txt` en Python 3.12 (imagen de prod) y actualizar `docs/DEPENDENCY_SECURITY.md`.

---

## 15. Mapa rápido archivo → variables

| Módulo | Variables |
| --- | --- |
| `core/shared/utils/environment.py` | `ENVIRONMENT` y **todos** los helpers/alias (`MAX_TOKEN_PER_MINUTE`/`TOKENS_PER_MINUTE`, JWT, flags) |
| `core/brevio_api/config/dotenv.py` | `API_KEY`, snapshot JWT, `CORS_ORIGINS` |
| `core/brevio_api/services/token_service.py` | TTL JWT + secret/algorithm (en `__init__`) |
| `core/brevio_api/services/auth_cookies.py` | `COOKIE_SECURE`, `REFRESH_COOKIE_PATH`, `ENVIRONMENT` |
| `core/brevio_api/services/encryption_service.py` | `CREDENTIAL_ENCRYPTION_KEY`, `CREDENTIAL_ENCRYPTION_KEY_PREVIOUS`, `ENVIRONMENT` |
| `core/brevio_api/core/database.py` | `MONGODB_URI`, timeouts |
| `core/brevio_api/celery.py` | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `core/brevio_api/events/broker.py` | `EVENTS_REDIS_URL`, `CELERY_BROKER_URL` |
| `core/brevio_api/routers/events_router.py` | `EVENTS_SSE_HEARTBEAT_SECONDS` |
| `core/brevio_api/services/email_service.py` | `EMAIL_FROM`, `EMAIL_PASSWORD` |
| `core/brevio_api/__main__.py` | `LOG_LEVEL` |
| `core/brevio/services/summary_service.py` | TPM, temperatura, wait, FORMAT, partials, min postprocess |
| `core/brevio/services/summary_pipeline.py` | `BREVIO_KEEP_PARTIALS` |
| `core/brevio/models/config_model.py` | `MAX_TOKENS`, TPM, temperatura |
| `core/brevio/services/credential_resolver.py` | `{PROVIDER}_API_KEY` |
| `core/brevio/services/provider_registry.py` | `{PROVIDER}_API_URL` |
| `core/brevio/services/platform_access_policy.py` | `DEV_ALLOW_PLATFORM_OVERRIDE` |
| `core/brevio/services/summary_providers/access_policy.py` | `ENABLED_SUMMARY_PROVIDERS`, `SUMMARY_LOCAL_USER_ACCESS` |
| `core/brevio/services/transcription/access_policy.py` | transcripción enable/default/local access |
| `core/brevio/services/transcription/local_whisper_provider.py` | modelo/timeout Whisper |
| `core/brevio/services/transcription/openai_provider.py` | URL/timeout Whisper API / gpt-transcribe |
| `core/brevio/services/transcription/google_provider.py` | `GOOGLE_TRANSCRIPTION_TIMEOUT` |
| `core/brevio/services/transcription/xai_provider.py` | `XAI_TRANSCRIPTION_TIMEOUT` |
| `core/brevio/services/media_preprocessor.py` | `FFMPEG_TIMEOUT` |
| `core/brevio/services/provider_quota/*` | `PROVIDER_QUOTA_*`, `JOB_MAX_PROVIDER_REQUESTS`, MAP fallback |
| `core/shared/utils/pricing_registry.py` | bloque comercial `PRICING_*` / FX / créditos |
| `frontend/src/services/http.ts` | `VITE_API_URL`, `VITE_API_KEY` |
| `docker-compose*.yml` | puertos y, en dev, override de cuotas/partials |
