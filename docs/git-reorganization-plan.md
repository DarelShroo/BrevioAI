# Plan de Reorganización Git — BrevioAI

## 1. Estado Inicial e Inventario

- **Fecha de inspección:** 15 de octubre de 2026
- **Rama activa de trabajo:** `main` (sigue a `origin/master`)
- **Rama principal remota:** `origin/master` (HEAD remota apunta a `origin/master`)
- **Commit base de partida:** `51fd21fbededda5ec3610800c2464b85e2ea41cf` (`test: añade y actualiza tests unitarios y e2e del frontend`)
- **Total de ficheros con modificaciones:** 126 archivos únicos (96 modificados, 30 nuevos sin rastreo inicial)
- **Estrategia de respaldo preventivo:**
  - Rama de respaldo base: `backup/base-before-reorg-51fd21f`
  - Rama de instantánea completa (árbol y untracked): `backup/full-snapshot-wip-20261015` (`0441b4835a86ea8881450a6f13dab5dca9f3b1ff`)
  - Archivos de respaldo físico en almacenamiento persistente: parches `.patch` y archivo comprimido `.tar.gz` de archivos sin rastrear.

---

## 2. Clasificación Semántica de Cambios

Se han definido 9 unidades de trabajo cohesivas y temáticas para organizar los 126 ficheros:

### Grupo 1: `build/infra-docker-dependencies`
- **Tipo:** `build` / `chore`
- **Objetivo:** Actualización de dependencias base de Python y Node, configuración de contenedores Docker y optimizaciones del arnés de pruebas.
- **Ficheros (10):**
  - `.env.example`
  - `.pre-commit-config.yaml`
  - `core/Dockerfile.dev`
  - `core/requirements.txt`
  - `database/Dockerfile`
  - `docker-compose.yml`
  - `frontend/Dockerfile`
  - `frontend/package.json`
  - `frontend/package-lock.json`
  - `frontend/playwright.config.ts`
- **Dependencias:** Ninguna (base).
- **Riesgo:** Bajo.

### Grupo 2: `feat/linguistic-resources-engine`
- **Tipo:** `feat`
- **Objetivo:** Módulo central de recursos lingüísticos para 12 idiomas y soporte de títulos e idioma en el renderizado y exportación de PDFs.
- **Ficheros (18):**
  - `core/brevio/constants/linguistic/__init__.py`
  - `core/brevio/constants/linguistic/arabic.py`
  - `core/brevio/constants/linguistic/base.py`
  - `core/brevio/constants/linguistic/chinese.py`
  - `core/brevio/constants/linguistic/english.py`
  - `core/brevio/constants/linguistic/french.py`
  - `core/brevio/constants/linguistic/german.py`
  - `core/brevio/constants/linguistic/hindi.py`
  - `core/brevio/constants/linguistic/italian.py`
  - `core/brevio/constants/linguistic/japanese.py`
  - `core/brevio/constants/linguistic/korean.py`
  - `core/brevio/constants/linguistic/portuguese.py`
  - `core/brevio/constants/linguistic/registry.py`
  - `core/brevio/constants/linguistic/russian.py`
  - `core/brevio/constants/linguistic/spanish.py`
  - `core/brevio/tests/services/test_linguistic_resources.py`
  - `core/brevio/services/pdf_export/pdf_renderer.py`
  - `core/brevio/services/pdf_export/pdf_styles.css`
- **Dependencias:** Grupo 1.
- **Riesgo:** Bajo.

### Grupo 3: `refactor/core-summary-quality-and-providers`
- **Tipo:** `refactor` / `feat`
- **Objetivo:** Integración del modelo Qwen3-VL-30B-A3B y proveedor RunAI, políticas de saliencia adaptativa, compresión en documentos extensos, renderizado inline HTML de diagramas y filtros de calidad multilingües.
- **Ficheros (22):**
  - `core/shared/enums/model.py`
  - `core/shared/models/history_token_model.py`
  - `core/shared/utils/model_capabilities.py`
  - `core/shared/utils/pricing_registry.py`
  - `core/shared/utils/model_catalog.py`
  - `core/shared/utils/adaptive_salience_policy.py`
  - `core/shared/utils/chunking_utils.py`
  - `core/shared/utils/summary_quality.py`
  - `core/brevio/config/provider_quotas.example.yaml`
  - `core/brevio/services/provider_quota/retry.py`
  - `core/brevio/services/provider_registry.py`
  - `core/brevio/services/summary_providers/openai_compatible.py`
  - `core/brevio/services/summary_providers/registry.py`
  - `core/brevio/generate.py`
  - `core/brevio/managers/directory_manager.py`
  - `core/brevio/services/diagram_processor.py`
  - `core/brevio/services/summary_service.py`
  - `core/brevio/tests/services/test_diagram_processor.py`
  - `core/brevio/tests/services/test_empty_documents.py`
  - `core/brevio/tests/services/test_reduce_truncation_contract.py`
  - `core/brevio/tests/services/test_summary_large_document.py`
  - `core/brevio/tests/services/test_summary_quality_contract.py`
