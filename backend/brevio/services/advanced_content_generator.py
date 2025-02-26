class AdvancedContentGenerator:
    TEMPLATES = {
        # Núcleo Base
        'base': {
            'structure': [
                "## Título Principal",
                "### Contexto",
                "### Elementos Clave",
                "### Detalles Relevantes",
                "### Aplicaciones Prácticas"
            ],
            'rules': [
                "Excluir contenido promocional",
                "Evitar jerga innecesaria",
                "Priorizar información verificable"
            ]
        },
        
        # Especializaciones por Categoría
        'programming': {
            'sections': {
                'code_examples': "### Ejemplos de Implementación",
                'best_practices': "### Patrones Recomendados",
                'debugging_tips': "### Errores Comunes",
                'compatibility': "### Compatibilidad y Dependencias",
                'performance': "### Consideraciones de Rendimiento"
            },
            'styles': {
                'tutorial': {"tono": "Didáctico", "elementos": ["code_examples", "debugging_tips"]},
                'api_docs': {"tono": "Técnico", "elementos": ["compatibility", "best_practices"]},
                'optimization': {"tono": "Analítico", "elementos": ["performance", "code_examples"]}
            },
            'rules': [
                "Incluir versiones de frameworks/lenguajes",
                "Especificar requisitos de sistema cuando sea necesario"
            ]
        },
        
        'business': {
            'sections': {
                'kpi_analysis': "### Análisis de Métricas",
                'swot': "### Análisis SWOT",
                'decision_points': "### Puntos de Decisión Clave",
                'market_context': "### Contexto de Mercado",
                'stakeholders': "### Impacto en Stakeholders",
                'risk_assessment': "### Evaluación de Riesgos"
            },
            'styles': {
                'executive': {"tono": "Concisa", "elementos": ["kpi_analysis", "decision_points"]},
                'investor': {"tono": "Persuasivo", "elementos": ["market_context", "swot"]},
                'internal': {"tono": "Directivo", "elementos": ["stakeholders", "risk_assessment"]}
            },
            'rules': [
                "Incluir comparativas con competidores clave",
                "Destacar tendencias históricas relevantes"
            ]
        },
        
        'journalism': {
            'sections': {
                '5w': "### Contexto (5W)",
                'sources': "### Fuentes Verificadas",
                'timeline': "### Cronología de Eventos",
                'impact': "### Impacto Social/Económico",
                'reactions': "### Reacciones Oficiales",
                'background': "### Antecedentes Históricos"
            },
            'styles': {
                'breaking_news': {"tono": "Urgente", "elementos": ["5w", "timeline"]},
                'investigative': {"tono": "Profundo", "elementos": ["sources", "background"]},
                'analysis': {"tono": "Interpretativo", "elementos": ["impact", "reactions"]}
            },
            'rules': [
                "Contrastar fuentes oficiales y alternativas",
                "Evitar especulaciones sin fundamento"
            ]
        },
        
        'science': {
            'sections': {
                'methodology': "### Metodología",
                'findings': "### Hallazgos Principales",
                'limitations': "### Limitaciones del Estudio",
                'implications': "### Implicaciones Científicas",
                'future_research': "### Investigación Futura"
            },
            'styles': {
                'academic': {"tono": "Formal", "elementos": ["methodology", "limitations"]},
                'educational': {"tono": "Accesible", "elementos": ["findings", "implications"]},
                'research': {"tono": "Técnico", "elementos": ["methodology", "future_research"]}
            },
            'rules': [
                "Citar referencias académicas siguiendo estándar APA/MLA",
                "Distinguir entre correlación y causalidad"
            ]
        },
        
        'medical': {
            'sections': {
                'diagnosis': "### Diagnóstico",
                'treatment': "### Opciones de Tratamiento",
                'prevention': "### Medidas Preventivas",
                'research': "### Investigaciones Recientes",
                'patient_info': "### Información para Pacientes"
            },
            'styles': {
                'clinical': {"tono": "Profesional", "elementos": ["diagnosis", "treatment"]},
                'patient': {"tono": "Informativo", "elementos": ["prevention", "patient_info"]},
                'research': {"tono": "Científico", "elementos": ["research", "diagnosis"]}
            },
            'rules': [
                "Incluir disclaimers médicos apropiados",
                "Referenciar guías clínicas actualizadas"
            ]
        }
    }
    
    def generate_prompt(self, category, style, output_format='markdown', lang='es', source_type=None):
        if category not in self.TEMPLATES:
            raise ValueError(f"Categoría '{category}' no encontrada. Opciones disponibles: {', '.join(self.TEMPLATES.keys())}")
        
        base = self.TEMPLATES['base']
        spec = self.TEMPLATES.get(category, {})
        
        if style not in spec.get('styles', {}):
            raise ValueError(f"Estilo '{style}' no encontrado para categoría '{category}'. Opciones disponibles: {', '.join(spec.get('styles', {}).keys())}")
            
        style_info = spec['styles'][style]
        
        prompt = [
            f"# Generador de Resumen: {category.replace('_', ' ').title()} - {style.replace('_', ' ').title()}",
            f"Genera un resumen en {output_format.upper()} para contenido de {category.replace('_', ' ').title()}",
            f"**Estilo requerido**: {style.replace('_', ' ').title()} ({style_info['tono']})",
            "",
            "**Instrucciones especiales**:"
        ]
        
        all_rules = base['rules'] + spec.get('rules', [])
        prompt.extend([f"- {rule}" for rule in all_rules])
        
        prompt.append("")
        prompt.append("**Estructura requerida**:")
        
        sections = base['structure'].copy()
        if 'sections' in spec and 'elementos' in style_info:
            for elemento in style_info['elementos']:
                if elemento in spec['sections']:
                    sections.append(spec['sections'][elemento])
        
        formatted_sections = []
        for section in sections:
            if output_format == 'markdown':
                # Mantener el formato markdown pero ajustar niveles si es necesario
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(f"{'#' * header_level} {content}")
            elif output_format == 'html':
                # Convertir a formato HTML
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(f"<h{header_level}>{content}</h{header_level}>")
            elif output_format == 'json':
                # Formato para representación JSON
                header_level = section.count('#')
                content = section.split(' ', header_level)[-1]
                formatted_sections.append(f'"section_{len(formatted_sections)}": "{content}"')
            else:  # texto plano u otros
                # Simplificar a texto plano
                content = section.split(' ', section.count('#'))[-1]
                formatted_sections.append(f"{content.upper()}")
        
        # Añadir secciones formateadas
        if output_format == 'json':
            prompt.append("```json\n{")
            prompt.extend([f"  {section}," for section in formatted_sections[:-1]])
            prompt.append(f"  {formatted_sections[-1]}\n}}\n```")
        else:
            prompt.extend(formatted_sections)
        
        # Consideraciones especiales según el tipo de fuente
        prompt.append("")
        prompt.append("**Consideraciones especiales**:")
        
        source_considerations = {
            'video': "- Video: Incluir timeline con marcas de tiempo (00:00 - 00:00)",
            'pdf': "- PDF: Referenciar secciones/páginas clave con números de página",
            'audio': "- Audio: Destacar citas textuales relevantes con timestamp",
            'web': "- Web: Incluir enlaces a fuentes adicionales relevantes",
            None: "- Adaptar al formato de la fuente original"
        }
        
        if source_type:
            prompt.append(source_considerations.get(source_type, source_considerations[None]))
        else:
            for src_type, consideration in source_considerations.items():
                if src_type is not None:
                    prompt.append(consideration)
        
        prompt.append(f"- Traducción completa al {lang} manteniendo tecnicismos originales")
        
        prompt.append("")
        prompt.append("**Metadatos**:")
        prompt.append(f"- Categoría: {category}")
        prompt.append(f"- Estilo: {style}")
        prompt.append(f"- Formato: {output_format}")
        prompt.append(f"- Idioma: {lang}")
        if source_type:
            prompt.append(f"- Tipo de fuente: {source_type}")
        
        return '\n'.join(prompt)

    def get_available_templates(self):
        summary = {}
        for category, data in self.TEMPLATES.items():
            if category != 'base':
                summary[category] = list(data.get('styles', {}).keys())
        return summary
        
    def add_custom_template(self, category, sections, styles, rules=None):
        if category in self.TEMPLATES:
            raise ValueError(f"La categoría '{category}' ya existe. Use otro nombre o actualice la existente.")
            
        self.TEMPLATES[category] = {
            'sections': sections,
            'styles': styles
        }
        
        if rules:
            self.TEMPLATES[category]['rules'] = rules
            
        return f"Plantilla '{category}' creada con éxito con {len(sections)} secciones y {len(styles)} estilos."
