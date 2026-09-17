# Modelos de Datos y Colecciones

La aplicación FastAPI NO usa un ORM pesado (como Beanie o MongoEngine). Usa el cliente asíncrono puro **Motor (`AsyncIOMotorClient`)** junto con Pydantic para validar los datos en los bordes de la aplicación.
Esto permite consultas complejas nativas y operaciones de rendimiento crítico (como `$inc` en facturación) sin la sobrecarga de un ORM.

## Pydantic como Interfaz

Los modelos de Pydantic (`models/`) se usan para:
1.  Validar el Input HTTP.
2.  Estructurar el Output (Swagger UI).
3.  Servir como "Schemas" mentales en el código, pero el Repositorio inyecta diccionarios planos (dicts) a MongoDB.

## Arquitectura de Dominios

Los modelos están separados por contextos lógicos (`core/brevio_api/models/`):

1.  **`user/`:** `User`, `UserSettings`. Maneja la identidad básica.
2.  **`auth/`:** Manejo de Login, Reset Password y Familias de Tokens.
3.  **`brevio/`:** Todo lo relacionado con el producto.
    *   `FolderEntry`: Representa un "Trabajo" de resumen lógico.
    *   `SummaryResult`: El artefacto resultante y sus tokens consumidos.
4.  **`billing/`:** Modelos de la Fase 3, 5 y 6. (Revisar [Módulo Billing](../05-billing/README.md)).
    *   `CreditAccount`: Saldo de la billetera.
    *   `CreditReservation`: Bloqueos de saldo temporales.
    *   `CostRecord` / `UsageRecord`: Facturación física y a nivel usuario.
