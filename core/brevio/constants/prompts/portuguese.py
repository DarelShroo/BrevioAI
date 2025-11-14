from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


class PortuguesePrompts:
    INSTRUCTIONS_TITLE: str = "**Instruções:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Idioma específico:** Português"
    SPECIFIC_LANGUAGE: str = (
        "A partir de agora, todas as respostas devem ser exclusivamente em português."
    )
    EXAMPLE_TITLE: str = "**Exemplo**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["Resumo direto sem títulos adicionais"]},
            "styles": {
                "default": {
                    "tone": "Neutro, adaptado ao contexto",
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
                "Resumir de forma concisa, removendo redundâncias",
                "Preservar o título original, se presente, sem modificações, usando sua redação e formato exatos (ex.: # Título, ## Subtítulo)",
                "Adaptar-se totalmente ao tom, intenção e estrutura implícita do conteúdo original",
                "Não introduzir títulos, subtítulos ou cabeçalhos a menos que explicitamente presentes no texto original",
                "Manter exemplos ou conceitos-chave em seu formato original (listas, código, itálicos, etc.)",
                "Evitar interpretações subjetivas ou modificações desnecessárias",
                "Produzir um único bloco contínuo de texto, a menos que o conteúdo original especifique o contrário",
            ],
            "needs": "Simplicidade e fidelidade ao conteúdo original",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Evento] Ao Vivo",
                    "- **[MM:SS]** Declaração ou fato-chave",
                    "- **[MM:SS]** Descrição do momento ou desenvolvimento principal",
                    "- **[MM:SS]** Reação ou análise do evento",
                ],
                "news_wire": [
                    "[Data] - [Local] - Resumo breve e direto",
                    "### Detalhes Principais",
                    "- [Fato-chave 1]",
                    "- [Fato-chave 2]",
                    "### Contexto",
                    "- [Informações de background]",
                    "### Estatísticas (se aplicável)",
                    "- [Estatística 1]",
                    "- [Estatística 2]",
                    "### Impacto",
                    "- [Impacto a curto prazo]",
                    "- [Implicações a longo prazo]",
                ],
                "analysis": [
                    "## [Tópico] Em Profundidade",
                    "### Visão Geral",
                    "- [Resumo breve do tópico]",
                    "### Aspectos Principais",
                    "- [Aspecto 1]: [Análise detalhada]",
                    "- [Aspecto 2]: [Análise detalhada]",
                    "### Implicações",
                    "- [Implicações a curto prazo]",
                    "- [Implicações a longo prazo]",
                    "### Opiniões de Especialistas",
                    "- [Citação ou perspectiva de um especialista]",
                    "### Conclusão",
                    "- [Resumo dos achados principais e perspectivas futuras]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, urgente",
                    "elements": ["linha do tempo", "momentos-chave", "reações"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Direto, informativo",
                    "elements": [
                        "detalhes-chave",
                        "contexto",
                        "estatísticas",
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
                        "visão geral",
                        "aspectos-chave",
                        "implicações",
                        "opiniões de especialistas",
                        "conclusão",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Incluir timestamps precisos para crônicas",
                "Citar fontes, se aplicável",
                "Evitar opiniões em notícias wire",
                "Usar bullet points para detalhes-chave em notícias wire",
                "Incluir pelo menos uma estatística ou dado em notícias wire",
                "Destacar impactos a curto e longo prazo em notícias wire",
                "Para crônicas, focar em momentos-chave e reações em tempo real",
                "Para análises, fornecer uma exploração detalhada do tópico, incluindo causas, efeitos e perspectivas de especialistas",
            ],
            "needs": [
                "Velocidade em notícias wire, detalhes em crônicas, contexto em análises"
            ],
        },
        "marketing": {
            "structures": {
                "highlights": [
                    "# ✨ [Campanha] - Destaques",
                    "🎯 **Principal:** Valor",
                ],
                "storytelling": [
                    "## [Marca] - Uma História: [Título]",
                    "### Introdução",
                    "- [Gancho emocional ou cenário]",
                    "### Narrativa Principal",
                    "- [Evento ou virada principal]",
                    "- [Desafios ou conflitos]",
                    "- [Resolução ou resultado]",
                    "### Impacto Emocional",
                    "- [Como a história faz o público se sentir]",
                    "### Chamada para Ação",
                    "- [Incentivo para engajar com a marca ou produto]",
                ],
                "report": [
                    "## [Campanha] - Resultados",
                    "### Visão Geral",
                    "- [Resumo breve da campanha e seus objetivos]",
                    "### Métricas Principais",
                    "| **Métrica** | **Meta** | **Realizado** | **Variação** |",
                    "|------------|----------|------------|--------------|",
                    "| [Métrica 1] | [Meta 1] | [Realizado 1] | [Variação 1] |",
                    "| [Métrica 2] | [Meta 2] | [Realizado 2] | [Variação 2] |",
                    "### Análise",
                    "- [Análise detalhada dos resultados, incluindo sucessos e desafios]",
                    "### Recomendações",
                    "- [Recomendações acionáveis baseadas nos dados]",
                    "### Conclusão",
                    "- [Resumo dos achados principais e próximos passos]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Engajante, visual",
                    "elements": ["emojis", "bullet points"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Emocional, imersivo",
                    "elements": ["narrativa", "gancho emocional", "chamada para ação"],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analítico, claro",
                    "elements": ["tabela", "análise", "recomendações"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Usar linguagem engajante para destaques e storytelling",
                "Incluir KPIs no relatório",
                "Evitar termos técnicos excessivos",
                "Para storytelling, focar na conexão emocional e fluxo narrativo",
            ],
            "needs": "Impacto visual, conexão emocional, dados acionáveis",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Estudo/Tratamento] - Relatório Clínico:**",
                    "Parágrafo técnico conciso focado em resultados e eficácia",
                ],
                "summary": [
                    "# 🩺 [Tópico] - Resumo",
                    "📈 **Indicador:** Resultado",
                    "| Semana | Progresso |",
                ],
                "case": ["**[Paciente] - Caso Clínico:**", "Narrativa detalhada"],
            },
            "styles": {
                "report": {
                    "tone": "Formal, preciso, baseado em evidências",
                    "elements": ["dados_quantitativos", "resultados_clínicos"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visual, acessível",
                    "elements": ["bullet_points", "tabela"],
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
                "Sempre incluir dados quantitativos e mensuráveis quando disponíveis",
                "Manter rigor científico e evitar linguagem subjetiva",
                "Ajustar complexidade da linguagem conforme o público (técnico para médicos, simplificado para pacientes)",
                "Garantir clareza, precisão e acessibilidade das informações médicas",
            ],
            "needs": {
                "doctors": "Dados clínicos claros e precisos para decisões informadas",
                "patients": "Explicações acessíveis e compreensíveis sobre condições e tratamentos",
                "researchers": "Informações robustas e baseadas em dados para análise",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Versão] - Atualização",
                    "✨ **Novos Recursos:**",
                    "- Recurso",
                    "🐛 **Correções:**",
                    "- Correção",
                ],
                "proposal": [
                    "# [Projeto] - Proposta Técnica",
                    "## Introdução",
                    "Descreva brevemente o projeto, seus objetivos e o problema que visa resolver.",
                    "## Objetivos",
                    "- Objetivo 1: Descreva o primeiro objetivo do projeto.",
                    "- Objetivo 2: Descreva o segundo objetivo do projeto.",
                    "## Abordagem Técnica",
                    "Explique a solução técnica, incluindo ferramentas, frameworks e metodologias a serem usados.",
                    "### Principais Recursos",
                    "- Recurso 1: Descreva o primeiro recurso principal.",
                    "- Recurso 2: Descreva o segundo recurso principal.",
                    "## Benefícios",
                    "Destaque as vantagens da solução proposta, como eficiência, escalabilidade ou economia de custos.",
                    "## Plano de Implementação",
                    "Forneça uma linha do tempo ou etapas de alto nível para implementar a solução.",
                    "## Riscos e Mitigação",
                    "Identifique riscos potenciais e proponha estratégias para mitigá-los.",
                    "## Conclusão",
                    "Resuma a proposta e reitere seu valor.",
                ],
                "diagram": [
                    "# [Processo] - Fluxo",
                    "```mermaid",
                    "graph TD",
                    "  A[Início] --> B{Decisão?}",
                    "  B -->|Sim| C[Processo 1]",
                    "  B -->|Não| D[Processo 2]",
                    "  C --> E[Fim]",
                    "  D --> E",
                    "```",
                    "**Anotações:**",
                    "- **A**: Início do processo.",
                    "- **B**: Ponto de decisão.",
                    "- **C/D**: Caminhos alternativos.",
                    "- **E**: Fim do processo.",
                    "**Cores:**",
                    "- **Verde**: Caminho bem-sucedido (ex.: usuário logado).",
                    "- **Vermelho**: Caminho alternativo (ex.: usuário não logado).",
                    "**Legenda:**",
                    "- **Retângulo**: Etapa do processo.",
                    "- **Losango**: Ponto de decisão.",
                    "- **Círculo**: Início/Fim.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Técnico, conciso",
                    "elements": ["bullet_points"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Persuasivo, claro, estruturado",
                    "elements": ["cabeçalhos", "bullet_points", "tabelas"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visual, descritivo, modular",
                    "elements": ["mermaid", "cores", "anotações", "legenda"],
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
                "Usar terminologia técnica específica ao projeto.",
                "Destacar benefícios da solução proposta para persuadir partes interessadas.",
                "Incluir um plano de implementação claro e estruturado.",
                "Abordar riscos potenciais e estratégias de mitigação.",
                "Usar bullet points e cabeçalhos para melhorar legibilidade.",
                "Fornecer exemplos concretos ou estudos de caso para apoiar a proposta.",
                "Garantir que a proposta seja modular e facilmente atualizável.",
                "Incluir uma conclusão que resuma o valor da proposta.",
            ],
            "needs": "Persuasão para partes interessadas, clareza na abordagem técnica, documentação estruturada e insights acionáveis",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Tópico] - Guia",
                    "## [Seção]",
                    "- **Conceito:** Explicação com exemplos práticos e aplicações.",
                ],
                "quick_ref": [
                    "**[Tópico] - Referência Rápida:**",
                    "- [Ponto-chave]: Resumo breve e acionável com contexto prático claro.",
                ],
                "timeline": [
                    "# 🎥 [Aula] - Linha do Tempo",
                    "- **[MM:SS]** [Conceito-chave ou ação realizada]: [Explicação breve e clara com resultados ou ações, destacando aplicação no mundo real].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educacional, estruturado, com exemplos para melhor clareza e compreensão",
                    "elements": [
                        "subseções",
                        "bullet_points",
                        "exemplos",
                        "aplicações_práticas",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Conciso, prático, projetado para aprendizado e aplicação rápidos",
                    "elements": ["bullet_points", "resumos_claros"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Cronológico, focado em ações, claro com ênfase em aplicações reais",
                    "elements": [
                        "linha_do_tempo",
                        "passo_a_passo",
                        "sinais_visuais",
                        "contexto_real",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Fornecer explicações claras e acionáveis com exemplos para melhor compreensão.",
                "Manter informações concisas mas abrangentes, focando em aplicações práticas.",
                "Garantir alinhamento com objetivos de aprendizado e contexto.",
                "Enfatizar clareza e usabilidade, especialmente para casos de uso real.",
            ],
            "needs": "Facilitar estudo, referência rápida e rastreamento de vídeos com insights práticos.",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Projeto] - Crônica",
                    "- **[MM:SS]** Elemento destacado",
                ],
                "report": [
                    "**[Projeto] - Relatório Técnico:**",
                    "Parágrafo com detalhes-chave",
                ],
                "list": ["# [Projeto] - Detalhes", "- **Aspecto:** Descrição"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, visual",
                    "elements": ["linha_do_tempo"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Técnico, detalhado",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descritivo, organizado",
                    "elements": ["bullet_points"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Destacar inovação ou sustentabilidade",
                "Incluir dados técnicos, se aplicável",
                "Ser visualmente atraente",
            ],
            "needs": "Documentação técnica, apresentação atraente, rastreamento de vídeos",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Período] - Relatório Financeiro",
                    "- **Indicador**: [Valor]",
                ],
                "table": [
                    "## [Período] - Resumo Financeiro",
                    "| **Indicador** | **Valor** |",
                ],
                "executive": [
                    "**[Período] - Resumo Executivo:**",
                    "Parágrafo breve e impactante destacando insights-chave.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analítico, formal",
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
                    "tone": "Visual, conciso",
                    "elements": ["tabela"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Direto, executivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Garantir clareza e concisão na apresentação de números-chave.",
                "Evitar ambiguidade na apresentação de dados.",
                "Apoiar a tomada de decisão com insights acionáveis.",
                "Títulos de tabelas devem ser formatados sem espaços extras antes ou depois dos asteriscos.",
            ],
            "needs": "Dados acionáveis, síntese visual clara e resumos executivos focados em impacto.",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Destino] - Crônica",
                    "- **[MM:SS]** Iniciativa",
                    "- **[MM:SS]** Marco principal",
                ],
                "report": [
                    "**[Destino] - Políticas:**",
                    "Parágrafo formal com ênfase nos objetivos do destino e impacto no turismo",
                ],
                "list": [
                    "# [Destino] - Iniciativas",
                    "- **Área:** Detalhe (considere adicionar cultura local ou atrações)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, engajante, imersivo",
                    "elements": ["linha_do_tempo", "storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formal, informativo, objetivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descritivo, claro, informativo",
                    "elements": ["bullet_points", "fatos_concisos"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Destacar sustentabilidade, significado cultural e apelo turístico",
                "Incluir informações práticas de viagem (ex.: melhor época para visitar, atrações locais, contatos essenciais)",
                "Focar em descrições claras, concisas e precisas de políticas e iniciativas",
                "Evitar exageros, manter-se realista e informativo",
            ],
            "needs": "Promoção engajante com destaques informativos, apresentação clara de políticas e detalhes práticos focados no turista",
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "O conteúdo descreve medidas econômicas anunciadas em 08 de março de 2025, incluindo reduções de impostos e linhas de crédito."
        },
        "journalism": {
            "chronicle": (
                "# Evento da Apple Ao Vivo\n"
                "- **[00:03:00]** Tim Cook apresenta a Apple Intelligence, um novo sistema de IA integrado aos dispositivos da Apple.\n"
                "- **[00:05:11]** Apresentação do Apple Watch Series 10, destacando sua tela maior e design mais fino.\n"
                "- **[00:07:03]** Demonstração da nova tela OLED, 40% mais brilhante em ângulos oblíquos.\n"
                "- **[00:09:06]** Anúncio de que o Series 10 é 10% mais fino que o Series 9, com apenas 9,7 mm de espessura.\n"
                "- **[00:10:19]** Introdução do carregamento rápido: 80% da bateria em 30 minutos.\n"
                "- **[00:11:03]** Revelação do acabamento em titânio polido, 20% mais leve que o aço inoxidável.\n"
                "- **[00:12:00]** Ênfase na sustentabilidade: 95% de titânio reciclado e 100% de energia renovável na fabricação.\n"
                "- **[00:13:50]** Novos recursos de saúde: detecção de apneia do sono e monitoramento de temperatura corporal para rastreamento de ovulação.\n"
                "- **[00:15:19]** Discussão sobre a importância da detecção de apneia do sono, com 80% dos casos não diagnosticados globalmente."
            ),
            "news_wire": (
                "[08 de março de 2025] - Capital - Presidente anuncia medidas econômicas.\n"
                "### Detalhes Principais\n"
                "- Redução de impostos para famílias de classe média.\n"
                "- Aumento de gastos em projetos de infraestrutura.\n"
                "### Contexto\n"
                "- As medidas visam impulsionar o crescimento econômico em meio à inflação crescente.\n"
                "### Estatísticas\n"
                "- Previsão de crescimento do PIB: 2,5% em 2025.\n"
                "- Taxa de desemprego: 5,8% (abaixo dos 6,3% do ano anterior).\n"
                "### Impacto\n"
                "- Curto prazo: Alívio imediato para famílias de classe média.\n"
                "- Longo prazo: Espera-se que estimule o crescimento econômico e crie empregos."
            ),
            "analysis": (
                "## Reforma Tributária em Profundidade\n"
                "### Visão Geral\n"
                "- A recente reforma tributária visa reduzir a carga tributária sobre a classe média e aumentar gastos em projetos de infraestrutura para estimular o crescimento econômico.\n"
                "### Aspectos Principais\n"
                "- **Redução de Impostos**: Redução de 10% nos impostos para famílias de classe média, com expectativa de aumento da renda disponível e do consumo.\n"
                "- **Investimento em Infraestrutura**: Aumento de gastos em projetos de infraestrutura, com objetivo de criar empregos e melhorar serviços públicos.\n"
                "### Implicações\n"
                "- **Curto Prazo**: Alívio imediato para famílias de classe média, com potencial aumento no consumo e na atividade econômica.\n"
                "- **Longo Prazo**: Espera-se que estimule o crescimento econômico, crie empregos e melhore a infraestrutura pública, levando a uma economia mais robusta.\n"
                "### Opiniões de Especialistas\n"
                "- 'Esta reforma tributária é um passo significativo para reduzir a desigualdade de renda e estimular o crescimento econômico', diz Dra. Jane Doe, economista da Universidade de Harvard.\n"
                "### Conclusão\n"
                "- A reforma tributária representa uma abordagem equilibrada para lidar com desafios econômicos, com benefícios potenciais tanto para indivíduos quanto para a economia em geral. No entanto, seu sucesso a longo prazo dependerá de implementação e monitoramento eficazes."
            ),
        },
        "marketing": {
            "highlights": "# ✨ Lançamento EcoLife - Destaques\n🎯 **Público-alvo:** Jovens.\n📈 **Vendas:** +15%.",
            "storytelling": (
                "## EcoLife - Uma História: Uma Jornada para a Sustentabilidade\n"
                "### Introdução\n"
                "- Em uma cidade movimentada, uma jovem chamada Maria se sentia sobrecarregada pelo ritmo acelerado da vida e pelos desafios ambientais ao seu redor.\n"
                "### Narrativa Principal\n"
                "- Um dia, Maria descobriu a EcoLife, uma marca dedicada à vida sustentável. Ela começou a usar seus produtos ecológicos e notou uma mudança significativa em seu estilo de vida.\n"
                "- Apesar do ceticismo inicial de seus amigos, o compromisso de Maria com a sustentabilidade os inspirou a se juntarem a ela nessa jornada.\n"
                "### Impacto Emocional\n"
                "- A história de Maria é um testemunho de como pequenas mudanças podem ter um grande impacto, tanto pessoal quanto ambientalmente.\n"
                "### Chamada para Ação\n"
                "- Junte-se a Maria e milhares de outros na mudança. Comece sua jornada sustentável com a EcoLife hoje!"
            ),
            "report": (
                "## EcoLife - Resultados\n"
                "### Visão Geral\n"
                "- A campanha EcoLife teve como objetivo aumentar a conscientização da marca e as vendas entre jovens adultos, promovendo a vida sustentável.\n"
                "### Métricas Principais\n"
                "| **Métrica**       | **Meta** | **Realizado** | **Variação** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Aumento de Vendas   | +15%     | +18%       | +3%          |\n"
                "| Alcance nas Redes Sociais | 1M      | 1,2M       | +200K        |\n"
                "### Análise\n"
                "- A campanha excedeu a meta de vendas em 3%, impulsionada pelo forte engajamento nas redes sociais e parcerias com influenciadores.\n"
                "- O alcance nas redes sociais superou as expectativas, indicando estratégia de conteúdo eficaz e direcionamento preciso ao público.\n"
                "### Recomendações\n"
                "- Continuar aproveitando parcerias com influenciadores para manter o momentum.\n"
                "- Expandir a estratégia de conteúdo para incluir mais posts educativos sobre sustentabilidade.\n"
                "### Conclusão\n"
                "- A campanha EcoLife aumentou com sucesso a conscientização da marca e as vendas, estabelecendo uma base sólida para iniciativas futuras."
            ),
        },
        "health": {
            "report": "**Tratamento X - Relatório Clínico:** Ensaios clínicos mostram redução de 70% nos sintomas após 8 semanas de tratamento consistente.",
            "summary": "# 🩺 Tratamento X - Resumo\n📈 **Eficácia:** 70%.\n| Semana | Progresso |\n| 8    | 70%     |",
            "case": "**Paciente A - Caso Clínico:** Homem de 62 anos apresenta melhora após 2 semanas.",
        },
        "technology": {
            "changelog": "# v3.0 - Atualização\n✨ **Novos Recursos:**\n- OCR.\n🐛 **Correções:**\n- Exportação.",
            "proposal": """
                    # Projeto X - Proposta Técnica

                    ## Introdução
                    Esta proposta descreve a abordagem técnica para implementar um sistema automatizado de integração de API para melhorar a eficiência do processamento de dados.

                    ## Objetivos
                    - Objetivo 1: Reduzir a entrada manual de dados em 50%.
                    - Objetivo 2: Aumentar a velocidade de processamento de dados em 30%.

                    ## Abordagem Técnica
                    A solução usará Python com Flask para desenvolvimento de API, Docker para conteinerização e Kubernetes para orquestração.

                    ### Principais Recursos
                    - Recurso 1: Ingestão automatizada de dados de múltiplas fontes.
                    - Recurso 2: Validação e tratamento de erros em tempo real.

                    ## Benefícios
                    - **Eficiência**: Reduz esforço manual e acelera o processamento.
                    - **Escalabilidade**: Escala facilmente para lidar com volumes crescentes.
                    - **Economia**: Reduz custos operacionais automatizando tarefas repetitivas.

                    ## Plano de Implementação
                    1. **Fase 1**: Desenvolvimento e teste da API (2 semanas).
                    2. **Fase 2**: Implantação e integração com sistemas existentes (3 semanas).
                    3. **Fase 3**: Monitoramento e otimização (1 semana).

                    ## Riscos e Mitigação
                    - **Risco 1**: Tempo de inatividade da API durante a implantação.
                    - **Mitigação**: Implementar estratégia de atualização progressiva.
                    - **Risco 2**: Erros de validação de dados.
                    - **Mitigação**: Usar testes automatizados para detectar erros antecipadamente.

                    ## Conclusão
                    Esta proposta apresenta uma solução robusta para automatizar o processamento de dados, oferecendo ganhos significativos de eficiência e economia.
                """,
            "diagram": "# Autenticação do Usuário - Fluxo\n```mermaid\ngraph TD\n  A[Início] --> B{Usuário logado?}\n  B -->|Sim| C[Mostrar Dashboard]\n  B -->|Não| D[Redirecionar para Login]\n  C --> E[Fim]\n  D --> E\n```\n**Anotações:**\n- **A**: Início do processo.\n- **B**: Ponto de decisão.\n- **C/D**: Caminhos alternativos.\n- **E**: Fim do processo.\n**Cores:**\n- **Verde**: Caminho bem-sucedido (usuário logado).\n- **Vermelho**: Caminho alternativo (usuário não logado).\n**Legenda:**\n- **Retângulo**: Etapa do processo.\n- **Losango**: Ponto de decisão.\n- **Círculo**: Início/Fim.",
        },
        "education": {
            "guide": "# 📚 [Tópico] - Guia\n## [Seção]\n- **Conceito:** Explicação com exemplos práticos e uso.",
            "quick_ref": "**[Tópico] - Referência Rápida:**\n- [Ponto-chave]: Resumo breve e acionável.",
            "timeline": "# 🎥 [Aula] - Linha do Tempo\n- **[MM:SS]** [Conceito-chave ou ação realizada]: [Explicação breve e clara com resultados ou ações realizadas].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Torre Verde - Crônica\n- **[01:15]** Materiais sustentáveis.",
            "report": "**Torre Verde - Relatório Técnico:** O design utiliza energia renovável.",
            "list": "# Torre Verde - Detalhes\n- **Materiais:** Reciclados.\n- **Energia:** Solar.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Relatório Financeiro\n- **Receita:** Crescimento de 5% impulsionado por avanços tecnológicos e expansão de mercado.",
            "table": "## Q1 2025 - Resumo Financeiro\n| **Indicador** | **Valor** |\n|---------------|-----------|\n| Receita       | +5%       |",
            "executive": "**Q1 2025 - Resumo Executivo:** Crescimento de 5% impulsionado por avanços tecnológicos e expansão estratégica de mercado, fortalecendo a perspectiva financeira.",
        },
        "tourism": {
            "chronicle": "# 🌍 Praia Azul - Crônica\n- **[01:00]** Iniciativas de ecoturismo ajudam a reduzir resíduos.\n- **[05:00]** Grande desenvolvimento de hotel eco-friendly.",
            "report": "**Praia Azul - Políticas:** Promove sustentabilidade reduzindo resíduos e apoiando iniciativas de ecoturismo. O governo local visa neutralidade de carbono até 2030, com foco em energia renovável e redução de resíduos.",
            "list": "# Praia Azul - Iniciativas\n- **Ecologia:** Redução do uso de plástico, aumento de iniciativas de reciclagem.\n- **Atrativo Turístico:** Oferece atividades durante todo o ano, com alta temporada de maio a setembro.",
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
            f"**Objetivo:** Criar conteúdo no formato {output_format.value.upper()} otimizado para {category.value.title()}",
            f"**Estilo:** {style.value.title()} ({style_info['tone']})",
            f"**Requisitos essenciais:** {spec.get('needs', 'adaptação ao contexto')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "Evite frases genéricas como 'O texto agora está livre de repetições e permanece claro e coerente.' Concentre-se em fornecer feedback concreto e específico.",
            "Não inclua frases como 'Aqui está o texto revisado, removendo redundâncias e repetições, mantendo todos os detalhes e a estrutura original.'",
            "Nunca inclua a tag ```markdown. Se usar blocos de código, eles devem ser não especificados ou em uma linguagem diferente de Markdown.",
            f"A partir de agora, responda apenas em português, independentemente do idioma original da pergunta.",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- Resuma o documento de forma completa, destacando os principais temas, pontos-chave e o objetivo geral em aproximadamente {word_limit} palavras."

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            Contexto do texto anterior: {previous_context}\n
            Instruções: Forneça um resumo detalhado do texto a seguir, integrando novas informações de forma coerente com o contexto anterior.
            Inclua exemplos, explicações e quaisquer detalhes que facilitem o estudo do tema.
            Organize o resumo em seções ou pontos principais para facilitar a compreensão."""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""Você é um editor especialista em melhorar textos removendo redundâncias.
            Revise o resumo a seguir e remova apenas informações repetidas ou redundantes,
            como textos, frases ou ideias repetidas.
            Não simplifique, reduza ou resuma o conteúdo de forma alguma; mantenha todos os detalhes, dados e elementos importantes como estão.
            Certifique-se de que o texto final seja claro, coerente e bem estruturado, sem alterar sua estrutura ou significado original."""
        return prompt
