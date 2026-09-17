# Mocking y Aislamiento (Database & Celery)

## 1. Aislamiento de Variables de Entorno

`conftest.py` inyecta un diccionario `_ISOLATED_ENV` al arrancar. Esto significa que los tests ignoran por completo tu archivo `.env` local.
*   Las claves API (OpenAI, Anthropic) se sobreescriben con `sk-pytest-isolated-not-real`.
*   El secreto del JWT se cambia a `pytest-isolated-secret`.
*   Esto asegura que nadie corrompa la base de datos de desarrollo por error al correr `pytest`.

## 2. Aislamiento de MongoDB

La clase `AsyncDB` (el cliente principal de MongoDB) es "parcheada" (mocked) mediante la inyección de `MagicMock`. 
Por defecto, ninguna prueba de unidad toca una base de datos real. Todas las respuestas de base de datos (`find_one`, `update`) deben ser emuladas en cada test (usando `unittest.mock.patch` o `pytest-mock`), asegurando que las pruebas corren en milisegundos.

## 3. Celery Offline

Las tareas de Celery se configuran con:
```env
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
```
Esto permite que el backend pueda encolar tareas durante las pruebas unitarias sin necesidad de arrancar un worker de Celery separado ni un clúster de RabbitMQ/Redis.
