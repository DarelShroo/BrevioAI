# BrevioAI

BrevioAI incluye:

- Backend API (FastAPI)
- Worker asincrono (Celery)
- Frontend (Vue + Nginx)
- Base de datos (MongoDB)
- Cola de mensajes (Redis)

Todo se ejecuta con Docker Compose.

## Requisitos

- Docker Engine 24+ (o compatible)
- Docker Compose Plugin (`docker compose`)
- Minimo recomendado: 8 GB RAM

Comprobar instalacion:

```bash
docker --version
docker compose version
```

## Estructura de Compose

- `docker-compose.yml`: configuracion base de la rama master (perfil NVIDIA)
- `docker-compose.amd.yml`: configuracion para portatiles/equipos AMD

## Configuracion inicial

1. Clona el repositorio y entra al directorio:

```bash
git clone <repository-url>
cd BrevioAI
```

2. Verifica archivo de entorno para backend:

```bash
ls core/.env
```

Si no existe, crea `core/.env` usando como referencia `core/brevio_api/.env.example`.

3. Selecciona perfil de entorno para transcripcion:

- `core/.env.dev`: usa `ENVIRONMENT=development` (transcripcion local con Whisper).
- `core/.env.prod`: usa `ENVIRONMENT=production` (transcripcion remota via OpenAI).

Puedes activar un perfil copiandolo a `core/.env`:

```bash
cp core/.env.dev core/.env
```

o

```bash
cp core/.env.prod core/.env
```

En `production` debes definir `OPENAI_API_KEY` en `core/.env`.

## Levantar proyecto (NVIDIA / compose principal)

Desde la raiz:

```bash
docker compose up -d --build
```

Servicios esperados:

- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/api/docs`
- Frontend: `http://localhost:80`
- MongoDB: `localhost:27017`
- Redis: `localhost:6380`

## Levantar proyecto (AMD)

Usa el archivo AMD:

```bash
docker compose -f docker-compose.amd.yml up -d --build
```

Notas:

- Este compose usa `core/Dockerfile.amd`.
- Instala `torch` en variante CPU para evitar dependencias CUDA/NVIDIA.
- El primer build puede tardar varios minutos.

Servicios esperados en AMD:

- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/api/docs`
- Frontend: `http://localhost:8080`
- MongoDB: `localhost:27017`
- Redis: `localhost:6380`

## Verificar estado

```bash
docker compose -f docker-compose.amd.yml ps
```

Probar endpoints:

```bash
curl -I http://localhost:8000/api/docs
curl -I http://localhost:8080
```

## Parar servicios

NVIDIA/base:

```bash
docker compose down
```

AMD:

```bash
docker compose -f docker-compose.amd.yml down
```

## Troubleshooting

1. MongoDB sale con lock o estado inconsistente

```bash
docker compose -f docker-compose.amd.yml down -v
docker compose -f docker-compose.amd.yml up -d
```

2. Backend responde 404 en `/docs`

La ruta configurada del proyecto es `/api/docs`.

3. Forzar rebuild completo

```bash
docker compose -f docker-compose.amd.yml build --no-cache
docker compose -f docker-compose.amd.yml up -d
```

4. Ver logs de un servicio

```bash
docker compose -f docker-compose.amd.yml logs -f backend
docker compose -f docker-compose.amd.yml logs -f celery
docker compose -f docker-compose.amd.yml logs -f database
```

## Limpieza total (imagenes, contenedores y volumenes del proyecto)

```bash
docker compose -f docker-compose.amd.yml down -v --rmi local
```
