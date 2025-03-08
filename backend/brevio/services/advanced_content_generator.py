from googletrans import Translator
import asyncio

class AdvancedContentGenerator:
    TEMPLATES = {
        'simple_summary': {
            'structures': {
                'default': ["Direct summary without additional headings"]
            },
            'styles': {
                'default': {"tone": "Neutral, adapted to context", "elements": [], "source_types": ["text", "video", "audio"]}
            },
            'rules': [
                "Summarize concisely, removing redundancies",
                "Preserve the original title if present, without modification, using its exact wording and format (e.g., # Title, ## Subtitle)",
                "Adapt fully to the tone, intent, and implicit structure of the source content",
                "Do not introduce titles, subtitles, or headings unless explicitly present in the original text",
                "Maintain key examples or concepts in their original format (e.g., lists, code, italics)",
                "Avoid subjective interpretations or unnecessary modifications",
                "Produce a single, continuous block of text unless the original content specifies otherwise"
            ],
            'needs': "Simplicity and fidelity to the original content"
        },
        'journalism': {
            'structures': {
                'chronicle': ["# [Event] Live", "- **[MM:SS]** Statement or key fact"],
                'news_wire': ["[Date] - [Location] - Brief and direct summary"],
                'analysis': ["## [Topic] In Depth", "### [Aspect]", "- Key point"]
            },
            'styles': {
                'chronicle': {"tone": "Narrative, urgent", "elements": ["timeline"], "source_types": ["video", "audio"]},
                'news_wire': {"tone": "Direct, informative", "elements": [], "source_types": ["text", "video", "audio"]},
                'analysis': {"tone": "Reflective, contextual", "elements": ["subsections"], "source_types": ["text"]}
            },
            'rules': [
                "Include precise timestamps for chronicle",
                "Cite sources if applicable",
                "Avoid opinions in news wire"
            ],
            'needs': "Speed in news wire, detail in chronicle, context in analysis"
        },
        'marketing': {
            'structures': {
                'highlights': ["# ✨ [Campaign] - Highlights", "🎯 **Key:** Value"],
                'storytelling': ["**[Brand] - A Story:**", "Emotional narrative paragraph"],
                'report': ["## [Campaign] - Results", "| **Metric** | **Goal** | **Actual** |"]
            },
            'styles': {
                'highlights': {"tone": "Engaging, visual", "elements": ["emojis", "bullet_points"], "source_types": ["text", "video"]},
                'storytelling': {"tone": "Emotional, immersive", "elements": ["narrative"], "source_types": ["text"]},
                'report': {"tone": "Analytical, clear", "elements": ["table"], "source_types": ["text"]}
            },
            'rules': [
                "Use engaging language for highlights and storytelling",
                "Include KPIs in report",
                "Avoid excessive technical terms"
            ],
            'needs': "Visual impact, emotional connection, actionable data"
        },
        'health': {
            'structures': {
                'report': ["**[Study/Treatment] - Clinical Report:**", "Concise technical paragraph"],
                'summary': ["# 🩺 [Topic] - Summary", "📈 **Indicator:** Result", "| Week | Progress |"],
                'case': ["**[Patient] - Clinical Case:**", "Detailed narrative"]
            },
            'styles': {
                'report': {"tone": "Precise, professional", "elements": [], "source_types": ["text"]},
                'summary': {"tone": "Visual, accessible", "elements": ["bullet_points", "table"], "source_types": ["text", "video"]},
                'case': {"tone": "Narrative, clinical", "elements": ["narrative"], "source_types": ["text", "audio"]}
            },
            'rules': [
                "Include quantitative data when possible",
                "Maintain scientific rigor",
                "Adjust language to the audience (technical or general)"
            ],
            'needs': "Clarity for doctors, accessibility for patients, precision in data"
        },
        'technology': {
            'structures': {
                'changelog': ["# [Version] - Update", "✨ **New Features:**", "- Feature", "🐛 **Fixes:**", "- Fix"],
                'proposal': ["**[Project] - Technical Proposal:**", "Structured paragraph"],
                'diagram': ["# [Process] - Flow", "```mermaid", "graph TD", "  A --> B", "```"]
            },
            'styles': {
                'changelog': {"tone": "Technical, concise", "elements": ["bullet_points"], "source_types": ["text"]},
                'proposal': {"tone": "Persuasive, clear", "elements": [], "source_types": ["text"]},
                'diagram': {"tone": "Visual, descriptive", "elements": ["mermaid"], "source_types": ["text", "video"]}
            },
            'rules': [
                "Use specific technical terminology",
                "Highlight benefits in proposals",
                "Include clear flows in diagrams"
            ],
            'needs': "Quick documentation, persuasion for stakeholders, process clarity"
        },
        'education': {
            'structures': {
                'guide': ["# 📚 [Topic] - Guide", "## [Section]", "- **Concept:** Explanation"],
                'quick_ref': ["**[Topic] - Quick Reference:**", "- Key point"],
                'timeline': ["# 🎥 [Class] - Timeline", "- **[MM:SS]** Content"]
            },
            'styles': {
                'guide': {"tone": "Educational, structured", "elements": ["subsections", "bullet_points"], "source_types": ["text"]},
                'quick_ref': {"tone": "Concise, practical", "elements": ["bullet_points"], "source_types": ["text"]},
                'timeline': {"tone": "Chronological, clear", "elements": ["timeline"], "source_types": ["video"]}
            },
            'rules': [
                "Use practical examples",
                "Avoid information overload",
                "Align with learning objectives"
            ],
            'needs': "Ease of study, quick reference, video tracking"
        },
        'architecture': {
            'structures': {
                'chronicle': ["# 🏛️ [Project] - Chronicle", "- **[MM:SS]** Highlighted element"],
                'report': ["**[Project] - Technical Report:**", "Paragraph with key details"],
                'list': ["# [Project] - Details", "- **Aspect:** Description"]
            },
            'styles': {
                'chronicle': {"tone": "Narrative, visual", "elements": ["timeline"], "source_types": ["video"]},
                'report': {"tone": "Technical, detailed", "elements": [], "source_types": ["text"]},
                'list': {"tone": "Descriptive, organized", "elements": ["bullet_points"], "source_types": ["text"]}
            },
            'rules': [
                "Highlight innovation or sustainability",
                "Include technical data if applicable",
                "Be visually appealing"
            ],
            'needs': "Technical documentation, attractive presentation, video tracking"
        },
        'finance': {
            'structures': {
                'report': ["# 💰 [Period] - Report", "- **Indicator:** Value"],
                'table': ["## [Period] - Summary", "| **Indicator** | **Value** |"],
                'executive': ["**[Period] - Executive:**", "Brief paragraph"]
            },
            'styles': {
                'report': {"tone": "Analytical, formal", "elements": ["bullet_points"], "source_types": ["text"]},
                'table': {"tone": "Visual, concise", "elements": ["table"], "source_types": ["text"]},
                'executive': {"tone": "Direct, executive", "elements": [], "source_types": ["text"]}
            },
            'rules': [
                "Include clear figures",
                "Avoid ambiguity",
                "Guide decision-making"
            ],
            'needs': "Actionable data, visual synthesis, executive reports"
        },
        'tourism': {
            'structures': {
                'chronicle': ["# 🌍 [Destination] - Chronicle", "- **[MM:SS]** Initiative"],
                'report': ["**[Destination] - Policies:**", "Formal paragraph"],
                'list': ["# [Destination] - Initiatives", "- **Area:** Detail"]
            },
            'styles': {
                'chronicle': {"tone": "Narrative, engaging", "elements": ["timeline"], "source_types": ["audio", "video"]},
                'report': {"tone": "Formal, informative", "elements": [], "source_types": ["text"]},
                'list': {"tone": "Descriptive, clear", "elements": ["bullet_points"], "source_types": ["text"]}
            },
            'rules': [
                "Highlight sustainability or appeal",
                "Include practical data",
                "Avoid exaggerations"
            ],
            'needs': "Engaging promotion, useful information, clear policies"
        }
    }

    EXAMPLES = {
        'simple_summary': {
            'default': "The content describes economic measures announced on March 08, 2025, including tax reductions and credit lines."
        },
        'journalism': {
            'chronicle': "# Debate Live\n- **[00:45]** Announcement of measures.\n- **[02:10]** Tax reduction.",
            'news_wire': "[March 08, 2025] - Capital - President announces economic measures.",
            'analysis': "## Tax Reform In Depth\n### Taxes\n- 10% reduction for SMEs."
        },
        'marketing': {
            'highlights': "# ✨ EcoLife Launch - Highlights\n🎯 **Target:** Youth.\n📈 **Sales:** +15%.",
            'storytelling': "**EcoLife - A Story:** A young woman finds purpose in sustainability.",
            'report': "## EcoLife - Results\n| **Metric** | **Goal** | **Actual** |\n| Sales     | +15%    | +18%      |"
        },
        'health': {
            'report': "**Treatment X - Clinical Report:** Reduces symptoms by 70% after 8 weeks.",
            'summary': "# 🩺 Treatment X - Summary\n📈 **Efectiveness:** 70%.\n| Week | Progress |\n| 8    | 70%     |",
            'case': "**Patient A - Clinical Case:** A 62-year-old man improves after 2 weeks."
        },
        'technology': {
            'changelog': "# v3.0 - Update\n✨ **New Features:**\n- OCR.\n🐛 **Fixes:**\n- Export.",
            'proposal': "**App X - Technical Proposal:** Integrate API for automation.",
            'diagram': "# App Flow\n```mermaid\ngraph TD\n  A[Start] --> B[Process]\n```"
        },
        'education': {
            'guide': "# 📚 Python - Guide\n## Basics\n- **Print:** Display text.",
            'quick_ref': "**Python - Quick Reference:**\n- Print: Output.\n- If: Condition.",
            'timeline': "# 🎥 Python Class - Timeline\n- **[01:00]** Intro to variables."
        },
        'architecture': {
            'chronicle': "# 🏛️ Green Tower - Chronicle\n- **[01:15]** Sustainable materials.",
            'report': "**Green Tower - Technical Report:** Design uses renewable energy.",
            'list': "# Green Tower - Details\n- **Materials:** Recycled.\n- **Energy:** Solar."
        },
        'finance': {
            'report': "# 💰 Q1 2025 - Report\n- **Revenue:** +5%.",
            'table': "## Q1 2025 - Summary\n| **Indicator** | **Value** |\n| Revenue      | +5%      |",
            'executive': "**Q1 2025 - Executive:** 5% growth due to technology."
        },
        'tourism': {
            'chronicle': "# 🌍 Blue Beach - Chronicle\n- **[01:00]** Eco-tourism.",
            'report': "**Blue Beach - Policies:** Promotes sustainability.",
            'list': "# Blue Beach - Initiatives\n- **Ecology:** Less plastic."
        }
    }

    async def generate_prompt(self, category, style, output_format='markdown', lang='en', source_type=None, content_length=None):
        if category not in self.TEMPLATES:
            raise ValueError(f"Category '{category}' not found: {', '.join(self.TEMPLATES.keys())}")
        spec = self.TEMPLATES[category]
        if style not in spec['styles']:
            raise ValueError(f"Style '{style}' not valid for '{category}': {', '.join(spec['styles'].keys())}")
        style_info = spec['styles'][style]

        if source_type and source_type not in style_info['source_types']:
            raise ValueError(f"Source type '{source_type}' not supported for '{style}' in '{category}'.")

        prompt = [
            f"# Prompt for {category.title()} - {style.title()}",
            f"**Objective:** Generate content in {output_format.upper()} optimized for {category.title()}",
            f"**Style:** {style.title()} ({style_info['tone']})",
            f"**Key Needs:** {spec.get('needs', 'Adapt to context')}",
            ""
        ]

        prompt.append("**Instructions**:")
        all_rules = spec.get('rules', [])
        prompt.extend([f"- {rule}" for rule in all_rules])

        if content_length:
            prompt.append(f"- Summarize a {content_length}-page document comprehensively, capturing main themes, key points, and overall purpose in approximately 200-300 words.")

        prompt.append("\n**Expected Format**:")
        structure = spec['structures'].get(style, ["Direct summary without additional headings"])
        for line in structure:
            if output_format == 'markdown':
                prompt.append(line)
            elif output_format == 'text':
                prompt.append(line.lstrip('#* ').strip('*- ').upper())

        prompt.append("\n**Source Handling**:")
        source_rules = {
            'video': "- Use timestamps [MM:SS] for key events",
            'audio': "- Include relevant quotes with timestamps if applicable",
            'text': "- Summarize main ideas with references if applicable",
            None: "- Adapt to the original content"
        }
        prompt.append(source_rules.get(source_type, source_rules[None]))

        if category in self.EXAMPLES and style in self.EXAMPLES[category]:
            prompt.append("\n**Example**:")
            example = self.EXAMPLES[category][style]
            if output_format == 'markdown':
                prompt.append(f"```markdown\n{example}\n```")
            else:
                prompt.append(example.replace('#', '').replace('*', '').strip())

        prompt_text = '\n'.join(prompt)
        if lang != 'en':
            translator = Translator()
            try:
                translated = await translator.translate(prompt_text, dest=lang)
                prompt_text = translated.text
            except Exception as e:
                print(f"Translation error: {e}")

        return prompt_text

    def get_available_templates(self):
        summary = {}
        for category, data in self.TEMPLATES.items():
            summary[category] = list(data.get('styles', {}).keys())
        return summary

    def add_custom_template(self, category, structures, styles, rules=None, examples=None, needs=None):
        if category in self.TEMPLATES:
            raise ValueError(f"The category '{category}' already exists. Use a different name or update the existing one.")
        self.TEMPLATES[category] = {
            'structures': structures,
            'styles': styles
        }
        if rules:
            self.TEMPLATES[category]['rules'] = rules
        if examples:
            self.EXAMPLES[category] = examples
        if needs:
            self.TEMPLATES[category]['needs'] = needs
        return f"Template '{category}' successfully created with {len(structures)} structures and {len(styles)} styles."

    def get_all_category_style_combinations(self):
        combinations = []
        templates = self.get_available_templates()
        for category, styles in templates.items():
            for style in styles:
                combinations.append((category, style))
        return combinations
