# Procesamiento de Documentos Físicos

Antes de que un texto pueda ser resumido, debe ser extraído de su formato original.

## Flujo de Entrada (Inputs)

1.  **Documentos (PDF, DOCX, TXT):**
    *   El sistema utiliza librerías especializadas (como `pdfplumber` o similar dependiendo del binding de FastAPI).
    *   Se lee el texto plano. Se remueven cabeceras, índices (Table of Contents) gigantes que puedan aportar "ruido" al LLM.
2.  **Multimedia (Audio / Video / YouTube):**
    *   Para YouTube: se utiliza `yt-dlp` para descargar la pista de audio.
    *   El audio pasa por el `TranscriptionService`, el cual llama a Whisper (Local o API de OpenAI) para convertir el audio a texto.
    *   A partir de aquí, el archivo de transcripción (texto plano) se trata exactamente igual que un PDF.

## Chunking (Particionado)

Una vez se tiene el texto extraído (`full_text`), se evalúa su longitud usando `tiktoken` (contando los tokens exactos para el modelo objetivo, ej. `gpt-4o`).

*   **¿Cabe en el Context Window?**
    Si `tokens_texto < (Límite_Contexto - Margen_Seguridad)`, se utiliza la ruta `DIRECT_RUNNING`.
*   **No Cabe (Chunking):**
    Si el documento es masivo, entra a la función `chunk_text`.
    *   Se divide el texto en fragmentos que se acercan al límite máximo del modelo (`max_tokens_per_chunk`).
    *   **Solapamiento (Overlap):** Para no cortar ideas a la mitad (ej. una frase cortada entre el final del Chunk 1 y el principio del Chunk 2), se añade un solapamiento (ej. 20%). Esto asegura continuidad narrativa.

```python
# Ejemplo mental del algoritmo de Chunking
chunks = []
overlap_tokens = chunk_size * 0.2
while no_fin_de_texto:
    chunks.append(texto[start : start + chunk_size])
    start = start + chunk_size - overlap_tokens
```