- **Dependencias:** Grupo 2 (`feat/linguistic-resources-engine`).
- **Riesgo:** Medio.

### Grupo 4: `feat/backend-i18n-and-error-codes`
- **Tipo:** `feat`
- **Objetivo:** Catálogo de códigos de error unificados (`ApiErrorCode`, `CodedHTTPException`) y localización de respuestas en el backend.
- **Ficheros (7):**
  - `core/brevio_api/models/errors/api_codes.py`
  - `core/brevio_api/i18n/__init__.py`
  - `core/brevio_api/i18n/catalog.py`
  - `core/brevio_api/i18n/locale.py`
  - `core/brevio_api/handlers/exception_handlers.py`
  - `core/brevio_api/routers/examples_router.py`
  - `core/brevio_api/tests/test_i18n_backend.py`
- **Dependencias:** Grupo 1.
- **Riesgo:** Bajo.

### Grupo 5: `feat/credentials-and-auth-validation`
- **Tipo:** `feat`
- **Objetivo:** Resolución de credenciales con comprobación previa de disponibilidad de proveedores locales y validación de autenticación tipada por códigos.
- **Ficheros (8):**
  - `core/brevio/services/credential_resolver.py`
  - `core/brevio/tests/services/test_credential_resolver.py`
  - `core/brevio_api/models/auth/auth_base.py`
  - `core/brevio_api/models/auth/auth.py`
  - `core/brevio_api/routers/user_credential_router.py`
  - `core/brevio_api/tests/routers/test_auth_router.py`
  - `frontend/src/services/credentials.service.ts`
  - `frontend/src/__tests__/services/credentials.service.test.ts`
- **Dependencias:** Grupo 4 (`feat/backend-i18n-and-error-codes`).
- **Riesgo:** Bajo a Medio.

### Grupo 6: `feat/billing-stripe-resilience`
- **Tipo:** `feat`
- **Objetivo:** Resiliencia en webhooks de Stripe, matriz de consistencia financiera ante fallos e integración dinámica de planes.
- **Ficheros (7):**
  - `core/brevio/config/commercial_plans.yaml`
  - `core/brevio_api/routers/plans_router.py`
  - `core/brevio_api/routers/stripe_router.py`
  - `core/brevio_api/services/billing/stripe_service.py`
  - `core/brevio_api/tests/routers/test_stripe_router.py`
  - `core/brevio_api/tests/services/test_financial_consistency_matrix.py`
  - `core/brevio_api/tests/services/test_stripe_billing.py`
- **Dependencias:** Grupo 4 (`feat/backend-i18n-and-error-codes`).
- **Riesgo:** Medio.

### Grupo 7: `feat/job-lifecycle-and-realtime-events`
- **Tipo:** `feat`
- **Objetivo:** Trazabilidad estricta de ciclo de vida de trabajos, eventos SSE (`create_progress`, `create_failed`), incrustación de SVG en resúmenes generados y prueba e2e integral.
- **Ficheros (13):**
  - `core/brevio_api/events/models.py`
  - `core/brevio_api/events/publisher.py`
  - `core/brevio_api/services/progress/reporter.py`
  - `core/brevio_api/services/user_service.py`
  - `core/brevio_api/routers/brevio_router.py`
  - `core/brevio_api/services/brevio_service.py`
  - `core/brevio_api/tests/conftest.py`
  - `core/brevio_api/tests/services/test_job_lifecycle_fase2.py`
  - `core/brevio_api/tests/services/test_brevio_service.py`
  - `core/brevio_api/tests/services/test_anti_abuse_fase7.py`
  - `core/brevio_api/tests/services/test_estimation_service.py`
  - `core/brevio_api/tests/routers/test_brevio_router.py`
  - `core/brevio_api/tests/integration/test_real_e2e_journey.py`
- **Dependencias:** Grupo 3 y Grupo 4.
- **Riesgo:** Medio.

