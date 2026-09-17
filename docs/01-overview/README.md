# 01 - Visión General

## ¿Qué es BrevioAI?

**BrevioAI** es una plataforma avanzada orientada a la generación asíncrona de resúmenes (summaries) a partir de documentos (PDF, DOCX) y contenido multimedia (Audio, Video, YouTube).

A diferencia de un chat interactivo simple, BrevioAI está diseñado para manejar **cargas de trabajo pesadas de forma robusta**, lo que significa que el procesamiento de un documento complejo puede durar varios minutos. Para asegurar que este proceso no falle por problemas de red, timeouts o limitaciones de los proveedores de IA, la aplicación divide el trabajo en múltiples pasos asíncronos y utiliza un potente motor de particionado de documentos (chunking y map-reduce).

### Características Principales

*   **Soporte Multimodal:** Extrae texto de PDFs complejos, documentos de Word, audios y vídeos de YouTube (transcripción).
*   **Procesamiento Asíncrono Robusto:** Utiliza un sistema de colas (Redis + Celery) y un programador equitativo (Fair Scheduler) para manejar la concurrencia y evitar la saturación del sistema.
*   **Gestión de Cuotas y Facturación:** Implementa un sistema de créditos granular que estima el coste en tokens antes de procesar un trabajo, hace una reserva, y luego asienta el coste real, protegiendo tanto al usuario como a la plataforma frente a abusos.
*   **Procesamiento Map/Reduce:** Permite resumir documentos masivos que superan el límite de contexto de cualquier modelo de Inteligencia Artificial al dividirlos inteligentemente, resumir las partes, y luego combinar los resultados de forma iterativa.
*   **Personalización:** Soporta configuraciones de estilo, formatos de salida (markdown, pdf, docx), nivel de detalle, e idioma de forma agnóstica al documento original.

### Destinatarios de la Documentación

Esta documentación está pensada para:
1.  **Desarrolladores:** Para entender cómo mantener, escalar y agregar nuevas funcionalidades al Core de generación y la API.
2.  **Operadores / DevOps:** Para entender el flujo de la infraestructura (Redis, Mongo, Celery) y la gestión de picos de carga.
3.  **Gestión de Producto:** Para entender con precisión matemática cómo funciona el sistema de facturación (Billing), cómo se limitan los recursos y cómo interactúan los planes de usuario (Free, Pro, etc.) con el consumo de la IA.
