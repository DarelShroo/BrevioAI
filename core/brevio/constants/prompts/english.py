from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class EnglishPrompts:
    INSTRUCTIONS_TITLE: str = "**Instructions:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Specific Language:** English"
    SPECIFIC_LANGUAGE: str = "From now on, all responses must be in English only."
    EXAMPLE_TITLE: str = "**Example**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["Direct summary without additional headings"]},
            "styles": {
                "default": {
                    "tone": "Neutral, adapted to context",
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
                "Summarize the source content: themes, definitions, facts, procedures and important examples",
                "Write in third person. First person is forbidden (I learned, I need to clarify, it would help me)",
                "Do not invent questions, exercises, doubts or 'points to clarify' / 'what I learned' sections",
                "Do not turn the document into a learning diary or student homework",
                "Preserve the original title if present, without modification, using its exact wording and format (e.g., # Title, ## Subtitle)",
                "Use headings only if the original document has real equivalent sections",
                "Maintain key examples or concepts in their original format (e.g., lists, code, italics)",
                "Do not add external knowledge or claims the source does not support",
            ],
            "needs": "Simplicity and fidelity to the original content",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Event] Live",
                    "- **[MM:SS]** Statement or key fact",
                    "- **[MM:SS]** Description of key moment or development",
                    "- **[MM:SS]** Reaction or analysis of the event",
                ],
                "news_wire": [
                    "[Date] - [Location] - Brief and direct summary",
                    "### Key Details",
                    "- [Key fact 1]",
                    "- [Key fact 2]",
                    "### Context",
                    "- [Background information]",
                    "### Statistics (if applicable)",
                    "- [Statistic 1]",
                    "- [Statistic 2]",
                    "### Impact",
                    "- [Short-term impact]",
                    "- [Long-term implications]",
                ],
                "analysis": [
                    "## [Topic] In Depth",
                    "### Overview",
                    "- [Brief summary of the topic]",
                    "### Key Aspects",
                    "- [Aspect 1]: [Detailed analysis]",
                    "- [Aspect 2]: [Detailed analysis]",
                    "### Implications",
                    "- [Short-term implications]",
                    "- [Long-term implications]",
                    "### Expert Opinions",
                    "- [Quote or perspective from an expert]",
                    "### Conclusion",
                    "- [Summary of key findings and future outlook]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrative, urgent",
                    "elements": ["timeline", "key moments", "reactions"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Direct, informative",
                    "elements": ["key details", "context", "statistics", "impact"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "Reflective, contextual",
                    "elements": [
                        "overview",
                        "key aspects",
                        "implications",
                        "expert opinions",
                        "conclusion",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Include precise timestamps for chronicle",
                "Cite sources if applicable",
                "Avoid opinions in news wire",
                "Use bullet points for key details in news wire",
                "Include at least one statistic or data point in news wire",
                "Highlight both short-term and long-term impacts in news wire",
                "For chronicle, focus on key moments and reactions in real-time",
                "For analysis, provide a detailed exploration of the topic, including causes, effects, and expert perspectives",
            ],
            "needs": ["Speed in news wire, detail in chronicle, context in analysis"],
        },
        "marketing": {
            "structures": {
                "highlights": ["# ✨ [Campaign] - Highlights", "🎯 **Key:** Value"],
                "storytelling": [
                    "## [Brand] - A Story: [Title]",
                    "### Introduction",
                    "- [Emotional hook or setting]",
                    "### Main Narrative",
                    "- [Key event or turning point]",
                    "- [Challenges or conflicts]",
                    "- [Resolution or outcome]",
                    "### Emotional Impact",
                    "- [How the story makes the audience feel]",
                    "### Call to Action",
                    "- [Encouragement to engage with the brand or product]",
                ],
                "report": [
                    "## [Campaign] - Results",
                    "### Overview",
                    "- [Brief summary of the campaign and its objectives]",
                    "### Key Metrics",
                    "| **Metric** | **Goal** | **Actual** | **Variance** |",
                    "|------------|----------|------------|--------------|",
                    "| [Metric 1] | [Goal 1] | [Actual 1] | [Variance 1] |",
                    "| [Metric 2] | [Goal 2] | [Actual 2] | [Variance 2] |",
                    "### Analysis",
                    "- [Detailed analysis of the results, including successes and challenges]",
                    "### Recommendations",
                    "- [Actionable recommendations based on the data]",
                    "### Conclusion",
                    "- [Summary of key findings and next steps]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Engaging, visual",
                    "elements": ["emojis", "bullet_points"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Emotional, immersive",
                    "elements": ["narrative", "emotional_hook", "call_to_action"],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analytical, clear",
                    "elements": ["table", "analysis", "recommendations"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Use engaging language for highlights and storytelling",
                "Include KPIs in report",
                "Avoid excessive technical terms",
                "For storytelling, focus on emotional connection and narrative flow",
            ],
            "needs": "Visual impact, emotional connection, actionable data",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Study/Treatment] - Clinical Report:**",
                    "Concise and data-driven technical paragraph focused on results and efficacy",
                ],
                "summary": [
                    "# 🩺 [Topic] - Summary",
                    "📈 **Indicator:** Result",
                    "| Week | Progress |",
                ],
                "case": ["**[Patient] - Clinical Case:**", "Detailed narrative"],
            },
            "styles": {
                "report": {
                    "tone": "Formal, precise, and evidence-based",
                    "elements": ["quantitative_data", "clinical_results"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visual, accessible",
                    "elements": ["bullet_points", "table"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "Narrative, clinical",
                    "elements": ["narrative"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "Always include quantitative and measurable data when available",
                "Maintain scientific rigor and avoid subjective language",
                "Adjust language complexity based on audience (technical for doctors, simplified for patients)",
                "Ensure clarity, accuracy, and accessibility of medical information",
            ],
            "needs": {
                "doctors": "Clear and precise clinical data for informed decision-making",
                "patients": "Accessible and understandable explanations of conditions and treatments",
                "researchers": "Robust and data-driven information for analysis",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Version] - Update",
                    "✨ **New Features:**",
                    "- Feature",
                    "🐛 **Fixes:**",
                    "- Fix",
                ],
                "proposal": [
                    "# [Project] - Technical Proposal",
                    "## Introduction",
                    "Briefly describe the project, its goals, and the problem it aims to solve.",
                    "## Objectives",
                    "- Objective 1: Describe the first goal of the project.",
                    "- Objective 2: Describe the second goal of the project.",
                    "## Technical Approach",
                    "Explain the technical solution, including tools, frameworks, and methodologies to be used.",
                    "### Key Features",
                    "- Feature 1: Describe the first key feature.",
                    "- Feature 2: Describe the second key feature.",
                    "## Benefits",
                    "Highlight the advantages of the proposed solution, such as efficiency, scalability, or cost savings.",
                    "## Implementation Plan",
                    "Provide a high-level timeline or steps for implementing the solution.",
                    "## Risks and Mitigation",
                    "Identify potential risks and propose strategies to mitigate them.",
                    "## Conclusion",
                    "Summarize the proposal and reiterate its value.",
                ],
                "diagram": [
                    "# [Process] - Flow",
                    "```mermaid",
                    "graph TD",
                    "  A[Start] --> B{Decision?}",
                    "  B -->|Yes| C[Process 1]",
                    "  B -->|No| D[Process 2]",
                    "  C --> E[End]",
                    "  D --> E",
                    "```",
                    "**Annotations:**",
                    "- **A**: Start of the process.",
                    "- **B**: Decision point.",
                    "- **C/D**: Alternative paths.",
                    "- **E**: End of the process.",
                    "**Colors:**",
                    "- **Green**: Successful path (e.g., user logged in).",
                    "- **Red**: Alternative path (e.g., user not logged in).",
                    "**Legend:**",
                    "- **Rectangle**: Process step.",
                    "- **Diamond**: Decision point.",
                    "- **Circle**: Start/End point.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Technical, concise",
                    "elements": ["bullet_points"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Persuasive, clear, and structured",
                    "elements": ["headings", "bullet_points", "tables"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visual, descriptive, and modular",
                    "elements": ["mermaid", "colors", "annotations", "legend"],
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
                "Use specific technical terminology relevant to the project.",
                "Highlight the benefits of the proposed solution to persuade stakeholders.",
                "Include a clear and structured implementation plan.",
                "Address potential risks and propose mitigation strategies.",
                "Use bullet points and headings to improve readability.",
                "Provide concrete examples or case studies to support the proposal.",
                "Ensure the proposal is modular and can be easily updated.",
                "Include a conclusion that summarizes the value of the proposal.",
            ],
            "needs": "Persuasion for stakeholders, clarity in technical approach, structured documentation, and actionable insights",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Topic] - Guide",
                    "## [Section]",
                    "- **Concept:** Explanation with practical examples and applications.",
                ],
                "quick_ref": [
                    "**[Topic] - Quick Reference:**",
                    "- [Key point]: Brief, actionable summary with clear practical context.",
                ],
                "timeline": [
                    "# 🎥 [Class] - Timeline",
                    "- **[MM:SS]** [Key concept or action performed]: [Brief, clear explanation with results or actions, highlighting real-world application].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educational, structured, with examples for better clarity and understanding",
                    "elements": [
                        "subsections",
                        "bullet_points",
                        "examples",
                        "real-world applications",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Concise, practical, designed for quick learning and application",
                    "elements": ["bullet_points", "clear summaries"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Chronological, action-focused, clear with emphasis on real-world applications",
                    "elements": [
                        "timeline",
                        "step-by-step actions",
                        "visual cues",
                        "real-world context",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Provide clear, actionable explanations with examples for better understanding.",
                "Keep information concise yet comprehensive, focusing on practical applications.",
                "Ensure alignment with learning objectives and context to aid retention.",
                "Emphasize clarity and usability, especially for real-world use cases.",
            ],
            "needs": "Facilitate study ease, quick reference, and video tracking with practical insights.",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Project] - Chronicle",
                    "- **[MM:SS]** Highlighted element",
                ],
                "report": [
                    "**[Project] - Technical Report:**",
                    "Paragraph with key details",
                ],
                "list": ["# [Project] - Details", "- **Aspect:** Description"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrative, visual",
                    "elements": ["timeline"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Technical, detailed",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptive, organized",
                    "elements": ["bullet_points"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Highlight innovation or sustainability",
                "Include technical data if applicable",
                "Be visually appealing",
            ],
            "needs": "Technical documentation, attractive presentation, video tracking",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Period] - Financial Report",
                    "- **Indicator**: [Value]",
                ],
                "table": [
                    "## [Period] - Financial Summary",
                    "| **Indicator** | **Value** |",
                ],
                "executive": [
                    "**[Period] - Executive Summary:**",
                    "Brief and impactful paragraph highlighting key insights.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analytical, formal",
                    "elements": ["bullet_points"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "Visual, concise",
                    "elements": ["table"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Direct, executive",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Ensure clarity and conciseness in presenting key figures.",
                "Avoid ambiguity in the presentation of data.",
                "Support decision-making by offering actionable insights.",
                "Table titles must be formatted without any extra spaces before or after the double asterisks.",
            ],
            "needs": "Actionable data, clear visual synthesis, and executive summaries focused on impact.",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Destination] - Chronicle",
                    "- **[MM:SS]** Initiative",
                    "- **[MM:SS]** Major Milestone",
                ],
                "report": [
                    "**[Destination] - Policies:**",
                    "Formal paragraph with emphasis on the destination's goals and impact on tourism",
                ],
                "list": [
                    "# [Destination] - Initiatives",
                    "- **Area:** Detail (consider adding local culture or attractions)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrative, engaging, immersive",
                    "elements": ["timeline", "storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formal, informative, objective",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptive, clear, informative",
                    "elements": ["bullet_points", "concise facts"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Highlight sustainability, cultural significance, and the appeal to tourists",
                "Include practical travel information (e.g., best time to visit, local attractions, essential contact info)",
                "Focus on clear, concise, and accurate descriptions of policies and initiatives",
                "Avoid exaggerations, remain realistic and informative",
            ],
            "needs": "Engaging promotion with informative highlights, clear presentation of policies, and practical tourist-focused details",
        },
        "requirements": {
            "structures": {
                "elicitation": [
                    "Requirements for [Project/Name] - Elicitation",
                    "Context",
                    "- Meeting: [Date, participants, objective].",
                    "- Scope: [Purpose or expected outcome].",
                    "Functional Requirements",
                    "- FR-[ID]: [Clear description]. (Priority: [High/Medium/Low], Justification: [Brief reason]).",
                    "Non-Functional Requirements",
                    "- NFR-[ID]: [Description, e.g. quality, timing]. (Priority: [High/Medium/Low], Justification: [Reason]).",
                    "Dependencies and Constraints",
                    "- Dependency: [Relationship to other requirements/resources].",
                    "- Constraint: [Limitations, e.g. budget, time].",
                    "Open Questions",
                    "- [Question to clarify].",
                    "Timestamps (If Applicable)",
                    "- [MM:SS]: [Brief quote from the source].",
                    "Prioritization Criteria",
                    "- High: Critical for success or urgency.",
                    "- Medium: Important, but not essential.",
                    "- Low: Desirable, deferrable.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Clear, objective, adaptable",
                    "elements": ["bullet_points", "IDs", "priorities"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Extract requirements directly, without interpretations.",
                "Use IDs (FR-01, NFR-01) for traceability.",
                "Prioritize with justification (impact/urgency).",
                "Use clear language focused on 'what' is needed.",
                "List ambiguities under 'Open Questions'.",
                "Timestamps only for key requirements.",
            ],
            "needs": "Clear capture of requirements for any project, facilitating planning and communication.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Topic] - Guide",
                    "## [Section]",
                    "- **Concept:** Definition, principle, relationship, process, mechanism, classification or relevant evidence.",
                ],
                "formula_reference": [
                    "# 🔬 [Topic] - Formula Reference",
                    "## Main Formulas",
                    "| Formula | Meaning | Variables | Units | Conditions |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Topic] - Derivation",
                    "## Starting Point",
                    "- [Definition, principle, equation, observation, data or initial condition present in the source.]",
                    "## Development",
                    "1. [First step or reasoning present in the source.]",
                    "2. [Transformation, relationship, procedure or reasoning present in the source.]",
                    "## Result",
                    "- **Result:** [Result or conclusion obtained in the source.]",
                ],
                "quick_ref": [
                    "**[Topic] - Quick Reference:**",
                    "- **Concept:** Brief definition.",
                    "- **Principle/Law/Theory:** Fundamental relationship.",
                    "- **Process/Relationship:** Essential description.",
                    "- **Data/Formula:** Relevant quantitative information.",
                    "- **Condition:** Applicability or limitation.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educational, rigorous and structured",
                    "elements": [
                        "concepts",
                        "principles",
                        "laws",
                        "theories",
                        "models",
                        "processes",
                        "mechanisms",
                        "structures",
                        "relationships",
                        "data",
                        "formulas",
                        "examples",
                        "evidence",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Technical, compact and precise, oriented to correct application and reference",
                    "elements": [
                        "formulas",
                        "variables",
                        "units",
                        "relationships",
                        "conditions",
                        "tables",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formal, logical and rigorous, preserving the reasoning actually supported by the source",
                    "elements": [
                        "equations",
                        "procedures",
                        "deductions",
                        "sequences",
                        "reasoning",
                        "assumptions",
                        "conditions",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Concise, technical and practical, designed for quick review without losing scientific precision",
                    "elements": [
                        "key concepts",
                        "principles",
                        "laws",
                        "theories",
                        "processes",
                        "formulas",
                        "data",
                        "conditions",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
            },
            "rules": [
                "Use exclusively the information present in the source.",
                "Do not introduce external knowledge even if it is scientifically correct, known, obvious or useful to complete the explanation.",
                "Do not invent, complete, correct or reinterpret content that is not supported by the source.",
                "The structures are only an organizational guide and do not obligate creating content to complete sections.",
                "Do not include a section when the source does not contain sufficient information to justify it.",
                "Preserve relevant definitions, principles, laws, theories, hypotheses, models, processes, mechanisms, classifications, relationships, data, formulas, variables, units, evidence and conditions present in the source.",
                "Maintain the original meaning of scientific terms, symbols, variables, magnitudes, relationships, processes and mechanisms.",
                "Do not transform a hypothesis, model, observation, correlation, association or experimental result into a fact, law or causal relationship not established by the source.",
                "Do not generalize results, mechanisms or conclusions beyond the conditions, population, system, scale or context indicated in the source.",
                "Preserve exceptions, limits, assumptions, restrictions, uncertainties and conditions of validity when they affect interpretation.",
                "When quantitative data exists, conserve values, units, relationships, orders of magnitude and relevant precision.",
                "When formulas or mathematical relationships exist, preserve signs, exponents, indices, operators, variables, units, approximations and conditions of validity.",
                "Do not perform conversions, calculations, algebraic transformations or additional quantitative inferences that are not present or unequivocally supported by the source.",
                "When a derivation, demonstration, procedure, experiment or sequential reasoning exists, conserve only the essential steps actually supported by the source.",
                "Do not add intermediate steps, mechanisms, causes or explanations that the source does not present or does not allow to establish unequivocally.",
                "Conserve temporal, causal, functional, structural and hierarchical relationships when they are relevant to correctly understand the content.",
                "Do not confuse correlation with causality nor association with mechanism.",
                "Do not eliminate information whose absence could change the meaning, interpretation, result or scope of application of the content.",
                "Eliminate redundancies and repetitive formulations without eliminating necessary scientific information.",
                "Reduce the explanation, not the meaning.",
                "In case of conflict, prioritize in this order: fidelity to the source, scientific accuracy, preservation of meaning and conditions, clarity, structure and finally conciseness.",
                "The objective is to compactly and accurately represent the knowledge contained in the source, not to provide a general explanation of the topic based on external knowledge.",
            ],
            "needs": (
                "Maximum scientific fidelity and precision, preserving concepts, "
                "processes, mechanisms, relationships, data, formulas, evidence, "
                "conditions, limits and essential reasoning present in the source, "
                "without introducing external knowledge or completing absent information."
            ),
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "The content describes economic measures announced on March 08, 2025, including tax reductions and credit lines."
        },
        "journalism": {
            "chronicle": (
                "# Apple Event Live\n"
                "- **[00:03:00]** Tim Cook takes the stage to introduce Apple Intelligence, a new AI system integrated into Apple devices.\n"
                "- **[00:05:11]** Presentation of the Apple Watch Series 10, highlighting its larger display and thinner design.\n"
                "- **[00:07:03]** Demonstration of the new OLED display, 40% brighter at oblique angles.\n"
                "- **[00:09:06]** Announcement of the Series 10 being 10% thinner than the Series 9, with a thickness of only 9.7 mm.\n"
                "- **[00:10:19]** Introduction of fast charging: 80% battery in 30 minutes.\n"
                "- **[00:11:03]** Reveal of the polished titanium finish, 20% lighter than stainless steel.\n"
                "- **[00:12:00]** Emphasis on sustainability: 95% recycled titanium and 100% renewable energy in manufacturing.\n"
                "- **[00:13:50]** New health features: Sleep apnea detection and body temperature monitoring for ovulation tracking.\n"
                "- **[00:15:19]** Discussion of the importance of sleep apnea detection, with 80% of cases going undiagnosed globally."
            ),
            "news_wire": (
                "[March 08, 2025] - Capital - President announces economic measures.\n"
                "### Key Details\n"
                "- Tax reduction for middle-class families.\n"
                "- Increased spending on infrastructure projects.\n"
                "### Context\n"
                "- The measures aim to boost economic growth amid rising inflation.\n"
                "### Statistics\n"
                "- GDP growth forecast: 2.5% for 2025.\n"
                "- Unemployment rate: 5.8% (down from 6.3% last year).\n"
                "### Impact\n"
                "- Short-term: Immediate relief for middle-class families.\n"
                "- Long-term: Expected to stimulate economic growth and create jobs."
            ),
            "analysis": (
                "## Tax Reform In Depth\n"
                "### Overview\n"
                "- The recent tax reform aims to reduce the tax burden on middle-class families and increase spending on infrastructure projects to stimulate economic growth.\n"
                "### Key Aspects\n"
                "- **Tax Reduction**: A 10% reduction in taxes for middle-class families, expected to increase disposable income and boost consumer spending.\n"
                "- **Infrastructure Investment**: Increased spending on infrastructure projects, aimed at creating jobs and improving public services.\n"
                "### Implications\n"
                "- **Short-term**: Immediate relief for middle-class families, with potential increases in consumer spending and economic activity.\n"
                "- **Long-term**: Expected to stimulate economic growth, create jobs, and improve public infrastructure, leading to a more robust economy.\n"
                "### Expert Opinions\n"
                "- 'This tax reform is a significant step towards reducing income inequality and stimulating economic growth,' says Dr. Jane Doe, an economist at Harvard University.\n"
                "### Conclusion\n"
                "- The tax reform represents a balanced approach to addressing economic challenges, with potential benefits for both individuals and the broader economy. However, its long-term success will depend on effective implementation and monitoring."
            ),
        },
        "marketing": {
            "highlights": "# ✨ EcoLife Launch - Highlights\n🎯 **Target:** Youth.\n📈 **Sales:** +15%.",
            "storytelling": (
                "## EcoLife - A Story: A Journey to Sustainability\n"
                "### Introduction\n"
                "- In a bustling city, a young woman named Maria felt overwhelmed by the fast-paced life and the environmental challenges around her.\n"
                "### Main Narrative\n"
                "- One day, Maria discovered EcoLife, a brand dedicated to sustainable living. She started using their eco-friendly products and noticed a significant change in her lifestyle.\n"
                "- Despite initial skepticism from her friends, Maria's commitment to sustainability inspired them to join her journey.\n"
                "### Emotional Impact\n"
                "- Maria's story is a testament to how small changes can lead to a big impact, both personally and environmentally.\n"
                "### Call to Action\n"
                "- Join Maria and thousands of others in making a difference. Start your sustainable journey with EcoLife today!"
            ),
            "report": (
                "## EcoLife - Results\n"
                "### Overview\n"
                "- The EcoLife campaign aimed to increase brand awareness and sales among young adults by promoting sustainable living.\n"
                "### Key Metrics\n"
                "| **Metric**       | **Goal** | **Actual** | **Variance** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Sales Increase   | +15%     | +18%       | +3%          |\n"
                "| Social Media Reach | 1M      | 1.2M       | +200K        |\n"
                "### Analysis\n"
                "- The campaign exceeded its sales target by 3%, driven by strong social media engagement and influencer partnerships.\n"
                "- Social media reach surpassed expectations, indicating effective content strategy and audience targeting.\n"
                "### Recommendations\n"
                "- Continue leveraging influencer partnerships to maintain momentum.\n"
                "- Expand content strategy to include more educational posts about sustainability.\n"
                "### Conclusion\n"
                "- The EcoLife campaign successfully increased brand awareness and sales, setting a strong foundation for future initiatives."
            ),
        },
        "health": {
            "report": "**Treatment X - Clinical Report:** Clinical trials show a 70% reduction in symptoms after 8 weeks of consistent treatment.",
            "summary": "# 🩺 Treatment X - Summary\n📈 **Efectiveness:** 70%.\n| Week | Progress |\n| 8    | 70%     |",
            "case": "**Patient A - Clinical Case:** A 62-year-old man improves after 2 weeks.",
        },
        "technology": {
            "changelog": "# v3.0 - Update\n✨ **New Features:**\n- OCR.\n🐛 **Fixes:**\n- Export.",
            "proposal": """
                    # Project X - Technical Proposal

                    ## Introduction
                    This proposal outlines the technical approach for implementing an automated API integration system to improve data processing efficiency.

                    ## Objectives
                    - Objective 1: Reduce manual data entry by 50%.
                    - Objective 2: Increase data processing speed by 30%.

                    ## Technical Approach
                    The solution will use Python with Flask for API development, Docker for containerization, and Kubernetes for orchestration.

                    ### Key Features
                    - Feature 1: Automated data ingestion from multiple sources.
                    - Feature 2: Real-time data validation and error handling.

                    ## Benefits
                    - **Efficiency**: Reduces manual effort and speeds up data processing.
                    - **Scalability**: Easily scales to handle increasing data volumes.
                    - **Cost Savings**: Reduces operational costs by automating repetitive tasks.

                    ## Implementation Plan
                    1. **Phase 1**: API development and testing (2 weeks).
                    2. **Phase 2**: Deployment and integration with existing systems (3 weeks).
                    3. **Phase 3**: Monitoring and optimization (1 week).

                    ## Risks and Mitigation
                    - **Risk 1**: API downtime during deployment.
                    - **Mitigation**: Implement a rolling update strategy to minimize downtime.
                    - **Risk 2**: Data validation errors.
                    - **Mitigation**: Use automated testing to catch errors early.

                    ## Conclusion
                    This proposal presents a robust solution for automating data processing, offering significant efficiency gains and cost savings.
            """,
            "diagram": "# User Authentication - Flow\n```mermaid\ngraph TD\n  A[Start] --> B{Is user logged in?}\n  B -->|Yes| C[Show Dashboard]\n  B -->|No| D[Redirect to Login]\n  C --> E[End]\n  D --> E\n```\n**Annotations:**\n- **A**: Start of the process.\n- **B**: Decision point.\n- **C/D**: Alternative paths.\n- **E**: End of the process.\n**Colors:**\n- **Green**: Successful path (user logged in).\n- **Red**: Alternative path (user not logged in).\n**Legend:**\n- **Rectangle**: Process step.\n- **Diamond**: Decision point.\n- **Circle**: Start/End point.",
        },
        "education": {
            "guide": "# 📚 [Topic] - Guide\n## [Section]\n- **Concept:** Explanation with practical examples and usage.",
            "quick_ref": "**[Topic] - Quick Reference:**\n- [Key point]: Short, actionable summary.",
            "timeline": "# 🎥 [Class] - Timeline\n- **[MM:SS]** [Key concept or action performed]: [Brief, clear explanation with results or actions performed].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Green Tower - Chronicle\n- **[01:15]** Sustainable materials.",
            "report": "**Green Tower - Technical Report:** Design uses renewable energy.",
            "list": "# Green Tower - Details\n- **Materials:** Recycled.\n- **Energy:** Solar.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Financial Report\n- **Revenue:** 5% growth driven by technological advancements and market expansion.",
            "table": "## Q1 2025 - Financial Summary\n| **Indicator** | **Value** |\n|---------------|-----------|\n| Revenue       | +5%       |",
            "executive": "**Q1 2025 - Executive Summary:** 5% growth driven by technology advancements and strategic market expansion, strengthening financial outlook.",
        },
        "tourism": {
            "chronicle": "# 🌍 Blue Beach - Chronicle\n- **[01:00]** Eco-tourism initiatives help reduce waste.\n- **[05:00]** Major eco-friendly hotel development.",
            "report": "**Blue Beach - Policies:** Promotes sustainability by reducing waste and supporting eco-tourism efforts. The local government aims for carbon neutrality by 2030, focusing on renewable energy and waste reduction.",
            "list": "# Blue Beach - Initiatives\n- **Ecology:** Reduced plastic usage, increased recycling initiatives.\n- **Tourism Appeal:** Offers year-round activities, with a peak season from May to September.",
        },
        "requirements": {
            "elicitation": """Requirements for Corporate Event 2025 - Elicitation
                Context
                - Meeting: 20/09/2025, ABC marketing team, plan event for 500 attendees.
                - Scope: Networking and product launch event, within budget.
                Functional Requirements
                - FR-01: Venue for 500 people with booths. (Priority: High, Justification: Critical for the event).
                - FR-02: Online registration with email. (Priority: Medium, Justification: Facilitates logistics).
                - FR-03: Keynote with guest speaker. (Priority: High, Justification: Central to the event).
                Non-Functional Requirements
                - NFR-01: Comply with safety and accessibility standards. (Priority: High, Justification: Legal obligation).
                - NFR-02: Planning within 2 months. (Priority: High, Justification: Fixed deadline).
                Dependencies and Constraints
                - Dependency: Venue requires budget approval.
                - Constraint: Budget of $30,000.
                Open Questions
                - Is event streaming required?
                Timestamps
                - [03:15]: 'Large venue for 500 people with booths'.
                - [08:20]: 'Keynote will make the event memorable'.
                Prioritization Criteria
                - High: Critical for success or urgency.
                - Medium: Important, but not essential.
                - Low: Desirable, deferrable."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Topic] - Guide\n"
                "## [Section present in the source]\n"
                "- **Concept:** Definition or explanation condensed from the source content.\n"
                "## [Another section present in the source]\n"
                "- **Process:** Sequence or mechanism described in the source.\n"
            ),
            "formula_reference": (
                "# 🔬 [Topic] - Formula Reference\n"
                "## Main Formulas\n"
                "| Formula | Meaning | Variables | Units | Conditions |\n"
                "|---|---|---|---|---|\n"
                "| [Formula present in the source] | [Meaning indicated in the source] | [Variables defined in the source] | [Indicated units] | [Indicated conditions] |\n"
            ),
            "derivation": (
                "# 🔬 [Topic] - Derivation\n"
                "## Starting Point\n"
                "- [Definition, equation, data, observation or initial condition present in the source.]\n"
                "## Development\n"
                "1. [First step or transformation explicitly shown in the source.]\n"
                "2. [Second step, relationship or reasoning explicitly shown in the source.]\n"
                "## Result\n"
                "- **Result:** [Result or conclusion that the source explicitly obtains.]\n"
            ),
            "quick_ref": (
                "**[Topic] - Quick Reference:**\n"
                "- **Concept:** [Definition present in the source.]\n"
                "- **Principle/Law/Theory:** [Only if it appears in the source.]\n"
                "- **Process/Relationship:** [Process or relationship described in the source.]\n"
                "- **Data/Formula:** [Data or formula present in the source.]\n"
                "- **Condition:** [Condition or limitation indicated in the source.]\n"
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
            f"# Prompt for {category.value.title()} - {style.value.title()}",
            f"**Objective:** Create content in {output_format.value.upper()} format optimized for {category.value.title()}",
            f"**Style:** {style.value.title()} ({style_info['tone']})",
            f"**Essential Requirements:** {spec.get('needs', 'adaptation to context')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "Do not use first person or pretend to be a student taking notes.",
            "Do not invent questions, doubts, conclusions or data not in the source.",
            "The output IS the summary. Never a help menu, cover, or questions to the reader.",
            "Never include the ```markdown tag under any circumstance. If you use code blocks, they must be unspecified or in a language other than Markdown.",
            "Avoid generic phrases like 'The text is now free of repetitions while remaining clear and coherent.' Focus on providing concrete and specific feedback.",
            "Do not include phrases like 'Here is the revised text, removing redundancies and repetitions, while preserving all details and original structure.'",
            "From now on, respond only in English, regardless of the original question's language.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Instructions: Extract the distinctive facts from this fragment.
            IMPORTANT: You are processing ONLY ONE PART (chunk) of a much larger document.
            - Write headings, lists and prose in English. Other languages only in code or proper names.
            - DO NOT generate a global Introduction or a global Conclusion.
            - DO NOT restart numbering hierarchies (e.g. ## 1. Introduction).
            - DO NOT generate a standalone document.
            - Extract from THIS fragment according to the summary level: definitions and central facts always;
              examples, figures and anecdotes only at the density of the length instruction.
            - Summary level controls detail density, not whether a major topic present here may be omitted.
            - CRITICAL PRIORITY: preserve the nature of the language or system (e.g. interpreted vs compiled,
              client vs server, static vs dynamic) with the same degree of certainty as the source.
            - If the text contrasts static and dynamic pages, define BOTH.
            - If it claims something is multiplatform only in theory, keep that hedge (do not turn it into an absolute fact).
            - Keep comparative tables or lists point by point (do not reduce them to "there are differences").
            - Preserve names of tools, file paths, numeric constants, formulas and code quotes.
            - Preserve conditions, exceptions and hedges (theoretically, may, only if, does not imply…).
            - Preserve syntax, formulas and examples exactly as they appear in this fragment.
            - Distinguish a table of contents or index from content actually developed here.
            - If this fragment is an index, describe it as an index (which units exist) and DO NOT extract those units as if this fragment developed them.
            - Do not treat index-named lessons as explained if this fragment does not develop them.
            - Name only tools, libraries, APIs, editors and URLs that appear literally in this fragment.
            - Do not use first person. Do not invent questions or a learning diary.
            - The output IS the extract. Never a help menu, book cover, questions to the reader, or "what do you need?".
            - This is a dense extract for later synthesis, not a tiny standalone recap.
            - Use the available output budget for distinctive facts; do not stop early if important details remain.
            - Prepare the content so it is useful for a later global synthesis.
            - DO NOT include any external knowledge or information not present in the text.
            - DO NOT generate a table of contents or index.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "You are an expert editor. Your task is to INTEGRATE the provided text blocks "
            "into a unified text.\n\n"
            "MANDATORY RULES:\n"
            "- ZERO FLUFF: DO NOT add unnecessary transition sentences, generic introductions, or conclusions. "
            "Get straight to the point.\n"
            "- STRICT DEDUPLICATION: Eliminate any concept, idea, or argument repeated across blocks.\n"
            "- SINGLE STRUCTURE: Consolidate the content under a single hierarchy. Remove redundant headers, "
            "but KEEP distinct section topics that represent different parts of the source.\n"
            "- STRICT FIDELITY: Maintain absolute fidelity. DO NOT invent facts or add external knowledge.\n"
            "- COVERAGE FIRST: Every source block that carries substantive content must be represented. "
            "Summary level controls detail density, not whether a major topic may disappear.\n"
            "- DO NOT COMPRESS BELOW THE TARGET: Merge and remove duplicates. "
            "If the length instruction asks for more words than the input has, "
            "keep ALL remaining non-redundant content; do not shorten further and do not invent filler.\n"
            "- RESPECT LENGTH INSTRUCTION: If a length instruction is provided, follow it. "
            "Coming in far below the target while dropping major topics is an error.\n"
            "- The output IS the unified summary. Never an assistant, option menu, cover blurb, "
            "questions to the reader, or 'what do you need?'.\n"
            "- FORBIDDEN: first person, learning diaries, invented questions, "
            "'what I learned' or 'points to clarify' sections.\n"
            "- The index is not developed content: do not summarize units, examples or APIs "
            "that only appear in the table of contents if the document body does not explain them.\n"
            "- Name only tools, libraries, APIs, editors and URLs that appear literally in the blocks.\n"
            "- Do not mention 'block 1' or internal pipeline labels.\n"
            "- Do not invent ISBN, book titles or Java/JVM comparisons the source does not make.\n"
            "- LANGUAGE: write the ENTIRE summary in English. Translate blocks that are in Spanish or another language. "
            "Other languages only in quotations, code or proper names.\n"
            "- A block that says 'INDEX ONLY' or lists units/pages without explaining them "
            "is ONLY an index: DISCARD IT. Do not mention it in the final summary. "
            "Do not list index units. Devote the summary to content actually developed.\n"
            "- PRESERVE WITHOUT DILUTING: tool names, files, numeric constants, "
            "point-by-point comparisons, and certainty hedges (theoretically, may, does not imply, only if).\n"
            "- NO token padding: do not clone sections, do not paraphrase the same block several times, "
            "do not invent tools, APIs, editors or runtimes that are not in the source.\n"
            "- If a topic is already written, do not write it again. "
            "- Priority order: factuality, coverage, completeness, coherence, structure, then concision. "
            "Concision must not destroy coverage."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Available Styles and Tones:**"

    def get_semantic_profile_title(self) -> str:
        return "**Semantic Profile (Information to Preserve):**"

    def get_length_instruction_title(self) -> str:
        return "**Length Instruction:**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Express the main thesis, essential conclusions, and central concepts "
                "in a highly condensed form. Keep every major pillar. "
                "Omit secondary examples, anecdotes, reading tips, and minor nuances."
            ),
            SummaryLevel.CONCISE: (
                "Preserve main arguments, essential justifications, and the primary thematic structure. "
                "Be direct; trim secondary elaboration without dropping important sections."
            ),
            SummaryLevel.MODERATE: (
                "Preserve arguments, justifications, relevant evidence, representative examples, "
                "and important taxonomies."
            ),
            SummaryLevel.DETAILED: (
                "Preserve subtopics, methodology, evidence, implications, complete taxonomies, "
                "and relationships between concepts."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Preserve details including exceptions, nuances, particular cases, context, "
                "and formally relevant particulars. "
                "In technical tutorials: do not omit definitions of system nature "
                "(interpreted/compiled, client/server), comparative tables, tool names, "
                "example files, numeric constants or example conditions."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "LENGTH / DENSITY: Produce a summary that is visibly shorter than moderate. "
                "Keep the thesis, pillars, and central definitions. "
                "Omit secondary examples, anecdotes, reading recommendations, and any note about an index. "
                "At most one short example per pillar, and only if it clarifies the definition. "
                "Coming in shorter than moderate is correct if major topics survive. "
                "Do not drop a pillar; do not copy every moderate-level example. "
                "Prefer dense phrasing over listing every case."
            ),
            SummaryLevel.CONCISE: (
                "LENGTH / DENSITY: Produce a brief summary, longer than very_concise and shorter than moderate. "
                "Prefer compact wording over deleting important sections. "
                "One representative example per major topic is enough."
            ),
            SummaryLevel.MODERATE: (
                "LENGTH / DENSITY: Produce a medium-length summary, visibly longer than very_concise "
                "and shorter than very_detailed. "
                "Keep one representative example per major concept, with distinctive numbers or names from the source. "
                "Do not copy every case or anecdote."
            ),
            SummaryLevel.DETAILED: (
                "LENGTH / DENSITY: Produce a detailed summary, longer than moderate. "
                "Take the space needed for subtopics, evidence, and several source examples."
            ),
            SummaryLevel.VERY_DETAILED: (
                "LENGTH / DENSITY: Produce a summary visibly longer than moderate. "
                "Keep every example, figure, name, exception, and condition developed in the source body. "
                "Do not compress those distinctive facts. "
                "Never pad by repeating paragraphs, cloning sections, citing the index, "
                "or adding external knowledge."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "COVERAGE GUARANTEE (applies at every summary level): "
            "Main ideas, essential concepts, important section topics, and central terms MUST survive. "
            "Summary level controls detail density and secondary elaboration only. "
            "It never authorizes dropping a major section or the document's core thesis."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Coverage checklist (only if the section is DEVELOPED in the blocks, "
            "not if it only appears in an index):**\n"
            f"{lines}\n"
            "Do not invent the content of a header that the blocks do not explain."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Closing instruction:** "
            "Cover the distinctive facts of THIS fragment at the density of the length instruction. "
            "Use the available output budget for those facts; do not stop early if important details remain. "
            "Do not repeat paragraphs to fill space. "
            "Always end on a complete sentence."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "index entries"
        return (
            "INDEX ONLY — this fragment is a table of contents, not developed lessons. "
            f"Listed: {listed}. "
            "Do not present these entries as if the document explained them here."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "You are an expert document synthesizer. Summarize the full document "
            "in a single pass. Preserve important conceptual structure "
            "(relevant titles/sections), main ideas, definitions, "
            "procedures, examples and central terms. "
            "Emit clean Markdown. Do not invent content. "
            "Do not write a learning diary or lists of questions.\n"
            "The index or table of contents is NOT developed content: "
            "mention it only as an index; do not present units or examples from the index "
            "as if the document body had explained them.\n"
            "CRITICAL PRIORITY: preserve language nature (interpreted/compiled), "
            "execution environment (client/server), static/dynamic contrast, "
            "comparative tables, tool names, files, numeric constants "
            "and certainty hedges (theoretically, may, does not imply, only if).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "You are a formatting editor. Your only task is to apply Markdown formatting "
            "to the provided text.\n\n"
            "Do NOT summarize, shorten, expand, reinterpret, or omit information.\n"
            "Do NOT add an introduction, conclusion, global title, or external knowledge.\n"
            "Preserve order, lists, tables, code, URLs, and technical terms.\n"
            "If a formatting constraint conflicts with preserving information, preserve the information."
        )

    def get_format_strict_rules(self) -> str:
        return """
CRITICAL FORMATTING RULES:
1. You must preserve all information contained in the input.
2. Do not omit any section, paragraph, list item, table, code example, URL, technical term, or factual statement.
3. Do not summarize, shorten, expand, reinterpret, or add information.
4. Your task is formatting only.
5. The output must contain all source information, preserving the original order.
6. If formatting constraints conflict with preserving information, preserving information has priority.
7. Never use external knowledge.
8. Never complete missing information.
9. Never invent examples or explanations.
10. Output ONLY the formatted version of the input. Do NOT add any title header at the top of your output. Do NOT add an "Introduction" section. Do NOT add conclusions. Do NOT invent section titles.
11. Preserve paragraph structure; do not prefix every paragraph with bullet markers unless the input already does.
12. If you cannot fit all content, output as much as fits and STOP at a sentence boundary. Never emit "[texto truncado]" or similar placeholders.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Please apply the format and style indicated in the instructions to the following text. "
            "Do NOT summarize or omit information:\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nIMPORTANT: This is BLOCK 1 of {total} in a multi-part document. "
                "Format this section as the OPENING of the document. "
                "You MAY include an introduction here if the content warrants it. "
                "Do NOT add a conclusion or closing remarks."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nIMPORTANT: This is BLOCK {idx} of {total} (LAST BLOCK) in a multi-part document. "
                "Format this section as the CLOSING of the document. "
                "You MAY include a conclusion or closing remarks here if the content warrants it. "
                "Do NOT add a new introduction or restart numbering."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nIMPORTANT: This is BLOCK {idx} of {total} (MIDDLE BLOCK) in a multi-part document. "
            "Format this as a CONTINUATION of the document. "
            "Do NOT add an introduction, do NOT add a conclusion, do NOT restart section numbering."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Process the following text blocks. "
            "Write the unified output only in English; translate any block written in Spanish or another language. "
            "If a block is only an index, ignore it completely; do not mention it.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Block {block_index} (Fragments: {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "CRITICAL INSTRUCTION: You are an intermediate reduction step. "
            "Merge and deduplicate the provided blocks. "
            f"Target remaining length: approximately {pct}% of the input (~{target_words} words). "
            f"Write at least {min_words} words. Do NOT compress substantially below this target. "
            "Do not repeat paragraphs to fill space. "
            "Preserve distinctive names, examples, slogans, conclusions, and bibliographic facts from EVERY block. "
            "Discard only repeated phrasing and verbose restatements. Do not invent content.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "CRITICAL INSTRUCTION: You are the FINAL synthesis step. "
            "Integrate the blocks into a single summary in English, without duplicating sections. "
            f"Coverage floor: keep at least ~{min_words} words of non-redundant content "
            f"(target ~{target_words}) if the blocks contain it. "
            "If the blocks have less than the target, keep ALL distinctive content; "
            "do not compress further and do not invent filler to reach the count. "
            "If the blocks have more, merge duplicates but do not delete topics, figures, names or examples. "
            "An index is not developed content: omit those blocks and do not mention that an index exists. "
            "Do not present units, examples or APIs that only appear in the table of contents. "
            "Name only tools and APIs that are in the blocks.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        return (
            "CRITICAL: Write the summary itself. Never a help menu, assistant greeting, "
            "book cover, or questions to the reader.\n\n"
        )
