# Indexación y Rendimiento (Indexes)

Debido a que BrevioAI no usa un ORM y no tiene migraciones automatizadas tradicionales como Alembic (en SQL), **los índices se declaran y construyen por código (Repositories) durante el arranque de la aplicación**.

## El patrón `ensure_indexes()`

Cada repositorio de base de datos (ej. `FolderRepository`, `CreditAccountRepository`) tiene un método `ensure_indexes()`.
Cuando un servicio necesita hacer una operación crítica, llama a este método al menos una vez por ciclo de vida de la aplicación.
MongoDB crea los índices en *background* y de forma idempotente (si ya existe, no hace nada).

### Ejemplos de Índices Críticos

1.  **Unique Indexes (Evitar Duplicados):**
    *   `email` en `Users`: `db.users.create_index("email", unique=True)`.
    *   `job_id` en `CreditReservation`: Evita que por un fallo de red o doble clic, se reserven dos veces los mismos créditos para un mismo documento.
2.  **TTL Indexes (Expiración Automática):**
    *   Para documentos que solo deben vivir temporalmente (ej. Tokens de Reset de Contraseña), MongoDB los borra de forma automática sin que FastAPI haga un cron, usando `expireAfterSeconds`.
3.  **Compound Indexes (Consultas Múltiples):**
    *   Búsquedas por `(user_id, status)` en el historial de trabajos para acelerar la carga del Dashboard de los usuarios.

## Transaccionalidad

MongoDB soporta transacciones multi-documento (ACID), pero requieren configurar Replica Sets. Para que BrevioAI funcione en entornos Standalone (docker-compose local simple), **BrevioAI evita usar transacciones**.
En su lugar, diseña la lógica para ser idempotente y usa modificadores atómicos como `$set`, `$inc`, y *find_and_modify* con comparadores `$gte` (mayor o igual) para evitar condiciones de carrera (Race Conditions) al actualizar saldo de créditos.
