# Tests Herméticos (Offline por defecto)

El archivo `conftest.py` es el guardián del entorno de pruebas. Su misión es asegurar que los tests se puedan ejecutar en un avión sin internet o en un servidor de Integración Continua (CI) sin consumir dólares de las APIs.

## 1. Bloqueo de Red (`httpx`)

BrevioAI hace "monkey-patching" (sobrescritura en tiempo de ejecución) de los métodos `send` de `httpx.AsyncClient` y `httpx.Client`.
Cualquier intento de hacer una petición HTTP hacia internet (por ejemplo, a `api.openai.com`) fallará inmediatamente con un `RuntimeError`. Solo se permiten llamadas a `testserver` (el servidor de pruebas interno de FastAPI).

## 2. Tokenización sin modelos locales

La producción y los tests usan **tiktoken** para estimar tokens. No se instalan
`transformers`, HuggingFace Hub, PyTorch ni tokenizers de modelos locales en
`requirements.txt` de producción.

## 3. Opt-in para Redis

Las pruebas que dependen de un Redis real están marcadas con `@pytest.mark.redis`. Por defecto, estas pruebas se saltan (Skip) para que los tests pasen rápido en máquinas que no tienen Redis instalado. Para ejecutarlas, el desarrollador debe establecer la variable `BREVIO_RUN_REDIS_TESTS=1`.
