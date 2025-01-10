class Constants:
    TRANSCRIPTION_FILE = "transcription.txt"
    SUMMARY_FILE = "summary.md"
    ALL_TRANSCRIPTIONS = "all_transcriptions.txt"
    ALL_SUMMARIES = "all_summaries.md"
    DESTINATION_FOLDER = "audios"
    CONTENT = """
            Genera un resumen muy breve y preciso en formato Markdown del siguiente texto. El resumen debe cumplir con las siguientes directrices:

            - **Limitarse únicamente a las ideas esenciales.** No incluir detalles secundarios, explicaciones largas ni redundancias.
            - **Excluir completamente contenido promocional**, como:
              - Enlaces a sitios web o menciones de productos.
              - Llamadas a la acción, recomendaciones o recursos adicionales.
              - Comentarios sobre contenido educativo o instrucciones para usuarios.
            - Utilizar un tono técnico, profesional y adecuado para una audiencia académica.
            - Emplear títulos jerárquicos (#, ##, ###) y listas con viñetas para organizar la información de forma clara.
            - **Resaltar términos clave** en **negrita** o *cursiva* solo si es estrictamente necesario.
            - Evitar incluir ejemplos de código salvo en casos esenciales para ilustrar un concepto técnico.
            - **El resumen debe ser lo más breve posible**, omitiendo cualquier detalle innecesario.
            - Organizar el contenido con un formato visual limpio, sin caracteres de salto de línea `\n` en el texto.

            **Texto original:**
            [Texto del contenido a resumir.]

            **Texto transformado:**

            ## Título Principal

            [Un resumen conciso de las ideas principales, sin detalles superfluos.]

            ### Características principales

            - **Punto clave 1**
            - **Punto clave 2**
            - [Agregar otros puntos clave, si los hay.]

            [El contenido debe ser claro, directo y contener solo lo fundamental, presentado en formato Markdown correctamente estructurado.]"""
