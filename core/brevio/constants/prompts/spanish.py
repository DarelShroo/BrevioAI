from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class SpanishPrompts:
    INSTRUCTIONS_TITLE: str = "**Instrucciones:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Idioma específico:** Español"
    SPECIFIC_LANGUAGE: str = (
        "A partir de ahora, todas las respuestas deben estar únicamente en español."
    )
    EXAMPLE_TITLE: str = "**Ejemplo**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["Resumen directo sin encabezados adicionales"]},
            "styles": {
                "default": {
                    "tone": "Neutral, adaptado al contexto",
                    "elements": [],
                    "source_types": [
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                }
            },
            "rules": [
                "Resumir el contenido de la fuente: temas, definiciones, hechos, procedimientos y ejemplos importantes",
                "Escribe en tercera persona. Prohibido primera persona (aprendí, necesito aclarar, me ayudaría)",
                "No inventes preguntas, ejercicios, dudas ni secciones de 'puntos a aclarar' o 'lo que aprendí'",
                "No conviertas el documento en un diario de aprendizaje ni en deberes de estudiante",
                "Preservar el título original si está presente, sin modificaciones, usando su redacción y formato exactos (ej: # Título, ## Subtítulo)",
                "Usa encabezados solo si el documento original tiene secciones reales equivalentes",
                "Mantener ejemplos o conceptos clave en su formato original (ej: listas, código, cursivas)",
                "No añadir conocimiento externo ni afirmaciones que la fuente no respalde",
            ],
            "needs": "Simplicidad y fidelidad al contenido original",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Evento] En Vivo",
                    "- **[MM:SS]** Declaración o dato clave",
                    "- **[MM:SS]** Descripción de momento clave o desarrollo",
                    "- **[MM:SS]** Reacción o análisis del evento",
                ],
                "news_wire": [
                    "[Fecha] - [Ubicación] - Resumen breve y directo",
                    "### Detalles Clave",
                    "- [Dato clave 1]",
                    "- [Dato clave 2]",
                    "### Contexto",
                    "- [Información de fondo]",
                    "### Estadísticas (si aplica)",
                    "- [Estadística 1]",
                    "- [Estadística 2]",
                    "### Impacto",
                    "- [Impacto a corto plazo]",
                    "- [Implicaciones a largo plazo]",
                ],
                "analysis": [
                    "## [Tema] En Profundidad",
                    "### Resumen",
                    "- [Breve resumen del tema]",
                    "### Aspectos Clave",
                    "- [Aspecto 1]: [Análisis detallado]",
                    "- [Aspecto 2]: [Análisis detallado]",
                    "### Implicaciones",
                    "- [Implicaciones a corto plazo]",
                    "- [Implicaciones a largo plazo]",
                    "### Opiniones de Expertos",
                    "- [Cita o perspectiva de un experto]",
                    "### Conclusión",
                    "- [Resumen de hallazgos clave y perspectivas futuras]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, urgente",
                    "elements": ["cronología", "momentos clave", "reacciones"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Directo, informativo",
                    "elements": [
                        "detalles clave",
                        "contexto",
                        "estadísticas",
                        "impacto",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "Reflexivo, contextual",
                    "elements": [
                        "resumen",
                        "aspectos clave",
                        "implicaciones",
                        "opiniones de expertos",
                        "conclusión",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Incluir marcas de tiempo precisas para crónicas",
                "Citar fuentes si aplica",
                "Evitar opiniones en cables de noticias",
                "Usar viñetas para detalles clave en cables de noticias",
                "Incluir al menos una estadística o dato en cables de noticias",
                "Destacar impactos a corto y largo plazo en cables de noticias",
                "Para crónicas, enfocarse en momentos clave y reacciones en tiempo real",
                "Para análisis, explorar el tema en detalle, incluyendo causas, efectos y perspectivas expertas",
            ],
            "needs": [
                "Velocidad en cables de noticias, detalle en crónicas, contexto en análisis"
            ],
        },
        "marketing": {
            "structures": {
                "highlights": ["# ✨ [Campaña] - Destacados", "🎯 **Clave:** Valor"],
                "storytelling": [
                    "## [Marca] - Una Historia: [Título]",
                    "### Introducción",
                    "- [Gancho emocional o ambientación]",
                    "### Narrativa Principal",
                    "- [Evento clave o punto de inflexión]",
                    "- [Desafíos o conflictos]",
                    "- [Resolución o resultado]",
                    "### Impacto Emocional",
                    "- [Cómo la historia hace sentir a la audiencia]",
                    "### Llamado a la Acción",
                    "- [Invitación a interactuar con la marca o producto]",
                ],
                "report": [
                    "## [Campaña] - Resultados",
                    "### Resumen",
                    "- [Breve resumen de la campaña y sus objetivos]",
                    "### Métricas Clave",
                    "| **Métrica** | **Meta** | **Real** | **Variación** |",
                    "|------------|----------|------------|--------------|",
                    "| [Métrica 1] | [Meta 1] | [Real 1] | [Variación 1] |",
                    "| [Métrica 2] | [Meta 2] | [Real 2] | [Variación 2] |",
                    "### Análisis",
                    "- [Análisis detallado de resultados, incluyendo éxitos y desafíos]",
                    "### Recomendaciones",
                    "- [Recomendaciones accionables basadas en datos]",
                    "### Conclusión",
                    "- [Resumen de hallazgos clave y próximos pasos]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Atractivo, visual",
                    "elements": ["emojis", "viñetas"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Emocional, inmersivo",
                    "elements": [
                        "narrativa",
                        "gancho_emocional",
                        "llamado_a_la_acción",
                    ],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analítico, claro",
                    "elements": ["tabla", "análisis", "recomendaciones"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Usar lenguaje atractivo para destacados y storytelling",
                "Incluir KPIs en informes",
                "Evitar tecnicismos excesivos",
                "Para storytelling, enfocarse en conexión emocional y flujo narrativo",
            ],
            "needs": "Impacto visual, conexión emocional, datos accionables",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Estudio/Tratamiento] - Reporte Clínico:**",
                    "Párrafo técnico conciso y basado en datos, enfocado en resultados y eficacia",
                ],
                "summary": [
                    "# 🩺 [Tema] - Resumen",
                    "📈 **Indicador:** Resultado",
                    "| Semana | Progreso |",
                ],
                "case": ["**[Paciente] - Caso Clínico:**", "Narrativa detallada"],
            },
            "styles": {
                "report": {
                    "tone": "Formal, preciso y basado en evidencia",
                    "elements": ["datos_cuantitativos", "resultados_clínicos"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visual, accesible",
                    "elements": ["viñetas", "tabla"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "Narrativo, clínico",
                    "elements": ["narrativa"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "Siempre incluir datos cuantitativos y medibles cuando estén disponibles",
                "Mantener rigor científico y evitar lenguaje subjetivo",
                "Ajustar complejidad del lenguaje según audiencia (técnico para doctores, simplificado para pacientes)",
                "Garantizar claridad, precisión y accesibilidad de la información médica",
            ],
            "needs": {
                "doctors": "Datos clínicos claros y precisos para toma de decisiones informadas",
                "patients": "Explicaciones accesibles y comprensibles de condiciones y tratamientos",
                "researchers": "Información robusta y basada en datos para análisis",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Versión] - Actualización",
                    "✨ **Nuevas Funcionalidades:**",
                    "- Función",
                    "🐛 **Correcciones:**",
                    "- Corrección",
                ],
                "proposal": [
                    "# [Proyecto] - Propuesta Técnica",
                    "## Introducción",
                    "Breve descripción del proyecto, sus objetivos y el problema que busca resolver.",
                    "## Objetivos",
                    "- Objetivo 1: Describir la primera meta del proyecto.",
                    "- Objetivo 2: Describir la segunda meta del proyecto.",
                    "## Enfoque Técnico",
                    "Explicar la solución técnica, incluyendo herramientas, frameworks y metodologías a usar.",
                    "### Características Clave",
                    "- Característica 1: Describir la primera característica clave.",
                    "- Característica 2: Describir la segunda característica clave.",
                    "## Beneficios",
                    "Destacar ventajas de la solución propuesta, como eficiencia, escalabilidad o ahorro de costos.",
                    "## Plan de Implementación",
                    "Proveer un cronograma general o pasos para implementar la solución.",
                    "## Riesgos y Mitigación",
                    "Identificar riesgos potenciales y proponer estrategias para mitigarlos.",
                    "## Conclusión",
                    "Resumir la propuesta y reiterar su valor.",
                ],
                "diagram": [
                    "# [Proceso] - Flujo",
                    "```mermaid",
                    "graph TD",
                    "  A[Inicio] --> B{¿Decisión?}",
                    "  B -->|Sí| C[Proceso 1]",
                    "  B -->|No| D[Proceso 2]",
                    "  C --> E[Fin]",
                    "  D --> E",
                    "```",
                    "**Anotaciones:**",
                    "- **A**: Inicio del proceso.",
                    "- **B**: Punto de decisión.",
                    "- **C/D**: Rutas alternativas.",
                    "- **E**: Fin del proceso.",
                    "**Colores:**",
                    "- **Verde**: Ruta exitosa (ej: usuario logueado).",
                    "- **Rojo**: Ruta alternativa (ej: usuario no logueado).",
                    "**Leyenda:**",
                    "- **Rectángulo**: Paso del proceso.",
                    "- **Diamante**: Punto de decisión.",
                    "- **Círculo**: Inicio/Fin.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Técnico, conciso",
                    "elements": ["viñetas"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Persuasivo, claro y estructurado",
                    "elements": ["encabezados", "viñetas", "tablas"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visual, descriptivo y modular",
                    "elements": ["mermaid", "colores", "anotaciones", "leyenda"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
            },
            "rules": [
                "Usar terminología técnica relevante al proyecto.",
                "Destacar beneficios de la solución propuesta para persuadir a stakeholders.",
                "Incluir un plan de implementación claro y estructurado.",
                "Abordar riesgos potenciales y proponer estrategias de mitigación.",
                "Usar viñetas y encabezados para mejorar legibilidad.",
                "Proveer ejemplos concretos o casos de estudio para respaldar la propuesta.",
                "Garantizar que la propuesta sea modular y fácil de actualizar.",
                "Incluir una conclusión que resuma el valor de la propuesta.",
            ],
            "needs": "Persuasión para stakeholders, claridad en enfoque técnico, documentación estructurada e insights accionables",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Tema] - Guía",
                    "## [Sección]",
                    "- **Concepto:** Explicación con ejemplos prácticos y aplicaciones.",
                ],
                "quick_ref": [
                    "**[Tema] - Referencia Rápida:**",
                    "- [Punto clave]: Resumen breve y accionable con contexto práctico claro.",
                ],
                "timeline": [
                    "# 🎥 [Clase] - Cronología",
                    "- **[MM:SS]** [Concepto clave o acción realizada]: [Explicación breve y clara con resultados o acciones, destacando aplicación en el mundo real].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educativo, estructurado, con ejemplos para mayor claridad y comprensión",
                    "elements": [
                        "subsecciones",
                        "viñetas",
                        "ejemplos",
                        "aplicaciones_reales",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Conciso, práctico, diseñado para aprendizaje rápido y aplicación",
                    "elements": ["viñetas", "resúmenes_claros"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Cronológico, enfocado en acciones, claro con énfasis en aplicaciones reales",
                    "elements": [
                        "cronología",
                        "acciones_paso_a_paso",
                        "señales_visuales",
                        "contexto_real",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Proveer explicaciones claras y accionables con ejemplos para mejor comprensión.",
                "Priorizar cobertura y fidelidad; la concisión no justifica omitir temas principales.",
                "Asegurar alineación con objetivos de aprendizaje y contexto para facilitar retención.",
                "Enfatizar claridad y usabilidad, especialmente para casos de uso reales.",
            ],
            "needs": "Facilitar estudio rápido, referencia ágil y seguimiento en video con insights prácticos.",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Proyecto] - Crónica",
                    "- **[MM:SS]** Elemento destacado",
                ],
                "report": [
                    "**[Proyecto] - Reporte Técnico:**",
                    "Párrafo con detalles clave",
                ],
                "list": ["# [Proyecto] - Detalles", "- **Aspecto:** Descripción"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, visual",
                    "elements": ["cronología"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Técnico, detallado",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptivo, organizado",
                    "elements": ["viñetas"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Destacar innovación o sostenibilidad",
                "Incluir datos técnicos si aplica",
                "Ser visualmente atractivo",
            ],
            "needs": "Documentación técnica, presentación atractiva, seguimiento en video",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Período] - Reporte Financiero",
                    "- **Indicador**: [Valor]",
                ],
                "table": [
                    "## [Período] - Resumen Financiero",
                    "| **Indicador** | **Valor** |",
                ],
                "executive": [
                    "**[Período] - Resumen Ejecutivo:**",
                    "Párrafo breve e impactante destacando insights clave.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analítico, formal",
                    "elements": ["viñetas"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "Visual, conciso",
                    "elements": ["tabla"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Directo, ejecutivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Garantizar claridad y concisión al presentar cifras clave.",
                "Evitar ambigüedad en la presentación de datos.",
                "Apoyar la toma de decisiones ofreciendo insights accionables.",
                "Los títulos de tablas deben formatearse sin espacios extra antes o después de los asteriscos dobles.",
            ],
            "needs": "Datos accionables, síntesis visual clara y resúmenes ejecutivos enfocados en impacto.",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Destino] - Crónica",
                    "- **[MM:SS]** Iniciativa",
                    "- **[MM:SS]** Hito importante",
                ],
                "report": [
                    "**[Destino] - Políticas:**",
                    "Párrafo formal con énfasis en los objetivos del destino y su impacto en el turismo",
                ],
                "list": [
                    "# [Destino] - Iniciativas",
                    "- **Área:** Detalle (considerar añadir cultura local o atracciones)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, atractivo, inmersivo",
                    "elements": ["cronología", "storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formal, informativo, objetivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptivo, claro, informativo",
                    "elements": ["viñetas", "datos_concísos"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Destacar sostenibilidad, significado cultural y atractivo turístico",
                "Incluir información práctica para viajeros (ej: mejor época para visitar, atracciones locales, contactos esenciales)",
                "Enfocarse en descripciones claras, concisas y precisas de políticas e iniciativas",
                "Evitar exageraciones, ser realista e informativo",
            ],
            "needs": "Promoción atractiva con información relevante, presentación clara de políticas y detalles prácticos para turistas",
        },
        "requirements": {
            "structures": {
                "elicitation": [
                    "Requisitos de [Proyecto/Nombre] - Elicitación",
                    "Contexto",
                    "- Reunión: [Fecha, participantes, objetivo].",
                    "- Alcance: [Propósito o resultado esperado].",
                    "Requisitos Funcionales",
                    "- RF-[ID]: [Descripción clara]. (Prioridad: [Alta/Media/Baja], Justificación: [Breve motivo]).",
                    "Requisitos No Funcionales",
                    "- RNF-[ID]: [Descripción, ej: calidad, tiempo]. (Prioridad: [Alta/Media/Baja], Justificación: [Motivo]).",
                    "Dependencias y Restricciones",
                    "- Dependencia: [Relación con otros requisitos/recursos].",
                    "- Restricción: [Limitaciones, ej: presupuesto, tiempo].",
                    "Preguntas Pendientes",
                    "- [Pregunta por aclarar].",
                    "Marcas de Tiempo (Si Aplica)",
                    "- [MM:SS]: [Cita breve de la fuente].",
                    "Criterios de Priorización",
                    "- Alta: Crítico para el éxito o urgencia.",
                    "- Media: Importante, pero no esencial.",
                    "- Baja: Deseable, posponible.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Claro, objetivo, adaptable",
                    "elements": ["viñetas", "IDs", "prioridades"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Extraer requisitos directamente, sin interpretaciones.",
                "Usar IDs (RF-01, RNF-01) para trazabilidad.",
                "Priorizar con justificación (impacto/urgencia).",
                "Usar lenguaje claro, enfocado en 'qué' se necesita.",
                "Listar ambigüedades en 'Preguntas Pendientes'.",
                "Marcas de tiempo solo para requisitos clave.",
            ],
            "needs": "Captura clara de requisitos para cualquier proyecto, facilitando planificación y comunicación.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Tema] - Guía",
                    "## [Sección]",
                    "- **Concepto:** Definición, principio, relación, proceso, mecanismo, clasificación o evidencia relevante.",
                ],
                "formula_reference": [
                    "# 🔬 [Tema] - Referencia de Fórmulas",
                    "## Fórmulas Principales",
                    "| Fórmula | Significado | Variables | Unidades | Condiciones |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Tema] - Desarrollo",
                    "## Punto de Partida",
                    "- [Definición, principio, ecuación, observación, dato o condición inicial presente en la fuente.]",
                    "## Desarrollo",
                    "1. [Primer paso o razonamiento presente en la fuente.]",
                    "2. [Transformación, relación, procedimiento o razonamiento presente en la fuente.]",
                    "## Resultado",
                    "- **Resultado:** [Resultado o conclusión obtenida en la fuente.]",
                ],
                "quick_ref": [
                    "**[Tema] - Referencia Rápida:**",
                    "- **Concepto:** Definición breve.",
                    "- **Principio/Ley/Teoría:** Relación fundamental.",
                    "- **Proceso/Relación:** Descripción esencial.",
                    "- **Dato/Fórmula:** Información cuantitativa relevante.",
                    "- **Condición:** Aplicabilidad o limitación.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educativo, riguroso y estructurado",
                    "elements": [
                        "conceptos",
                        "principios",
                        "leyes",
                        "teorías",
                        "modelos",
                        "procesos",
                        "mecanismos",
                        "estructuras",
                        "relaciones",
                        "datos",
                        "fórmulas",
                        "ejemplos",
                        "evidencias",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Técnico, compacto y preciso, orientado a consulta y aplicación correcta",
                    "elements": [
                        "fórmulas",
                        "variables",
                        "unidades",
                        "relaciones",
                        "condiciones",
                        "tablas",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formal, lógico y riguroso, preservando el razonamiento realmente sustentado por la fuente",
                    "elements": [
                        "ecuaciones",
                        "procedimientos",
                        "deducciones",
                        "secuencias",
                        "razonamientos",
                        "suposiciones",
                        "condiciones",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Conciso, técnico y práctico, diseñado para repaso rápido sin perder precisión científica",
                    "elements": [
                        "conceptos clave",
                        "principios",
                        "leyes",
                        "teorías",
                        "procesos",
                        "fórmulas",
                        "datos",
                        "condiciones",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
            },
            "rules": [
                "Utilizar exclusivamente la información presente en la fuente.",
                "No introducir conocimiento externo aunque sea científicamente correcto, conocido, obvio o útil para completar la explicación.",
                "No inventar, completar, corregir ni reinterpretar contenido que no esté sustentado por la fuente.",
                "Las estructuras son únicamente una guía de organización y no obligan a crear contenido para completar secciones.",
                "No incluir una sección cuando la fuente no contenga información suficiente para justificarla.",
                "Preservar definiciones, principios, leyes, teorías, hipótesis, modelos, procesos, mecanismos, clasificaciones, relaciones, datos, fórmulas, variables, unidades, evidencias y condiciones relevantes presentes en la fuente.",
                "Mantener el significado original de términos científicos, símbolos, variables, magnitudes, relaciones, procesos y mecanismos.",
                "No transformar una hipótesis, modelo, observación, correlación, asociación o resultado experimental en un hecho, ley o relación causal no establecida por la fuente.",
                "No generalizar resultados, mecanismos o conclusiones más allá de las condiciones, población, sistema, escala o contexto indicados en la fuente.",
                "Preservar excepciones, límites, supuestos, restricciones, incertidumbres y condiciones de validez cuando afecten a la interpretación.",
                "Cuando existan datos cuantitativos, conservar valores, unidades, relaciones, órdenes de magnitud y precisión relevante.",
                "Cuando existan fórmulas o relaciones matemáticas, preservar signos, exponentes, índices, operadores, variables, unidades, aproximaciones y condiciones de validez.",
                "No realizar conversiones, cálculos, transformaciones algebraicas o inferencias cuantitativas adicionales que no estén presentes o inequívocamente sustentadas por la fuente.",
                "Cuando exista una derivación, demostración, procedimiento, experimento o razonamiento secuencial, conservar únicamente los pasos esenciales realmente sustentados por la fuente.",
                "No añadir pasos intermedios, mecanismos, causas o explicaciones que la fuente no presente o no permita establecer inequívocamente.",
                "Conservar las relaciones temporales, causales, funcionales, estructurales y jerárquicas cuando sean relevantes para comprender correctamente el contenido.",
                "No confundir correlación con causalidad ni asociación con mecanismo.",
                "No eliminar información cuya ausencia pueda cambiar el significado, interpretación, resultado o ámbito de aplicación del contenido.",
                "Eliminar redundancias y formulaciones repetitivas sin eliminar información científica necesaria.",
                "Reducir la explicación, no el significado.",
                "En caso de conflicto, priorizar en este orden: fidelidad a la fuente, exactitud científica, preservación del significado y condiciones, claridad, estructura y finalmente concisión.",
                "El objetivo es representar de forma compacta y precisa el conocimiento contenido en la fuente, no proporcionar una explicación general del tema basada en conocimiento externo.",
            ],
            "needs": (
                "Máxima fidelidad y precisión científica, preservando conceptos, "
                "procesos, mecanismos, relaciones, datos, fórmulas, evidencias, "
                "condiciones, límites y razonamiento esencial presentes en la fuente, "
                "sin introducir conocimiento externo ni completar información ausente."
            ),
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "El contenido describe medidas económicas anunciadas el 08 de marzo de 2025, incluyendo reducciones de impuestos y líneas de crédito."
        },
        "journalism": {
            "chronicle": (
                "# Evento de Apple En Vivo\n"
                "- **[00:03:00]** Tim Cook sube al escenario para presentar Apple Intelligence, un nuevo sistema de IA integrado en dispositivos Apple.\n"
                "- **[00:05:11]** Presentación del Apple Watch Series 10, destacando su pantalla más grande y diseño más delgado.\n"
                "- **[00:07:03]** Demostración de la nueva pantalla OLED, 40% más brillante en ángulos oblicuos.\n"
                "- **[00:09:06]** Anuncio de que el Series 10 es 10% más delgado que el Series 9, con un grosor de solo 9.7 mm.\n"
                "- **[00:10:19]** Introducción de carga rápida: 80% de batería en 30 minutos.\n"
                "- **[00:11:03]** Presentación del acabado en titanio pulido, 20% más ligero que el acero inoxidable.\n"
                "- **[00:12:00]** Énfasis en sostenibilidad: 95% de titanio reciclado y 100% energía renovable en manufactura.\n"
                "- **[00:13:50]** Nuevas funciones de salud: Detección de apnea del sueño y monitoreo de temperatura corporal para seguimiento de ovulación.\n"
                "- **[00:15:19]** Discusión sobre la importancia de la detección de apnea del sueño, con 80% de casos sin diagnosticar globalmente."
            ),
            "news_wire": (
                "[08 de marzo, 2025] - Capital - Presidente anuncia medidas económicas.\n"
                "### Detalles Clave\n"
                "- Reducción de impuestos para familias de clase media.\n"
                "- Mayor gasto en proyectos de infraestructura.\n"
                "### Contexto\n"
                "- Las medidas buscan impulsar el crecimiento económico ante la inflación creciente.\n"
                "### Estadísticas\n"
                "- Pronóstico de crecimiento del PIB: 2.5% para 2025.\n"
                "- Tasa de desempleo: 5.8% (bajó desde 6.3% el año pasado).\n"
                "### Impacto\n"
                "- Corto plazo: Alivio inmediato para familias de clase media.\n"
                "- Largo plazo: Se espera estimular el crecimiento económico y crear empleos."
            ),
            "analysis": (
                "## Reforma Tributaria En Profundidad\n"
                "### Resumen\n"
                "- La reciente reforma tributaria busca reducir la carga fiscal en familias de clase media y aumentar el gasto en infraestructura para estimular el crecimiento económico.\n"
                "### Aspectos Clave\n"
                "- **Reducción de Impuestos**: 10% menos en impuestos para familias de clase media, lo que aumentaría el ingreso disponible y el consumo.\n"
                "- **Inversión en Infraestructura**: Mayor gasto en proyectos para crear empleos y mejorar servicios públicos.\n"
                "### Implicaciones\n"
                "- **Corto plazo**: Alivio inmediato para familias y potencial aumento en consumo.\n"
                "- **Largo plazo**: Crecimiento económico, creación de empleos y mejor infraestructura.\n"
                "### Opiniones de Expertos\n"
                "- 'Esta reforma es un paso importante para reducir desigualdad y estimular la economía', dice la Dra. Jane Doe, economista de Harvard.\n"
                "### Conclusión\n"
                "- La reforma aborda desafíos económicos de manera balanceada, pero su éxito dependerá de su implementación."
            ),
        },
        "marketing": {
            "highlights": "# ✨ Lanzamiento de EcoLife - Destacados\n🎯 **Objetivo:** Juventud.\n📈 **Ventas:** +15%.",
            "storytelling": (
                "## EcoLife - Una Historia: Un Viaje hacia la Sostenibilidad\n"
                "### Introducción\n"
                "- En una ciudad bulliciosa, María, una joven, se sentía abrumada por el ritmo de vida y los desafíos ambientales.\n"
                "### Narrativa Principal\n"
                "- Descubrió EcoLife, una marca de vida sostenible, y sus productos cambiaron su estilo de vida.\n"
                "- A pesar del escepticismo inicial, su compromiso inspiró a otros a unirse.\n"
                "### Impacto Emocional\n"
                "- La historia muestra cómo pequeños cambios generan grandes impactos.\n"
                "### Llamado a la Acción\n"
                "- Únete a María y miles más en su viaje sostenible con EcoLife."
            ),
            "report": (
                "## EcoLife - Resultados\n"
                "### Resumen\n"
                "- La campaña buscó aumentar awareness y ventas entre jóvenes promoviendo sostenibilidad.\n"
                "### Métricas Clave\n"
                "| **Métrica**       | **Meta** | **Real** | **Variación** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Aumento Ventas   | +15%     | +18%       | +3%          |\n"
                "| Alcance Redes    | 1M       | 1.2M       | +200K        |\n"
                "### Análisis\n"
                "- La campaña superó metas gracias a engagement en redes y alianzas con influencers.\n"
                "### Recomendaciones\n"
                "- Continuar con alianzas y expandir contenido educativo.\n"
                "### Conclusión\n"
                "- La campaña estableció bases sólidas para futuras iniciativas."
            ),
        },
        "health": {
            "report": "**Tratamiento X - Reporte Clínico:** Ensayos clínicos muestran reducción del 70% en síntomas tras 8 semanas de tratamiento consistente.",
            "summary": "# 🩺 Tratamiento X - Resumen\n📈 **Efectividad:** 70%.\n| Semana | Progreso |\n| 8      | 70%     |",
            "case": "**Paciente A - Caso Clínico:** Hombre de 62 años mejora tras 2 semanas.",
        },
        "technology": {
            "changelog": "# v3.0 - Actualización\n✨ **Nuevas Funcionalidades:**\n- OCR.\n🐛 **Correcciones:**\n- Exportación.",
            "proposal": """
                    # Proyecto X - Propuesta Técnica

                    ## Introducción
                    Esta propuesta describe un sistema automatizado de integración de APIs para mejorar eficiencia en procesamiento de datos.

                    ## Objetivos
                    - Objetivo 1: Reducir entrada manual de datos en 50%.
                    - Objetivo 2: Aumentar velocidad de procesamiento en 30%.

                    ## Enfoque Técnico
                    Usará Python con Flask para APIs, Docker para contenedores y Kubernetes para orquestación.

                    ### Características Clave
                    - Característica 1: Ingestión automática de datos desde múltiples fuentes.
                    - Característica 2: Validación en tiempo real y manejo de errores.

                    ## Beneficios
                    - **Eficiencia**: Reduce esfuerzo manual y acelera procesamiento.
                    - **Escalabilidad**: Maneja volúmenes crecientes de datos.
                    - **Ahorro de Costos**: Automatiza tareas repetitivas.

                    ## Plan de Implementación
                    1. **Fase 1**: Desarrollo y pruebas de API (2 semanas).
                    2. **Fase 2**: Despliegue e integración (3 semanas).
                    3. **Fase 3**: Monitoreo y optimización (1 semana).

                    ## Riesgos y Mitigación
                    - **Riesgo 1**: Caída de API durante despliegue.
                    - **Mitigación**: Implementar actualizaciones graduales.
                    - **Riesgo 2**: Errores en validación de datos.
                    - **Mitigación**: Usar pruebas automatizadas.

                    ## Conclusión
                    Esta solución ofrece ganancias significativas en eficiencia y ahorro de costos.
            """,
            "diagram": "# Autenticación de Usuario - Flujo\n```mermaid\ngraph TD\n  A[Inicio] --> B{¿Usuario logueado?}\n  B -->|Sí| C[Mostrar Dashboard]\n  B -->|No| D[Redirigir a Login]\n  C --> E[Fin]\n  D --> E\n```\n**Anotaciones:**\n- **A**: Inicio del proceso.\n- **B**: Punto de decisión.\n- **C/D**: Rutas alternativas.\n- **E**: Fin del proceso.\n**Colores:**\n- **Verde**: Ruta exitosa (usuario logueado).\n- **Rojo**: Ruta alternativa (usuario no logueado).\n**Leyenda:**\n- **Rectángulo**: Paso del proceso.\n- **Diamante**: Punto de decisión.\n- **Círculo**: Inicio/Fin.",
        },
        "education": {
            "guide": "# 📚 [Tema] - Guía\n## [Sección]\n- **Concepto:** Explicación con ejemplos prácticos.",
            "quick_ref": "**[Tema] - Referencia Rápida:**\n- [Punto clave]: Resumen breve y accionable.",
            "timeline": "# 🎥 [Clase] - Cronología\n- **[MM:SS]** [Concepto clave o acción realizada]: [Explicación breve con resultados o acciones].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Torre Verde - Crónica\n- **[01:15]** Materiales sostenibles.",
            "report": "**Torre Verde - Reporte Técnico:** Diseño usa energía renovable.",
            "list": "# Torre Verde - Detalles\n- **Materiales:** Reciclados.\n- **Energía:** Solar.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Reporte Financiero\n- **Ingresos:** Crecimiento del 5% impulsado por avances tecnológicos y expansión de mercado.",
            "table": "## Q1 2025 - Resumen Financiero\n| **Indicador** | **Valor** |\n|---------------|-----------|\n| Ingresos      | +5%       |",
            "executive": "**Q1 2025 - Resumen Ejecutivo:** Crecimiento del 5% impulsado por tecnología y expansión estratégica, fortaleciendo perspectivas financieras.",
        },
        "tourism": {
            "chronicle": "# 🌍 Playa Azul - Crónica\n- **[01:00]** Iniciativas de ecoturismo reducen desechos.\n- **[05:00]** Desarrollo importante de hotel eco-amigable.",
            "report": "**Playa Azul - Políticas:** Promueve sostenibilidad reduciendo desechos y apoyando ecoturismo. El gobierno local busca neutralidad de carbono para 2030.",
            "list": "# Playa Azul - Iniciativas\n- **Ecología:** Reducción de plástico, más reciclaje.\n- **Atractivo Turístico:** Actividades todo el año, temporada alta de mayo a septiembre.",
        },
        "requirements": {
            "elicitation": """Requisitos de Evento Corporativo 2025 - Elicitación
                Contexto",
                - Reunión: 20/09/2025, equipo de marketing ABC, planificar evento para 500 asistentes.
                - Alcance: Evento de networking y lanzamiento de producto, dentro del presupuesto.
                Requisitos Funcionales
                - RF-01: Venue para 500 personas con stands. (Prioridad: Alta, Justificación: Crítico para el evento).
                - RF-02: Registro en línea con email. (Prioridad: Media, Justificación: Facilita logística).
                - RF-03: Keynote con orador invitado. (Prioridad: Alta, Justificación: Central para el evento).
                Requisitos No Funcionales
                - RNF-01: Cumplir normas de seguridad y accesibilidad. (Prioridad: Alta, Justificación: Obligación legal).
                - RNF-02: Planificación en 2 meses. (Prioridad: Alta, Justificación: Fecha límite fija).
                Dependencias y Restricciones
                - Dependencia: Venue requiere aprobación de presupuesto.
                - Restricción: Presupuesto de $30,000.
                Preguntas Pendientes
                - ¿Streaming del evento necesario?
                Marcas de Tiempo
                - [03:15]: 'Lugar grande para 500 personas con stands'.
                - [08:20]: 'Keynote hará el evento memorable'.
                Criterios de Priorización",
                - Alta: Crítico para el éxito o urgencia.
                - Media: Importante, pero no esencial.
                - Baja: Deseable, posponible."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Tema] - Guía\n"
                "## [Sección presente en la fuente]\n"
                "- **Concepto:** Definición o explicación condensada a partir del contenido de la fuente.\n"
                "## [Otra sección presente en la fuente]\n"
                "- **Proceso:** Secuencia o mecanismo descrito en la fuente.\n"
            ),
            "formula_reference": (
                "# 🔬 [Tema] - Referencia de Fórmulas\n"
                "## Fórmulas Principales\n"
                "| Fórmula | Significado | Variables | Unidades | Condiciones |\n"
                "|---|---|---|---|---|\n"
                "| [Fórmula presente en la fuente] | [Significado indicado en la fuente] | [Variables definidas en la fuente] | [Unidades indicadas] | [Condiciones indicadas] |\n"
            ),
            "derivation": (
                "# 🔬 [Tema] - Desarrollo\n"
                "## Punto de Partida\n"
                "- [Definición, ecuación, dato, observación o condición inicial presente en la fuente.]\n"
                "## Desarrollo\n"
                "1. [Primer paso o transformación explícitamente mostrada en la fuente.]\n"
                "2. [Segundo paso, relación o razonamiento explícitamente mostrado en la fuente.]\n"
                "## Resultado\n"
                "- **Resultado:** [Resultado o conclusión que la fuente obtiene explícitamente.]\n"
            ),
            "quick_ref": (
                "**[Tema] - Referencia Rápida:**\n"
                "- **Concepto:** [Definición presente en la fuente.]\n"
                "- **Principio/Ley/Teoría:** [Solo si aparece en la fuente.]\n"
                "- **Proceso/Relación:** [Proceso o relación descrita en la fuente.]\n"
                "- **Dato/Fórmula:** [Dato o fórmula presente en la fuente.]\n"
                "- **Condición:** [Condición o limitación indicada en la fuente.]\n"
            ),
        },
    }

    def get_prompt_base(
        self,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        spec: Any,
        style_info: Any,
    ) -> list[str]:
        return [
            f"# Prompt para {category.value.title()} - {style.value.title()}",
            f"**Objetivo:** Crear contenido en formato {output_format.value.upper()} optimizado para {category.value.title()}",
            f"**Estilo:** {style.value.title()} ({style_info['tone']})",
            f"**Requisitos esenciales:** {spec.get('needs', 'adaptación al contexto')}",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "No uses primera persona ni simules ser un estudiante que toma apuntes.",
            "No inventes preguntas, dudas, conclusiones o datos que no estén en la fuente.",
            "El resultado ES el resumen. Nunca un menú de ayuda, portada o preguntas al lector.",
            "No incluyas la etiqueta ```markdown bajo ninguna circunstancia. Si usas bloques de código, deben ser sin especificar lenguaje o con un lenguaje distinto a Markdown.",
            "Evita frases genéricas como 'El texto queda libre de repeticiones manteniéndose claro y coherente.' Céntrate en aportar feedback concreto y específico.",
            "No incluyas frases como 'Aquí está el texto revisado, eliminando redundancias y repeticiones, preservando todos los detalles y la estructura original.'",
            "A partir de ahora, responde únicamente en español sin importar el idioma de la pregunta original.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Instrucciones: Extrae los hechos distintivos de este fragmento.
            IMPORTANTE: Estás procesando SOLO UNA PARTE (chunk) de un documento mucho más grande.
            - Redacta títulos, listas y prosa en español. El inglés solo vale en código o nombres propios.
            - NO generes una Introducción global ni una Conclusión global.
            - NO reinicies jerarquías de numeración (ej. ## 1. Introducción).
            - NO generes un documento independiente.
            - Extrae de ESTE fragmento según el nivel de resumen: definiciones y hechos centrales siempre;
              ejemplos, cifras y anécdotas solo con la densidad de la instrucción de longitud.
            - El nivel de resumen controla la densidad de detalle, no si puedes omitir un tema mayor presente aquí.
            - PRIORIDAD CRÍTICA: conserva la naturaleza del lenguaje o sistema (p. ej. interpretado vs compilado,
              cliente vs servidor, estático vs dinámico) con el mismo grado de certeza que la fuente.
            - Si el texto contrapone páginas estáticas y dinámicas, define AMBAS.
            - Si afirma que algo es multiplataforma solo en teoría, conserva ese matiz (no lo conviertas en hecho absoluto).
            - Conserva tablas o listas comparativas punto por punto (no las reduzcas a "hay diferencias").
            - Conserva nombres propios de herramientas, rutas/ficheros, constantes numéricas, fórmulas y citas de código.
            - Conserva condiciones, excepciones y matices (teóricamente, puede, únicamente si, no implica…).
            - Conserva sintaxis, fórmulas y ejemplos exactamente como aparecen en este fragmento.
            - Distingue el índice o tabla de contenidos del contenido realmente desarrollado aquí.
            - Si este fragmento es un índice, descríbelo como índice (qué unidades existen) y NO extraigas esas unidades como si este fragmento las desarrollara.
            - No des por explicadas lecciones que el índice nombra si este fragmento no las desarrolla.
            - Nombra únicamente herramientas, bibliotecas, APIs, editores y URLs que aparezcan literalmente en este fragmento.
            - No uses primera persona. No inventes preguntas ni un diario de aprendizaje.
            - El resultado ES el extracto. Nunca un menú de ayuda, portada, preguntas al lector ni «¿qué necesitas?».
            - Esto es un extracto denso para una síntesis posterior, no un recapitulativo mínimo.
            - Usa el presupuesto de salida disponible para los hechos distintivos; no te detengas pronto si quedan detalles importantes.
            - Prepara el contenido para que sea útil en una síntesis global posterior.
            - No incluyas conocimiento externo ni información que no esté en el texto.
            - NO generes tabla de contenidos ni índice.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "Eres un editor experto. Tu tarea es INTEGRAR los bloques de texto "
            "proporcionados en un texto unificado.\n\n"
            "REGLAS OBLIGATORIAS:\n"
            "- CERO RELLENO (NO FLUFF): NO añadas frases de transición innecesarias, introducciones, ni conclusiones genéricas. "
            "Ve directo al grano.\n"
            "- DEDUPLICACIÓN ESTRICTA: Elimina cualquier concepto, idea o argumento repetido entre los bloques.\n"
            "- ESTRUCTURA ÚNICA: Consolida el contenido bajo una única jerarquía. Elimina cabeceras redundantes, "
            "pero CONSERVA temas de sección distintos que representen partes diferentes de la fuente.\n"
            "- FIDELIDAD ESTRICTA: Mantén fidelidad absoluta. NO inventes datos ni añadas conocimiento externo.\n"
            "- COBERTURA PRIMERO: Todo bloque fuente con contenido sustantivo debe quedar representado. "
            "El nivel de resumen controla la densidad de detalle, no si un tema principal puede desaparecer.\n"
            "- NO COMPRIMAS POR DEBAJO DEL OBJETIVO: Fusiona y elimina duplicados. "
            "Si la instrucción de longitud pide más palabras de las que tiene la entrada, "
            "conserva TODO el contenido no redundante; no acortes más y no rellenes inventando.\n"
            "- RESPETA LA INSTRUCCIÓN DE LONGITUD: Si se te proporciona una instrucción de longitud, síguela. "
            "Quedarse muy por debajo del objetivo eliminando temas principales es un error.\n"
            "- El resultado ES el resumen unificado. Nunca un asistente, menú de opciones, "
            "portada, preguntas al lector ni «¿qué necesitas?».\n"
            "- PROHIBIDO: primera persona, diarios de aprendizaje, preguntas inventadas, "
            "secciones de 'lo que aprendí' o 'puntos a aclarar'.\n"
            "- El índice no es contenido desarrollado: no resumas unidades, ejemplos o APIs "
            "que solo aparecen en la tabla de contenidos si el cuerpo del documento no las explica.\n"
            "- Nombra únicamente herramientas, bibliotecas, APIs, editores y URLs que aparezcan literalmente en los bloques.\n"
            "- No menciones 'bloque 1' ni etiquetas internas del pipeline.\n"
            "- No inventes ISBN, títulos de libro ni comparaciones Java/JVM que la fuente no haga.\n"
            "- IDIOMA: escribe TODO el resumen en español. Traduce los bloques que estén en inglés. "
            "Prohibido inglés salvo citas, código o nombres propios.\n"
            "- Un bloque que diga 'ÍNDICE ÚNICAMENTE' o liste unidades/páginas sin explicarlas "
            "es SOLO índice: DESCÁRTALO. No lo menciones en el resumen final. "
            "No listes unidades del índice. Dedica el resumen al contenido realmente desarrollado.\n"
            "- PRESERVA SIN DILUIR: nombres de herramientas, ficheros, constantes numéricas, "
            "comparaciones punto a punto, y matices de certeza (teóricamente, puede, no implica, únicamente si).\n"
            "- NO rellenes tokens: no clones secciones, no parafrasees el mismo bloque varias veces, "
            "no inventes herramientas, APIs, editores o runtimes que no estén en la fuente.\n"
            "- Si un tema ya está escrito, no lo vuelvas a escribir. "
            "- Orden de prioridad: factualidad, cobertura, completitud, coherencia, estructura y después concisión. "
            "La concisión no debe destruir la cobertura."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Estilos y tonos disponibles:**"

    def get_semantic_profile_title(self) -> str:
        return "**Perfil Semántico (Información a Preservar):**"

    def get_length_instruction_title(self) -> str:
        return "**Instrucción de Longitud:**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Expresa la tesis principal, las conclusiones esenciales y los conceptos centrales "
                "de forma muy condensada. Conserva cada pilar o tema mayor. "
                "Omite ejemplos secundarios, anécdotas, recomendaciones de lectura y matices menores."
            ),
            SummaryLevel.CONCISE: (
                "Conserva los argumentos principales, las justificaciones esenciales y la estructura temática primaria. "
                "Sé directo; recorta elaboración secundaria sin eliminar secciones importantes."
            ),
            SummaryLevel.MODERATE: (
                "Conserva argumentos, justificaciones, evidencia relevante, ejemplos representativos "
                "y taxonomías importantes."
            ),
            SummaryLevel.DETAILED: (
                "Conserva subtemas, metodología, evidencia, implicaciones, taxonomías completas "
                "y relaciones entre conceptos."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Conserva detalles incluyendo excepciones, matices, casos particulares, contexto "
                "y particularidades formalmente relevantes. "
                "En tutoriales técnicos: no omitas definiciones de naturaleza del sistema "
                "(interpretado/compilado, cliente/servidor), tablas comparativas, nombres de herramientas, "
                "ficheros de ejemplo, constantes numéricas ni condiciones de los ejemplos."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "LONGITUD / DENSIDAD: Produce un resumen visiblemente más corto que moderate. "
                "Conserva tesis, pilares y definiciones centrales. "
                "Omite ejemplos secundarios, anécdotas, recomendaciones de lectura y cualquier nota sobre el índice. "
                "Como máximo un ejemplo breve por pilar, y solo si aclara la definición. "
                "Quedarse más corto que moderate es correcto si los temas mayores sobreviven. "
                "No borres un pilar; no copies todos los ejemplos del nivel moderate. "
                "Prefiere redacción densa a enumerar cada caso."
            ),
            SummaryLevel.CONCISE: (
                "LONGITUD / DENSIDAD: Produce un resumen breve, más largo que very_concise y más corto que moderate. "
                "Prefiere compactar la redacción a eliminar secciones importantes. "
                "Un ejemplo representativo por tema mayor basta."
            ),
            SummaryLevel.MODERATE: (
                "LONGITUD / DENSIDAD: Produce un resumen de longitud media, visiblemente más largo que very_concise "
                "y más corto que very_detailed. "
                "Conserva un ejemplo representativo por concepto mayor, con cifras o nombres distintivos de la fuente. "
                "No copies todos los casos ni todas las anécdotas."
            ),
            SummaryLevel.DETAILED: (
                "LONGITUD / DENSIDAD: Produce un resumen detallado, más largo que moderate. "
                "Usa el espacio necesario para explicar subtemas, evidencia y varios ejemplos de la fuente."
            ),
            SummaryLevel.VERY_DETAILED: (
                "LONGITUD / DENSIDAD: Produce un resumen visiblemente más extenso que moderate. "
                "Conserva todos los ejemplos, cifras, nombres, excepciones y condiciones que el cuerpo de la fuente desarrolla. "
                "No comprimas esos hechos distintivos. "
                "Nunca rellenes repitiendo párrafos, clonando secciones, citando el índice "
                "ni añadiendo conocimiento externo."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "GARANTÍA DE COBERTURA (aplica en todos los niveles de resumen): "
            "Las ideas principales, conceptos esenciales, temas de secciones importantes y términos centrales DEBEN sobrevivir. "
            "El nivel de resumen solo controla la densidad de detalle y la elaboración secundaria. "
            "Nunca autoriza eliminar una sección mayor ni la tesis central del documento."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Lista de cobertura (solo si la sección está DESARROLLADA en los bloques, "
            "no si únicamente figura en un índice):**\n"
            f"{lines}\n"
            "No inventes el contenido de una cabecera que los bloques no expliquen."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Instrucción de cierre:** "
            "Cubre los hechos distintivos de ESTE fragmento con la densidad de la instrucción de longitud. "
            "Usa el presupuesto de salida disponible para esos hechos; no te detengas pronto si quedan detalles importantes. "
            "No repitas párrafos para rellenar. "
            "Termina siempre en una oración completa."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "entradas del índice"
        return (
            "ÍNDICE ÚNICAMENTE — este fragmento es una tabla de contenidos, "
            "no lecciones desarrolladas. "
            f"Lista: {listed}. "
            "No presentes estas entradas como si el documento las hubiera explicado aquí."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "Eres un experto en síntesis documental. Resume el documento completo "
            "en una sola pasada. Conserva la estructura conceptual importante "
            "(títulos/secciones relevantes), las ideas principales, definiciones, "
            "procedimientos, ejemplos y términos centrales. "
            "Emite Markdown limpio. No inventes contenido. "
            "No escribas un diario de aprendizaje ni listas de preguntas.\n"
            "El índice o tabla de contenidos NO es contenido desarrollado: "
            "menciónalo solo como índice; no presentes unidades o ejemplos del índice "
            "como si el cuerpo del documento los hubiera explicado.\n"
            "PRIORIDAD CRÍTICA: conserva naturaleza del lenguaje (interpretado/compilado), "
            "entorno de ejecución (cliente/servidor), contraste estático/dinámico, "
            "tablas comparativas, nombres de herramientas, ficheros, constantes numéricas "
            "y matices de certeza (teóricamente, puede, no implica, únicamente si).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "Eres un editor de formato. Tu única tarea es aplicar formato Markdown "
            "al texto proporcionado.\n\n"
            "NO resumas, NO acortes, NO expandas, NO reinterpretes y NO omitas información.\n"
            "NO añadas introducción, conclusión, título global ni conocimiento externo.\n"
            "Conserva el orden, las listas, las tablas, el código, las URLs y los términos técnicos.\n"
            "Si una restricción de formato choca con preservar información, preserva la información."
        )

    def get_format_strict_rules(self) -> str:
        return """
REGLAS CRÍTICAS DE FORMATO:
1. Debes preservar toda la información contenida en la entrada.
2. No omitas ninguna sección, párrafo, elemento de lista, tabla, ejemplo de código, URL, término técnico o afirmación factual.
3. No resumas, acortes, expandas, reinterpretes ni añadas información.
4. Tu tarea es solo formatear.
5. La salida debe contener toda la información de la fuente, preservando el orden original.
6. Si las restricciones de formato chocan con preservar información, preservar información tiene prioridad.
7. Nunca uses conocimiento externo.
8. Nunca completes información faltante.
9. Nunca inventes ejemplos ni explicaciones.
10. Devuelve SOLO la versión formateada de la entrada. NO añadas un título global al inicio. NO añadas una sección de "Introducción". NO añadas conclusiones. NO inventes títulos de sección.
11. Preserva la estructura de párrafos; no antepongas viñetas a cada párrafo salvo que la entrada ya lo haga.
12. Si no cabe todo el contenido, escribe lo que quepa y DETENTE en un límite de oración. Nunca emitas "[texto truncado]" ni marcadores similares.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Por favor, aplica el formato y estilo indicados en las instrucciones al siguiente texto. "
            "NO resumas ni omitas información:\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nIMPORTANTE: Este es el BLOQUE 1 de {total} en un documento multiparte. "
                "Formatea esta sección como la APERTURA del documento. "
                "PUEDES incluir una introducción si el contenido lo justifica. "
                "NO añadas una conclusión ni remates de cierre."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nIMPORTANTE: Este es el BLOQUE {idx} de {total} (ÚLTIMO BLOQUE) en un documento multiparte. "
                "Formatea esta sección como el CIERRE del documento. "
                "PUEDES incluir una conclusión o remate si el contenido lo justifica. "
                "NO añadas una nueva introducción ni reinicies la numeración."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nIMPORTANTE: Este es el BLOQUE {idx} de {total} (BLOQUE INTERMEDIO) en un documento multiparte. "
            "Formatea esto como CONTINUACIÓN del documento. "
            "NO añadas introducción, NO añadas conclusión, NO reinicies la numeración de secciones."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Procesa los siguientes bloques de texto. "
            "Redacta la salida unificada únicamente en español; traduce cualquier bloque escrito en inglés. "
            "Si un bloque es un índice, ignóralo por completo; no lo menciones.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Bloque {block_index} (Fragmentos: {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "INSTRUCCIÓN CRÍTICA: Eres un paso de reducción intermedio. "
            "Fusiona y deduplica los bloques proporcionados. "
            f"Longitud restante objetivo: aproximadamente el {pct}% de la entrada (~{target_words} palabras). "
            f"Escribe al menos {min_words} palabras. NO comprimas sustancialmente por debajo de este objetivo. "
            "No repitas párrafos para rellenar. "
            "Conserva nombres distintivos, ejemplos, eslóganes, conclusiones y hechos bibliográficos de CADA bloque. "
            "Descarta solo frases repetidas y reformulaciones verbosas. No inventes contenido.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "INSTRUCCIÓN CRÍTICA: Eres el paso FINAL de síntesis. "
            "Integra los bloques en un único resumen en español, sin duplicar secciones. "
            f"Suelo de cobertura: conserva al menos ~{min_words} palabras de contenido no redundante "
            f"(objetivo ~{target_words}) si los bloques lo contienen. "
            "Si los bloques tienen menos que el objetivo, conserva TODO el contenido distintivo; "
            "no comprimas más y no inventes relleno para llegar al recuento. "
            "Si los bloques tienen más, fusiona duplicados pero no borres temas, cifras, nombres ni ejemplos. "
            "Un índice no es contenido desarrollado: omite esos bloques y no menciones que existe un índice. "
            "No presentes unidades, ejemplos o APIs que solo aparezcan en la tabla de contenidos. "
            "Nombra únicamente herramientas y APIs que estén en los bloques.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        return (
            "CRÍTICO: Escribe el resumen en sí. Nunca un menú de ayuda, saludo de asistente, "
            "portada de libro ni preguntas al lector.\n\n"
        )
