# Configuración de Prompts (PromptConfig)

La generación en BrevioAI es altamente parametrizable. El objeto `PromptConfig` viaja desde el Frontend hasta las entrañas del worker de Celery.

## Parámetros del PromptConfig

1.  **Language (Idioma Objetivo):**
    El idioma al que se debe traducir/escribir el resumen (Ej. `LanguageType.SPANISH`). BrevioAI es independiente del idioma de entrada; lee en alemán y resume en inglés si se le pide.
2.  **Summary Level (Nivel de Detalle):**
    *   `VERY_CONCISE`, `CONCISE`, `MODERATE`, `DETAILED`, `VERY_DETAILED`.
    *   **Impacto Real:** No solo cambia las palabras del prompt. Cambia matemáticamente la función `_reduce_batch_token_limit`. Un resumen "VERY_DETAILED" forzará al algoritmo a hacer reducciones más "suaves" (agrupando menos texto por ronda) para no perder datos por el camino, lo que inevitablemente aumenta el coste en tokens.
3.  **Category (Categoría Temática):**
    *   Ej. `ACADEMIC`, `LEGAL`, `GENERAL`.
    *   Inyecta terminología y reglas específicas (ej. "Mantén el rigor legal y cita jurisprudencia si aparece").
4.  **Style (Estilo):**
    *   Ej. `BULLET_POINTS`, `NARRATIVE`.
    *   Cambia la estructura del output (ej. "Usa guiones", "Usa párrafos conectados").
5.  **Format (Formato Técnico):**
    *   Ej. `MARKDOWN`, `PDF`, `DOCX`.
    *   Afecta a la exportación final (Fase de Finalización).

## Generador Avanzado (`AdvancedPromptGenerator`)

En lugar de usar un prompt gigantesco de texto plano concatenado, BrevioAI utiliza un sistema dinámico que ensambla el "System Prompt" como piezas de Lego, dependiendo de la combinación exacta de `Language`, `SummaryLevel`, `Category` y `Style`.
