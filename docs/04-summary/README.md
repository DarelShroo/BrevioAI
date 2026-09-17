# 04 - Motor de Resúmenes (Summary Engine)

## Visión General

El motor de resúmenes (`SummaryService` y `SummaryPipeline`) es el núcleo duro de BrevioAI. Se encarga de procesar texto en bruto (proveniente de documentos PDF/DOCX o de transcripciones de audio/vídeo) y transformarlo en un resumen coherente, respetando estrictamente los límites de contexto de los modelos LLM (Large Language Models) y el presupuesto del usuario.

### Desafíos Principales que Resuelve

1.  **Límite de Contexto (Context Window):** Un libro entero de 800 páginas no cabe en el prompt de la mayoría de los LLMs. El sistema debe dividirlo inteligentemente sin perder el hilo conductor.
2.  **Límite de Salida (Max Output Tokens):** Los LLMs suelen tener un límite máximo de generación por respuesta (ej. 4096 tokens). El motor debe forzar múltiples llamadas si el resumen solicitado es muy extenso.
3.  **Presupuesto (Token Bucket):** Evitar que un solo trabajo abrume financieramente la API o consuma el límite de tokens por minuto (TPM) asignado a la plataforma.

### Sub-módulos

*   [Ciclo de Vida de un Trabajo](lifecycle.md)
*   [Procesamiento de Documentos](document-processing.md)
*   [Procesamiento Map/Reduce](map-reduce.md)
*   [Modelos y Proveedores](models.md)
*   [Configuración de Prompts](prompts.md)
*   [Cálculo de Costes (Tokens)](costs.md)
