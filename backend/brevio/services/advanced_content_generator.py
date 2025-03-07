# Usamos la librería googletrans para la traducción
from googletrans import Translator


class AdvancedContentGenerator:
    TEMPLATES = {
        'base': {
            'structure': [
                "## Main Title",
                "### Context",
                "### Key Elements",
                "### Relevant Details",
                "### Practical Applications"
            ],
            'rules': [
                "Exclude promotional content",
                "Avoid unnecessary jargon",
                "Prioritize verifiable information"
            ]
        },

        'programming': {
            'sections': {
                'code_examples': "### Code Examples",
                'best_practices': "### Recommended Patterns",
                'debugging_tips': "### Common Errors",
                'compatibility': "### Compatibility and Dependencies",
                'performance': "### Performance Considerations"
            },
            'styles': {
                'tutorial': {"tone": "Didactic", "elements": ["code_examples", "debugging_tips"]},
                'api_docs': {"tone": "Technical", "elements": ["compatibility", "best_practices"]},
                'optimization': {"tone": "Analytical", "elements": ["performance", "code_examples"]}
            },
            'rules': [
                "Include versions of frameworks/languages",
                "Specify system requirements when necessary"
            ]
        },

        'business': {
            'sections': {
                'kpi_analysis': "### KPI Analysis",
                'swot': "### SWOT Analysis",
                'decision_points': "### Key Decision Points",
                'market_context': "### Market Context",
                'stakeholders': "### Stakeholder Impact",
                'risk_assessment': "### Risk Assessment"
            },
            'styles': {
                'executive': {"tone": "Concise", "elements": ["kpi_analysis", "decision_points"]},
                'investor': {"tone": "Persuasive", "elements": ["market_context", "swot"]},
                'internal': {"tone": "Direct", "elements": ["stakeholders", "risk_assessment"]}
            },
            'rules': [
                "Include comparisons with key competitors",
                "Highlight relevant historical trends"
            ]
        },

        'journalism': {
            'sections': {
                '5w': "### Context (5W)",
                'sources': "### Verified Sources",
                'timeline': "### Event Timeline",
                'impact': "### Social/Economic Impact",
                'reactions': "### Official Reactions",
                'background': "### Historical Background"
            },
            'styles': {
                'breaking_news': {"tone": "Urgent", "elements": ["5w", "timeline"]},
                'investigative': {"tone": "In-Depth", "elements": ["sources", "background"]},
                'analysis': {"tone": "Interpretative", "elements": ["impact", "reactions"]}
            },
            'rules': [
                "Contrast official and alternative sources",
                "Avoid baseless speculation"
            ]
        },

        'science': {
            'sections': {
                'methodology': "### Methodology",
                'findings': "### Key Findings",
                'limitations': "### Study Limitations",
                'implications': "### Scientific Implications",
                'future_research': "### Future Research"
            },
            'styles': {
                'academic': {"tone": "Formal", "elements": ["methodology", "limitations"]},
                'educational': {"tone": "Accessible", "elements": ["findings", "implications"]},
                'research': {"tone": "Technical", "elements": ["methodology", "future_research"]}
            },
            'rules': [
                "Cite academic references following APA/MLA standards",
                "Distinguish between correlation and causality"
            ]
        },

        'medical': {
            'sections': {
                'diagnosis': "### Diagnosis",
                'treatment': "### Treatment Options",
                'prevention': "### Preventive Measures",
                'research': "### Recent Research",
                'patient_info': "### Patient Information"
            },
            'styles': {
                'clinical': {"tone": "Professional", "elements": ["diagnosis", "treatment"]},
                'patient': {"tone": "Informative", "elements": ["prevention", "patient_info"]},
                'research': {"tone": "Scientific", "elements": ["research", "diagnosis"]}
            },
            'rules': [
                "Include appropriate medical disclaimers",
                "Reference updated clinical guidelines"
            ]
        },
        'book_summary': {
            'sections': {
                'core_concepts': "### Conceptos Fundamentales",
                'key_tools': "### Herramientas Clave",
                'practical_use_cases': "### Casos de Uso Prácticos",
                'main_lessons': "### Lecciones Principales",
                'best_practices': "### Buenas Prácticas"
            },
            'styles': {
                'executive': {
                    "tone": "Directo y Accionable",
                    "elements": ["core_concepts", "main_lessons"]
                },
                'developer': {
                    "tone": "Técnico sin Jerga",
                    "elements": ["key_tools", "practical_use_cases"]
                }
            },
            'rules': [
                "Máximo 5 puntos por sección",
                "Evitar detalles redundantes",
                "Priorizar ejemplos aplicables",
                "Usar viñetas, no párrafos largos",
                "Incluir comparaciones clave (ej: asyncio vs hilos)"
            ]
        }
    }

    async def generate_prompt(self, category, style, output_format='markdown', lang='en', source_type=None):
        if category not in self.TEMPLATES:
            raise ValueError(
                f"Category '{category}' not found. Available options: {', '.join(self.TEMPLATES.keys())}")

        base = self.TEMPLATES['base']
        spec = self.TEMPLATES.get(category, {})

        if style not in spec.get('styles', {}):
            raise ValueError(
                f"Style '{style}' not found for category '{category}'. Available options: {', '.join(spec.get('styles', {}).keys())}")

        style_info = spec['styles'][style]

        prompt = [
            f"# Summary Generator: {category.replace('_', ' ').title()} - {style.replace('_', ' ').title()}",
            f"Generate a summary in {output_format.upper()} format for content of {category.replace('_', ' ').title()}",
            f"**Required style**: {style.replace('_', ' ').title()} ({style_info['tone']})",
            "",
            "**Special Instructions**:"
        ]

        all_rules = base['rules'] + spec.get('rules', [])
        prompt.extend([f"- {rule}" for rule in all_rules])

        prompt.append("")
        prompt.append("**Required Structure**:")

        sections = base['structure'].copy()
        if 'sections' in spec and 'elements' in style_info:
            for element in style_info['elements']:
                if element in spec['sections']:
                    sections.append(spec['sections'][element])

        formatted_sections = []
        for section in sections:
            if output_format == 'markdown':
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(f"{'#' * header_level} {content}")
            elif output_format == 'html':
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(
                    f"<h{header_level}>{content}</h{header_level}>")
            elif output_format == 'json':
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(
                    f'"section_{len(formatted_sections)}": "{content}"')
            else:
                content = section.split(' ', section.count('#'))[-1]
                formatted_sections.append(f"{content.upper()}")

        if output_format == 'json':
            prompt.append("```json\n{")
            prompt.extend(
                [f"  {section}," for section in formatted_sections[:-1]])
            prompt.append(f"  {formatted_sections[-1]}\n}}\n```")
        else:
            prompt.extend(formatted_sections)

        prompt.append("")
        prompt.append("**Special Considerations**:")

        source_considerations = {
            'video': "- Video: Include timeline with timestamps (00:00 - 00:00)",
            'pdf': "- PDF: Reference key sections/pages with page numbers",
            'audio': "- Audio: Highlight relevant quotes with timestamps",
            'web': "- Web: Include links to relevant additional sources",
            None: "- Adapt to the format of the original source"
        }

        if source_type:
            prompt.append(source_considerations.get(
                source_type, source_considerations[None]))
        else:
            for src_type, consideration in source_considerations.items():
                if src_type is not None:
                    prompt.append(consideration)

        prompt.append(
            f"- Full translation to {lang} maintaining original technical terms")

        prompt.append("")
        prompt.append("**Metadata**:")
        prompt.append(f"- Category: {category}")
        prompt.append(f"- Style: {style}")
        prompt.append(f"- Format: {output_format}")
        prompt.append(f"- Language: {lang}")
        if source_type:
            prompt.append(f"- Source type: {source_type}")

        translator = Translator()
        translated_prompt = await translator.translate('\n'.join(prompt), dest=lang)

        return translated_prompt.text

    def get_available_templates(self):
        summary = {}
        for category, data in self.TEMPLATES.items():
            if category != 'base':
                summary[category] = list(data.get('styles', {}).keys())
        return summary

    def add_custom_template(self, category, sections, styles, rules=None):
        if category in self.TEMPLATES:
            raise ValueError(
                f"The category '{category}' already exists. Use a different name or update the existing one.")

        self.TEMPLATES[category] = {
            'sections': sections,
            'styles': styles
        }

        if rules:
            self.TEMPLATES[category]['rules'] = rules

        return f"Template '{category}' successfully created with {len(sections)} sections and {len(styles)} styles."

    def get_all_category_style_combinations(self):
        combinations = []
        templates = self.get_available_templates()
        for category, styles in templates.items():
            for style in styles:
                combinations.append((category, style))
        return combinations
