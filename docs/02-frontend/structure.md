# Estructura y Componentes del Frontend

La estructura de carpetas en `frontend/src/` sigue un estándar modular de Vue:

```text
src/
├── components/   # Componentes reutilizables de UI y lógica
├── composables/  # Funciones Vue Composition (e.g., useToast)
├── layouts/      # Plantillas principales (AppLayout, AuthLayout, DemoLayout)
├── router/       # Configuración de Vue Router y Guards
├── services/     # Clientes API (llamadas HTTP a FastAPI)
├── stores/       # Pinia stores (Estado global)
└── views/        # Páginas de nivel superior
```

## Páginas Principales (Views)

*   `SummaryView.vue`: La pantalla principal (Dashboard). Contiene pestañas para subir Documentos, Multimedia o enlaces de YouTube. Se encarga de ensamblar la petición (`PromptConfig`) y escuchar las respuestas.
*   `StoreView.vue` (posiblemente referenciado internamente como Library/History): Vista donde el usuario puede explorar trabajos anteriores.
*   `ProfileView.vue`: Gestión de perfil, contraseñas, BYOK (credenciales de usuario) y facturación.
*   `PlansView.vue`: Muestra las opciones de suscripción/créditos (Pricing).
*   `CompareView.vue` (`/comparar`): Una página pública de demostración que permite ver ejemplos de generación sin estar autenticado.
*   `auth/*`: Vistas de registro, login y recuperación de contraseña.

## Stores Principales (Pinia)

*   `auth.store.ts`: Maneja el ciclo de vida de la sesión (Login, Logout, hidratación de perfil, verificación de roles).
*   `realtime.store.ts`: Fundamental para la **arquitectura asíncrona**. Mantiene conexiones SSE con el Backend para actualizar el estado de los trabajos de generación en las vistas, sin recargar la página.
*   `catalog.store.ts`: Almacena y cachea las configuraciones dinámicas provenientes del backend, como los modelos LLM disponibles, idiomas soportados y proveedores de transcripción.

## Capa de Servicios (`services/`)

Aquí reside la lógica de comunicación con el Backend. Aisla a los componentes de Vue de la librería `axios` o `fetch` directa.

*   `brevio.service.ts`: Maneja las llamadas críticas como `estimateDocuments`, `submitDocuments`, `submitMedia`, y descargas (`downloadSummary`).
*   `credentials.service.ts`: CRUD para gestionar las claves de API (BYOK) introducidas por los usuarios.
