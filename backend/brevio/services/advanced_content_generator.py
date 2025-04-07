import html
import re
from typing import Any, Dict, List, Optional

from googletrans import Translator

from brevio.enums.language import LanguageType
from brevio.enums.source_type import SourceType


class AdvancedContentGenerator:
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
                "Summarize concisely, removing redundancies",
                "Preserve the original title if present, without modification, using its exact wording and format (e.g., # Title, ## Subtitle)",
                "Adapt fully to the tone, intent, and implicit structure of the source content",
                "Do not introduce titles, subtitles, or headings unless explicitly present in the original text",
                "Maintain key examples or concepts in their original format (e.g., lists, code, italics)",
                "Avoid subjective interpretations or unnecessary modifications",
                "Produce a single, continuous block of text unless the original content specifies otherwise",
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
                - **Risk 2**: Data validation errors.chronicle
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
    }

    async def generate_prompt(
        self,
        category: str,
        style: str,
        output_format: str = "markdown",
        lang: LanguageType = LanguageType.ENGLISH,
        source_type: Optional[SourceType] = None,
        content_length: Optional[int] = None,
    ) -> str:
        if not category:
            raise ValueError("Category cannot be empty")
        if category not in self.TEMPLATES:
            raise ValueError(
                f"Category '{category}' not found: {', '.join(self.TEMPLATES.keys())}"
            )

        if not style:
            raise ValueError("Style cannot be empty")

        spec: dict = self.TEMPLATES[category]

        if style not in spec["styles"]:
            raise ValueError(
                f"Style '{style}' not valid for '{category.title()}': {', '.join(spec['styles'].keys())}"
            )

        if content_length is not None:
            if not isinstance(content_length, int) or content_length <= 0:
                raise ValueError("Content length must be a positive integer")

        style_info = spec["styles"][style]
        if source_type is not None:
            # Check if source_type is a valid enum member
            if not isinstance(source_type, SourceType):
                try:
                    source_type = SourceType(source_type)
                except ValueError:
                    raise ValueError(f"Source type '{source_type}' not supported")

            # Check if source_type is valid for this style
            if source_type not in style_info["source_types"]:
                raise ValueError(
                    f"Source type '{source_type}' not supported for '{style}' in '{category}'."
                )

        prompt: List[str] = [
            f"# Prompt for {category.title()} - {style.title()}",
            f"**Objective:** Generate content in {output_format.upper()} optimized for {category.title()}",
            f"**Style:** {style.title()} ({style_info['tone']})",
            f"**Key Needs:** {spec.get('needs', 'Adapt to context')}",
            "",
        ]

        prompt.append("**Instructions**:")
        all_rules = spec.get("rules", [])
        all_rules.append(
            "Avoid generic statements like 'The text is now free of redundancies and repetitions while maintaining clarity and cohesion'. Focus on providing concrete and specific feedback."
        )
        all_rules.append(
            "Do not include phrases like 'Here is the revised text, eliminating redundancies and repetitions, while preserving all the details and the original structure."
        )
        all_rules.append(
            "You must not include the ```markdown tag under any circumstances. If you use code blocks, they must be either unspecified or use a language other than Markdown."
        )

        prompt.extend([f"- {rule}" for rule in all_rules])

        if content_length:
            prompt.append(
                f"- Summarize a {content_length}-page document comprehensively, capturing main themes, key points, and overall purpose in approximately 200-300 words."
            )

        prompt.append("\n**Expected Format**:")
        structure = spec["structures"].get(
            style, ["Direct summary without additional headings"]
        )
        for line in structure:
            if output_format == "markdown":
                prompt.append(line)
            elif output_format == "text":
                prompt.append(line.lstrip("#* ").strip("*- ").upper())

        prompt.append("\n**Source Handling**:")

        source_rules = {
            "video": "- Use timestamps [MM:SS] for key events",
            "audio": "- Include relevant quotes with timestamps if applicable",
            "text": "- Summarize main ideas with references if applicable",
            None: "- Adapt to the original content",
        }

        prompt.append(
            source_rules.get(
                source_type.value if source_type else None, source_rules[None]
            )
        )

        if category in self.EXAMPLES and style in self.EXAMPLES[category]:
            prompt.append("\n**Example**:")
            example = self.EXAMPLES[category][style]
            if output_format == "markdown":
                prompt.append(f"```markdown\n{example}\n```")
            else:
                prompt.append(example.replace("#", "").replace("*", "").strip())

        prompt_text = "\n".join(prompt)

        if lang != "en":
            translator = Translator()
            try:
                translated = await translator.translate(prompt_text, dest=lang.value)
                prompt_text = self.sanitize_markdown(translated.text)
            except Exception as e:
                print(f"Translation error: {e}")

        print("prompt", "\n" + prompt_text)
        return prompt_text

    def sanitize_markdown(
        self,
        prompt_text: str
        # Remove extra spaces before and after the double asterisks in headers (e.g., | **Indicator** |)
    ) -> str:
        # Remove extra spaces before and after the double asterisks in headers (e.g., | **Indicator** |)
        prompt_text = re.sub(r"\| \*\*([^*]+)\*\* \|", r"| **\1** |", prompt_text)

        # Remove extra spaces after asterisks in other areas (like **text**)
        prompt_text = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", prompt_text)

        # Ensure no spaces before and after double asterisks in any other places
        prompt_text = re.sub(r" \*\*([^*]+)\*\* ", r"**\1**", prompt_text)

        # Escapar caracteres HTML para prevenir XSS
        return html.escape(prompt_text)

    def get_available_templates(self) -> dict:
        summary = {}
        for category, data in self.TEMPLATES.items():
            summary[category] = [
                {"category": style_name, "source_types": style_data["source_types"]}
                for style_name, style_data in data.get("styles", {}).items()
            ]
        return summary

    def add_custom_template(
        self,
        category: str,
        structures: dict,
        styles: dict,
        rules: Optional[List[str]] = None,
        examples: Optional[dict] = None,
        needs: Optional[str] = None,
    ) -> str:
        if not structures:
            raise ValueError("Structures cannot be empty")
        if not styles:
            raise ValueError("Styles cannot be empty")
        if category in self.TEMPLATES:
            raise ValueError(
                f"The category '{category}' already exists. Use a different name or update the existing one."
            )
        self.TEMPLATES[category] = {"structures": structures, "styles": styles}
        if rules:
            self.TEMPLATES[category]["rules"] = rules
        if examples:
            self.EXAMPLES[category] = examples
        if needs:
            self.TEMPLATES[category]["needs"] = needs
        return f"Template '{category}' successfully created with {len(structures)} structures and {len(styles)} styles."

    def get_all_category_style_combinations(self) -> List[tuple[str, str]]:
        combinations = []
        for category, template_data in self.TEMPLATES.items():
            for style_name in template_data["styles"].keys():
                combinations.append((category, style_name))
        return combinations
