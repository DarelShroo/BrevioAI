# 02 - Frontend

## Visión General

El Frontend de BrevioAI está construido con **Vue 3** (Composition API) utilizando **TypeScript**. Es una Single Page Application (SPA) robusta que gestiona la configuración de los trabajos (jobs) del usuario, el seguimiento en tiempo real y la gestión de planes y facturación.

### Stack Tecnológico Principal

*   **Framework:** Vue 3 (Composition API, `<script setup>`).
*   **Lenguaje:** TypeScript.
*   **Estado Global:** Pinia (stores modulares).
*   **Enrutamiento:** Vue Router.
*   **Componentes de UI:** PrimeVue (versión sin estilos base, estilizado customizado o con utility classes).
*   **Gestión del Tiempo Real:** Server-Sent Events (SSE) y Polling manual como *fallback*.
*   **Internacionalización:** `vue-i18n` (Soporte multilingüe para la interfaz).
*   **Bundler/Tooling:** Vite.

### Principios de Diseño del Frontend

1.  **Modularidad:** Las vistas principales delegan la lógica pesada en componentes específicos (ej. `SummaryParamsForm`, `EstimatePanel`).
2.  **Validación Robusta:** El Frontend pre-valida el acceso (si el usuario tiene créditos, si puede usar un modelo) antes de hacer peticiones costosas al Backend.
3.  **Feedback Continuo:** Como los trabajos de IA son lentos, el Frontend siempre muestra al usuario el estado (`QUEUED`, `PROCESSING`, `COMPLETED`) utilizando Server-Sent Events (SSE).
