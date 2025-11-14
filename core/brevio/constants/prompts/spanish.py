from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


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
                "Resumir de manera concisa, eliminando redundancias",
                "Preservar el título original si está presente, sin modificaciones, usando su redacción y formato exactos (ej: # Título, ## Subtítulo)",
                "Adaptarse completamente al tono, intención y estructura implícita del contenido fuente",
                "No introducir títulos, subtítulos o encabezados a menos que estén explícitamente en el texto original",
                "Mantener ejemplos o conceptos clave en su formato original (ej: listas, código, cursivas)",
                "Evitar interpretaciones subjetivas o modificaciones innecesarias",
                "Producir un único bloque continuo de texto a menos que el contenido original especifique lo contrario",
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
                "Mantener información concisa pero exhaustiva, enfocada en aplicaciones prácticas.",
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
            "Evita frases genéricas como 'El texto ahora está libre de repeticiones manteniendo la claridad y coherencia.' Concéntrate en dar comentarios concretos y específicos.",
            "No incluyas frases como 'Aquí tienes el texto revisado, eliminando redundancias y repeticiones, pero conservando todos los detalles y la estructura original.'",
            "No incluyas la etiqueta ```markdown bajo ninguna circunstancia. Si usas bloques de código, deben ser sin especificar lenguaje o con un lenguaje distinto a Markdown.",
            f"A partir de ahora, responde únicamente en español sin importar el idioma de la pregunta original.",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- Resume el documento de manera completa, destacando los temas principales, puntos clave y el propósito general en aproximadamente {word_limit} palabras."

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            Contexto del texto anterior: {previous_context}\n
            Instrucciones: Proporciona un resumen detallado del siguiente texto, integrando la información nueva de manera coherente con el contexto anterior. 
            Incluye ejemplos, explicaciones y cualquier detalle que facilite el estudio del tema. 
            Organiza el resumen en secciones o puntos clave para una mejor comprensión."""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""Eres un editor experto en mejorar textos eliminando redundancias.
            Revisa el siguiente resumen y elimina únicamente repeticiones o información duplicada, 
            como frases, ideas o contenidos repetidos.
            No simplifiques, reduzcas ni resumas el contenido en ningún momento; mantén todos los detalles, datos y elementos importantes tal cual.
            Asegúrate de que el texto final sea claro, coherente y bien estructurado, sin alterar su estructura ni su significado original."""
        return prompt
