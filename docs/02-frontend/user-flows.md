# Flujos de Usuario (User Flows) en el Frontend

## 1. Flujo de Generación de un Resumen (SummaryView)

Este es el flujo interactivo más importante del Frontend:

1.  **Selección de Archivos:** El usuario arrastra un archivo al componente `FilePicker`. Se evalúa el tipo de archivo y tamaño inicial.
2.  **Configuración de Parámetros:** El componente `SummaryParamsForm` despliega los menús (Idioma, Modelo, Estilo).
3.  **Comprobación de Capacidad (BYOK/Credits):**
    *   Variables computadas (ej. `summaryBlocked`, `transcriptionBlocked`) verifican en el `auth.store` (créditos) y las credenciales si el usuario puede iniciar el trabajo.
    *   Si necesita clave API (BYOK) y no la tiene, se bloquea el botón y se le insta a ir al Perfil.
4.  **Estimación (EstimatePanel):**
    *   Si el usuario clica en "Estimar", se llama a `brevioService.estimateDocuments`.
    *   La UI dibuja un desglose de Tokens Esperados, Tokens Máximos, y Créditos requeridos (Mostrando advertencias si el documento es muy largo).
5.  **Envío (Submit):**
    *   Al clicar en "Procesar", se bloquea el formulario (`submitting = true`).
    *   Se hace la petición Multipart HTTP con los binarios y el payload.
    *   Al recibir el HTTP 202, se obtiene un `folder_entry_id` (Job ID).
6.  **Tracking (Realtime):**
    *   Se dispara `watchJob(folder_entry_id)`.
    *   El `realtime.store` inicia un EventSource (SSE) y el componente `StateBlock` pasa a mostrar un spinner de estado (`QUEUED`, `PROCESSING`).
7.  **Finalización:** Cuando SSE notifica el estado `COMPLETED`, aparece el botón de Descarga (`download(resultIndex)`).

## 2. Flujo de Autenticación y Guards

*   El usuario visita `/`.
*   Vue Router intercepta mediante `requireAuth` (en `guards.ts`).
*   Se llama a `auth.hydrate()`.
*   Si la hidratación (que usa las cookies seguras HTTP-only y tokens JWT) es válida, accede. Si no, es redirigido a `/auth/login`.

## 3. Gestión de Configuración (Catalog)

Cuando la aplicación se carga (`onMounted` en `SummaryView`), se invoca a `catalog.loadAll()`. Esto rellena dinámicamente:
*   ¿Qué modelos de IA están encendidos hoy? (OpenAI, Anthropic).
*   ¿Qué proveedores de transcripción están habilitados? (Local Whisper, Google, etc.).
Esto permite a la administración del backend apagar un modelo problemático y que el Frontend lo elimine automáticamente de los menús sin necesidad de redesplegar.
