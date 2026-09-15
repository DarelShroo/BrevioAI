# Proveedores de transcripción y resumen

La fuente de verdad de modelos, límites y parámetros **no** es este archivo. Vive en código:

- Resumen: `core/shared/enums/model.py`, `core/shared/utils/model_capabilities.py`, `core/shared/utils/model_catalog.py`, `core/shared/utils/pricing_registry.py`
- Transcripción: `core/brevio/services/transcription/models.py`
- HTTP de catálogo: `GET /brevio/models` y `GET /brevio/transcription-providers`

El frontend solo renderiza `parameters`, límites y `user_access` que envía el backend. Añadir un modelo nuevo debe tocar principalmente la definición del catálogo, el adapter del proveedor y, si aplica, precios. `SummaryService` y `TranscriptionService` no deben ramificar por proveedor.

Transcripción y resumen se eligen de forma independiente. El pipeline es:

```
Audio / Video / YouTube
  → adquisición de fuente / extracción de audio
  → TranscriptionProvider (texto normalizado)
  → SummaryProvider (pipeline MAP/REDUCE existente)
  → summary.md
```

## DEV vs PROD

- Local Whisper y modelos Ollama permanecen **implementados** en todos los entornos.
- En production no son seleccionables por el usuario final salvo `WHISPER_LOCAL_USER_ACCESS=true` / `SUMMARY_LOCAL_USER_ACCESS=true`.
- Las API keys de pago son BYOK (perfil). Las keys de plataforma en `.env` no se mezclan con Celery ni se hardcodean.
- Dependencias: producción instala solo `core/requirements.txt` (APIs cloud, sin PyTorch). Whisper local / PyTorch viven en `core/requirements.dev.txt` y en `core/Dockerfile.dev` (compose de desarrollo).

## Resumen (adapters)

| Provider | Adapter | Transporte |
| --- | --- | --- |
| openai | `OpenAISummaryProvider` | Chat Completions |
| google | `GeminiSummaryProvider` | Chat Completions OpenAI-compat |
| xai | `XAISummaryProvider` | Chat Completions OpenAI-compat |
| deepseek | `DeepSeekSummaryProvider` | Chat Completions OpenAI-compat |
| anthropic | `AnthropicSummaryProvider` | Messages API nativa (`/v1/messages`) |
| ollama | `OllamaSummaryProvider` | Chat Completions local (solo DEV salvo override) |

`max_output_tokens`, `temperature` y `context_window` son **solo backend**: el usuario no los configura ni los ve en la UI. Los valores salen de `model_capabilities.py` (defaults y límites oficiales del vendor). `summary_max_output_tokens` aplica el tope por llamada de Brevio (`min(nativo, 16384)`). `PromptConfig` descarta cualquier `max_output_tokens`/`temperature` del cliente.

El frontend solo muestra los ids de `parameters` de `GET /brevio/models` (hoy: `reasoning_effort` / `effort` cuando el modelo lo admite). Los adapters traducen a `max_tokens` / `max_completion_tokens` / Anthropic `max_tokens`, y omiten `temperature` si el vendor la rechaza.

DeepSeek admite thinking en su API; el pipeline de resumen lo deja desactivado (`thinking.type=disabled`) porque los tokens de razonamiento consumen el presupuesto de salida y vacían MAP/REDUCE. No se expone en la UI.

## Transcripción (adapters)

| Provider | Adapter | Endpoint oficial |
| --- | --- | --- |
| openai | `OpenAITranscriptionProvider` | `POST /v1/audio/transcriptions` |
| google | `GoogleTranscriptionProvider` | Files API + `models/gemini-3.5-transcribe:generateContent` |
| xai | `XAITranscriptionProvider` | `POST /v1/stt` (sin campo `model` oficial) |
| local_whisper | `LocalWhisperTranscriptionProvider` | proceso local |

La salida se normaliza a `TranscriptionResult` solo con campos que el proveedor realmente devuelve. Gemini 3.5 Transcribe admite diarization, timestamps y vocabulary biasing; Brevio no envía esos campos hasta tener el esquema REST cableado, y usa detección automática de idioma (documentada).

## Costes

Los precios de **tokens de resumen** están en `pricing_registry.py` (USD oficiales de input/output/cached). La estimación de documentos usa esos snapshots.

La transcripción de pago se factura con unidades distintas (minutos / audio tokens / hora). No se inventa `media_cost_per_minute` en el modelo de resumen. Referencias oficiales:

- OpenAI `gpt-transcribe`: $0.0045 / minuto de audio
- Gemini 3.5 Transcribe: $2.00 / 1M tokens de audio de entrada y $12.00 / 1M de salida (estimado oficial ~$0.005 / min)
- xAI Speech to Text REST: $0.10 / hora

## URLs oficiales consultadas

- https://platform.openai.com/docs/models/gpt-5.6
- https://platform.openai.com/docs/models/gpt-4o-mini
- https://platform.openai.com/docs/models/gpt-transcribe
- https://platform.openai.com/docs/guides/speech-to-text
- https://platform.openai.com/docs/deprecations
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/openai
- https://docs.x.ai/docs/models
- https://docs.x.ai/docs/models/grok-4.6
- https://docs.x.ai/developers/grok-4-6
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-text
- https://api-docs.deepseek.com/quick_start/pricing
- https://docs.anthropic.com/en/docs/about-claude/models/overview
- https://docs.anthropic.com/en/docs/about-claude/models/whats-new-sonnet-5
- https://docs.anthropic.com/en/docs/about-claude/models/extended-thinking-models
