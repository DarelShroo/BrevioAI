class Constants:
    TRANSCRIPTION_FILE = "transcription.txt"
    SUMMARY_FILE = "summary.md"
    ALL_TRANSCRIPTIONS = "all_transcriptions.txt"
    ALL_SUMMARIES = "all_summaries.md"
    DESTINATION_FOLDER = "audios"
    CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque técnico preciso, siguiendo estas directrices:

    Mantén un balance entre concisión y profundidad, explicando los conceptos técnicos esenciales sin extenderse innecesariamente.
    Excluye contenido promocional, enlaces, recomendaciones o recursos externos.
    Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
    Explica términos técnicos cuando sea necesario sin caer en redundancias.
    Incluye ejemplos de código solo si son esenciales.
    Evita explicaciones innecesarias.

Formato:

## Título Principal

Explicación técnica clara y precisa del tema.

### Características clave

    **Concepto 1**: Explicación técnica breve.
    **Concepto 2**: Profundización técnica si es necesario.

### Detalles técnicos

    **Aspecto relevante**: Explicación técnica sin redundancias.
    **Ejemplo de código (si es necesario)**:
    ```js // Código relevante ```
"""
