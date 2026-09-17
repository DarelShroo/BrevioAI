# BrevioAI: Documentación Oficial

Bienvenido a la documentación oficial de BrevioAI. Esta documentación está diseñada para explicar **cómo funciona realmente la aplicación**, basándose en la implementación real del código, no solo en la teoría.

## Índice Principal

### 1. Visión General
* [¿Qué es BrevioAI?](01-overview/README.md)
* [Arquitectura del Sistema](01-overview/architecture.md)
* [Flujo General de la Aplicación](01-overview/application-flow.md)

### 2. Frontend
* [Frontend Overview](02-frontend/README.md)
* [Estructura y Componentes](02-frontend/structure.md)
* [Flujos de Usuario (User Flows)](02-frontend/user-flows.md)

### 3. Backend & API
* [Backend Overview](03-backend/README.md)
* [API y Endpoints Principales](03-backend/api.md)
* [Servicios Core](03-backend/services.md)
* [Flujo de Datos Interno](03-backend/data-flow.md)

### 4. Motor de Summary (Prioridad Alta)
* [Generación de Summaries](04-summary/README.md)
* [Ciclo de Vida de un Trabajo (Job)](04-summary/lifecycle.md)
* [Procesamiento de Documentos](04-summary/document-processing.md)
* [Procesamiento Map/Reduce](04-summary/map-reduce.md)
* [Modelos y Proveedores](04-summary/models.md)
* [Configuración de Prompts](04-summary/prompts.md)
* [Cálculo de Costes (Tokens)](04-summary/costs.md)

### 5. Billing y Planes (Prioridad Alta)
* [Sistema de Billing](05-billing/README.md)
* [Planes de Usuario](05-billing/plans.md)
* [Créditos y Consumo](05-billing/credits.md)
* [Cálculo de Costes (Estimados vs Reales)](05-billing/cost-calculation.md)
* [Registro de Uso](05-billing/usage.md)
* [Bring Your Own Key (BYOK)](05-billing/byok.md)
* [Límites y Anti-Abuso](05-billing/limits.md)

### 6. Autenticación y Seguridad
* [Autenticación (Overview)](06-auth-security/README.md)
* [Tokens JWT (Access & Refresh)](06-auth-security/jwt-tokens.md)
* [Revocación de Sesiones](06-auth-security/session-revocation.md)
* [Hardening y Cabeceras](06-auth-security/security-headers.md)

### 7. Datos y Persistencia
* [Base de Datos (Overview)](07-data/README.md)
* [Modelos de Datos y Colecciones](07-data/models.md)
* [Indexación y Rendimiento](07-data/indexes.md)

### 8. Infraestructura
* [Infraestructura (Overview)](08-infrastructure/README.md)
* [Gestión de Contenedores (Docker)](08-infrastructure/docker.md)
* [Redes y Seguridad (Networking)](08-infrastructure/networking.md)

### 9. Testing
* [Estrategia de Tests (Overview)](09-testing/README.md)
* [Tests Herméticos (Offline)](09-testing/hermetic-tests.md)
* [Mocking y Aislamiento](09-testing/mocking.md)

### 0. Análisis
* [Hallazgos e Inconsistencias](00-analysis/findings.md)
