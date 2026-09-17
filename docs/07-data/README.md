# 07 - Gestión de Datos (Database)

## Visión General

BrevioAI utiliza una arquitectura persistente basada puramente en bases de datos NoSQL y en Memoria, evitando el uso de SQL (PostgreSQL, MySQL) debido a la naturaleza dinámica de los metadatos de los trabajos de Inteligencia Artificial.

### Stack de Datos

1.  **MongoDB (Principal):** Única fuente de verdad persistente (Single Source of Truth). Almacena Usuarios, Trabajos, Facturación y Configuraciones.
2.  **Redis (Transitorio):** Usado para:
    *   Gestión de la Cola de Tareas (Celery Broker & Result Backend).
    *   Rate Limiting global y por IP/Usuario.
    *   Lista Negra (Denylist) de Tokens JWT (Logout instantáneo).
    *   Caché efímera.
3.  **S3 / MinIO (Object Storage):** Almacenamiento binario de los archivos físicos (.pdf, .docx, audio). MongoDB nunca almacena archivos binarios grandes, solo las URLs (`storage_path`) que apuntan al bucket de S3.

### Sub-módulos

*   [Modelos de Datos y Colecciones](models.md)
*   [Indexación y Rendimiento](indexes.md)