### Grupo 8: `feat/frontend-i18n-localization`
- **Tipo:** `feat`
- **Objetivo:** Actualización completa de mensajes para 12 idiomas en la interfaz de usuario, tests de paridad de claves y tests contra cadenas hardcodeadas.
- **Ficheros (14):**
  - `frontend/src/i18n/messages/ar.ts`
  - `frontend/src/i18n/messages/de.ts`
  - `frontend/src/i18n/messages/en.ts`
  - `frontend/src/i18n/messages/es.ts`
  - `frontend/src/i18n/messages/fr.ts`
  - `frontend/src/i18n/messages/hi.ts`
  - `frontend/src/i18n/messages/it.ts`
  - `frontend/src/i18n/messages/ja.ts`
  - `frontend/src/i18n/messages/ko.ts`
  - `frontend/src/i18n/messages/pt.ts`
  - `frontend/src/i18n/messages/ru.ts`
  - `frontend/src/i18n/messages/zh.ts`
  - `frontend/src/__tests__/i18n/anti-hardcode.test.ts`
  - `frontend/src/__tests__/i18n/i18n-completeness.test.ts`
- **Dependencias:** Grupo 4.
- **Riesgo:** Bajo.

### Grupo 9: `feat/frontend-ui-reactivity-and-views`
- **Tipo:** `feat`
- **Objetivo:** Reactividad en tiempo real en StoreView para barras de progreso SSE, soporte de tema oscuro en demostraciones, acceso controlado a modelos y actualización de pruebas unitarias y e2e.
- **Ficheros (27):**
  - `frontend/src/utils/errors.ts`
  - `frontend/src/utils/labels.ts`
  - `frontend/src/utils/models.ts`
  - `frontend/src/utils/processingAccess.ts`
  - `frontend/src/services/http.ts`
  - `frontend/src/stores/catalog.store.ts`
  - `frontend/src/stores/library.store.ts`
  - `frontend/src/stores/realtime.store.ts`
  - `frontend/src/composables/useJobPolling.ts`
  - `frontend/src/composables/useRealtimeNotifications.ts`
  - `frontend/src/components/auth/AuthHeroPanel.vue`
  - `frontend/src/components/common/ProgressBar.vue`
  - `frontend/src/components/demo/DemoPdfViewer.vue`
  - `frontend/src/components/demo/SyncCompareDemo.vue`
  - `frontend/src/components/store/DownloadResultsDialog.vue`
  - `frontend/src/components/store/StoreEntryCard.vue`
  - `frontend/src/components/summary/SummaryParamsForm.vue`
  - `frontend/src/layouts/AuthLayout.vue`
  - `frontend/src/views/ProfileView.vue`
  - `frontend/src/views/StoreView.vue`
  - `frontend/src/views/SummaryView.vue`
  - `frontend/src/__tests__/components/UserMenu.test.ts`
  - `frontend/src/__tests__/utils/models.test.ts`
  - `frontend/src/__tests__/utils/processingAccess.test.ts`
  - `frontend/src/__tests__/views/StoreView.reactivity.test.ts`
  - `frontend/e2e/app.spec.ts`
  - `frontend/e2e/helpers.ts`
- **Dependencias:** Grupo 8 (`feat/frontend-i18n-localization`) y Grupo 7 (`feat/job-lifecycle-and-realtime-events`).
- **Riesgo:** Medio.

---

## 3. Grafo de Dependencias y Orden de Integración

```
[Base: 51fd21f]
       │
       ├─► 1. build/infra-docker-dependencies
       │          │
       │          ├─► 2. feat/linguistic-resources-engine
       │          │          │
       │          │          └─► 3. refactor/core-summary-quality-and-providers
       │          │
       │          └─► 4. feat/backend-i18n-and-error-codes
       │                     │
       │                     ├─► 5. feat/credentials-and-auth-validation
       │                     ├─► 6. feat/billing-stripe-resilience
       │                     ├─► 7. feat/job-lifecycle-and-realtime-events (combina 3 y 4)
       │                     └─► 8. feat/frontend-i18n-localization
       │                                │
       │                                └─► 9. feat/frontend-ui-reactivity-and-views (combina 7 y 8)
```

### Secuencia de Fusión Progresiva:
1. `build/infra-docker-dependencies` -> `main`
2. `feat/linguistic-resources-engine` -> `main`
3. `refactor/core-summary-quality-and-providers` -> `main`
4. `feat/backend-i18n-and-error-codes` -> `main`
5. `feat/credentials-and-auth-validation` -> `main`
6. `feat/billing-stripe-resilience` -> `main`
7. `feat/job-lifecycle-and-realtime-events` -> `main`
8. `feat/frontend-i18n-localization` -> `main`
9. `feat/frontend-ui-reactivity-and-views` -> `main`

Cada paso incluye validación y pruebas automatizadas pertinentes antes de avanzar al siguiente.
