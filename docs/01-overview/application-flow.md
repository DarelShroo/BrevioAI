# Flujo General de la Aplicación

Este documento describe el flujo completo end-to-end (de extremo a extremo) cuando un usuario solicita un resumen en BrevioAI. Se enfoca en ilustrar cómo interactúan los componentes de la arquitectura en el tiempo.

## El Viaje de una Petición

### 1. Preparación en el Frontend
1.  El usuario inicia sesión (obtiene JWT y cookies).
2.  Accede a la vista principal (`SummaryView.vue`).
3.  Selecciona archivos (PDF, DOCX) o pega una URL (YouTube).
4.  Configura las opciones (Idioma, Modelo LLM, Nivel de Detalle, Formato).
5.  El Frontend valida los tipos de archivo y rellena el formulario de parámetros (`PromptConfig`).

### 2. Estimación Local (Opcional, pero recomendada)
1.  El usuario puede hacer clic en "Estimar".
2.  El Frontend llama al endpoint `/brevio/estimate-documents`.
3.  El Backend (`EstimationService`) extrae rápidamente texto del PDF en memoria.
4.  Utiliza una librería local (`tiktoken`) para contar tokens. No se llama a OpenAI/Anthropic.
5.  Devuelve al Frontend una estimación: "Este PDF tiene ~10,000 tokens, requerirá 2 pasos de Chunking, y costará ~50 créditos".

### 3. Solicitud y Pre-Vuelo (Preflight)
1.  El usuario hace clic en "Procesar".
2.  La petición llega a los routers de FastAPI (ej. `/brevio/summary-documents`).
3.  Se aplican **filtros Anti-Abuso** vía Redis: ¿El usuario está enviando demasiados trabajos por minuto?
4.  Se ejecuta el **Preflight**: Se verifica si el usuario tiene saldo o una API Key propia válida (BYOK), y si el modelo solicitado está permitido en su plan.

### 4. Admisión Comercial y Reserva
1.  Se estima el coste *máximo* y *esperado* (similar al paso de estimación).
2.  El `ProductLimitService` y `CreditService` evalúan la petición: "¿Puede el usuario permitirse este coste máximo estimado?".
3.  Si la respuesta es afirmativa, se **bloquean (reservan)** los créditos en el saldo del usuario. Esto evita que el usuario gaste los mismos créditos en dos procesos paralelos (condición de carrera).
4.  Si no hay créditos suficientes, la solicitud se rechaza con un HTTP 402 (Payment Required).

### 5. Inserción del Trabajo y Scheduler
1.  Los archivos se guardan físicamente en disco o almacenamiento persistente (`Constants.DESTINATION_FOLDER`).
2.  Se crea un registro `FolderEntry` en MongoDB con el estado `QUEUED`.
3.  El trabajo se registra en el **Fair Scheduler** (vía Redis). El Scheduler decide si el trabajo entra inmediatamente a ejecución (Dispatch) o si debe esperar porque la infraestructura está muy cargada.

### 6. Despacho (Dispatch) a Celery
1.  Una vez el Scheduler da luz verde, el Backend ejecuta `process_summary_task.delay(job_id)`.
2.  El mensaje viaja por Redis hacia un Worker libre de Celery.
3.  El endpoint de FastAPI responde al Frontend con un HTTP 202 (Accepted) y el `job_id`.

### 7. Procesamiento Asíncrono (El Worker)
1.  Un Worker de Celery reclama el trabajo y lo marca como `PROCESSING` en MongoDB.
2.  Extrae el texto del documento (o transcribe el audio).
3.  Pasa el texto al **Motor Map/Reduce**:
    *   Si el texto es corto, hace una llamada directa al LLM.
    *   Si el texto es muy grande, lo divide en *Chunks*, resume cada Chunk en paralelo (MAP), y luego combina los resúmenes de forma estructurada (REDUCE).
4.  Guarda los archivos resultantes (Markdown, PDF, DOCX).

### 8. Asentamiento (Settlement)
1.  El Worker calcula el número real de tokens devueltos por el proveedor (OpenAI, Anthropic).
2.  Ejecuta `settle_job_credits`.
3.  Si la estimación inicial retuvo 50 créditos y la ejecución final solo usó 30, se devuelven 20 créditos al saldo del usuario de forma atómica.
4.  El trabajo se marca como `COMPLETED` en MongoDB.

### 9. Consumo por el Cliente
1.  Durante todo este tiempo (pasos 6, 7 y 8), el Frontend ha estado haciendo tracking del `job_id` (vía Polling o SSE a través de `realtime.store.ts`).
2.  Al detectar el cambio a `COMPLETED`, el Frontend muestra el botón de Descarga.
3.  El usuario descarga el resultado final.
