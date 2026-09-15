from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


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
                "Resumir o conteúdo da fonte: temas, definições, factos, procedimentos e exemplos importantes",
                "Escrever na terceira pessoa. Primeira pessoa proibida (aprendi, preciso esclarecer, ajudar-me-ia)",
                "Não inventar perguntas, exercícios, dúvidas nem secções de 'pontos a esclarecer' / 'o que aprendi'",
                "Não transformar o documento num diário de aprendizagem nem em deveres de estudante",
                "Preservar o título original se estiver presente, sem modificações, com a redação e formato exatos (ex.: # Título, ## Subtítulo)",
                "Usar cabeçalhos apenas se o documento original tiver secções reais equivalentes",
                "Manter exemplos ou conceitos-chave no formato original (ex.: listas, código, itálico)",
                "Não acrescentar conhecimento externo nem afirmações que a fonte não sustente",
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
        "requirements": {
            "structures": {
                "elicitation": [
                    "Requisitos para [Projeto/Nome] - Elicitação",
                    "Contexto",
                    "- Reunião: [Data, participantes, objetivo].",
                    "- Âmbito: [Propósito ou resultado esperado].",
                    "Requisitos funcionais",
                    "- FR-[ID]: [Descrição clara]. (Prioridade: [Alta/Média/Baixa], Justificação: [Motivo breve]).",
                    "Requisitos não funcionais",
                    "- NFR-[ID]: [Descrição, ex. qualidade, prazos]. (Prioridade: [Alta/Média/Baixa], Justificação: [Motivo]).",
                    "Dependências e restrições",
                    "- Dependência: [Relação com outros requisitos/recursos].",
                    "- Restrição: [Limitações, ex. orçamento, tempo].",
                    "Perguntas em aberto",
                    "- [Pergunta a esclarecer]",
                    "Marcas temporais (se aplicável)",
                    "- [MM:SS]: [Citação breve da fonte].",
                    "Critérios de priorização",
                    "- Alta: Crítico para o sucesso ou urgência.",
                    "- Média: Importante, mas não essencial.",
                    "- Baixa: Desejável, adiável.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Claro, objetivo, adaptável",
                    "elements": ["bullet_points", "IDs", "priorities"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Extrair requisitos diretamente, sem interpretações.",
                "Usar IDs (FR-01, NFR-01) para rastreabilidade.",
                "Priorizar com justificação (impacto/urgência).",
                "Usar linguagem clara focada no 'o quê' é necessário.",
                "Listar ambiguidades em 'Perguntas em aberto'.",
                "Marcas temporais apenas para requisitos-chave.",
            ],
            "needs": "Captura clara de requisitos para qualquer projeto, facilitando planeamento e comunicação.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Tópico] - Guia",
                    "## [Secção]",
                    "- **Conceito:** Definição, princípio, relação, processo, mecanismo, classificação ou evidência relevante.",
                ],
                "formula_reference": [
                    "# 🔬 [Tópico] - Referência de fórmulas",
                    "## Fórmulas principais",
                    "| Fórmula | Significado | Variáveis | Unidades | Condições |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Tópico] - Derivação",
                    "## Ponto de partida",
                    "- [Definição, princípio, equação, observação, dado ou condição inicial presente na fonte.]",
                    "## Desenvolvimento",
                    "1. [Primeiro passo ou raciocínio presente na fonte.]",
                    "2. [Transformação, relação, procedimento ou raciocínio presente na fonte.]",
                    "## Resultado",
                    "- **Resultado:** [Resultado ou conclusão obtido na fonte.]",
                ],
                "quick_ref": [
                    "**[Tópico] - Referência rápida:**",
                    "- **Conceito:** Definição breve.",
                    "- **Princípio/Lei/Teoria:** Relação fundamental.",
                    "- **Processo/Relação:** Descrição essencial.",
                    "- **Dado/Fórmula:** Informação quantitativa relevante.",
                    "- **Condição:** Aplicabilidade ou limitação.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educativo, rigoroso e estruturado",
                    "elements": [
                        "conceitos",
                        "princípios",
                        "leis",
                        "teorias",
                        "modelos",
                        "processos",
                        "mecanismos",
                        "estruturas",
                        "relações",
                        "dados",
                        "fórmulas",
                        "exemplos",
                        "evidências",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Técnico, compacto e preciso, orientado à aplicação correta e à referência",
                    "elements": [
                        "fórmulas",
                        "variáveis",
                        "unidades",
                        "relações",
                        "condições",
                        "tabelas",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formal, lógico e rigoroso, preservando o raciocínio realmente suportado pela fonte",
                    "elements": [
                        "equações",
                        "procedimentos",
                        "deduções",
                        "sequências",
                        "raciocínios",
                        "pressupostos",
                        "condições",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Conciso, técnico e prático, concebido para revisão rápida sem perder precisão científica",
                    "elements": [
                        "conceitos-chave",
                        "princípios",
                        "leis",
                        "teorias",
                        "processos",
                        "fórmulas",
                        "dados",
                        "condições",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
            },
            "rules": [
                "Utilizar exclusivamente a informação presente na fonte.",
                "Não introduzir conhecimento externo mesmo que seja cientificamente correto, conhecido, óbvio ou útil para completar a explicação.",
                "Não inventar, completar, corrigir nem reinterpretar conteúdo que não seja suportado pela fonte.",
                "As estruturas são apenas um guia de organização e não obrigam a criar conteúdo para completar secções.",
                "Não incluir uma secção quando a fonte não contém informação suficiente para a justificar.",
                "Preservar definições, princípios, leis, teorias, hipóteses, modelos, processos, mecanismos, classificações, relações, dados, fórmulas, variáveis, unidades, evidências e condições relevantes presentes na fonte.",
                "Manter o significado original de termos científicos, símbolos, variáveis, grandezas, relações, processos e mecanismos.",
                "Não transformar uma hipótese, modelo, observação, correlação, associação ou resultado experimental num facto, lei ou relação causal não estabelecida pela fonte.",
                "Não generalizar resultados, mecanismos ou conclusões para além das condições, população, sistema, escala ou contexto indicados na fonte.",
                "Preservar exceções, limites, pressupostos, restrições, incertezas e condições de validade quando afetam a interpretação.",
                "Quando existem dados quantitativos, conservar valores, unidades, relações, ordens de grandeza e precisão relevante.",
                "Quando existem fórmulas ou relações matemáticas, preservar sinais, expoentes, índices, operadores, variáveis, unidades, aproximações e condições de validade.",
                "Não realizar conversões, cálculos, transformações algébricas ou inferências quantitativas adicionais que não estejam presentes ou inequivocamente suportadas pela fonte.",
                "Quando existe uma derivação, demonstração, procedimento, experiência ou raciocínio sequencial, conservar apenas os passos essenciais realmente suportados pela fonte.",
                "Não adicionar passos intermédios, mecanismos, causas ou explicações que a fonte não apresenta ou não permite estabelecer inequivocamente.",
                "Conservar relações temporais, causais, funcionais, estruturais e hierárquicas quando forem relevantes para compreender corretamente o conteúdo.",
                "Não confundir correlação com causalidade nem associação com mecanismo.",
                "Não eliminar informação cuja ausência possa alterar o significado, a interpretação, o resultado ou o âmbito de aplicação do conteúdo.",
                "Eliminar redundâncias e formulações repetitivas sem eliminar informação científica necessária.",
                "Reduzir a explicação, não o significado.",
                "Em caso de conflito, priorizar nesta ordem: fidelidade à fonte, exactidão científica, preservação do significado e das condições, clareza, estrutura e finalmente concisão.",
                "O objetivo é representar de forma compacta e precisa o conhecimento contido na fonte, não fornecer uma explicação geral do tópico com base em conhecimento externo.",
            ],
            "needs": (
                "Máxima fidelidade e precisão científica, preservando conceitos, "
                "processos, mecanismos, relações, dados, fórmulas, evidências, "
                "condições, limites e raciocínio essencial presentes na fonte, "
                "sem introduzir conhecimento externo nem completar informação ausente."
            ),
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
        "requirements": {
            "elicitation": """Requisitos para Evento Corporativo 2025 - Elicitação
                Contexto
                - Reunião: 20/09/2025, equipa de marketing ABC, planear evento para 500 participantes.
                - Âmbito: Evento de networking e lançamento de produto, dentro do orçamento.
                Requisitos funcionais
                - FR-01: Local para 500 pessoas com stands. (Prioridade: Alta, Justificação: Crítico para o evento).
                - FR-02: Registo online com email. (Prioridade: Média, Justificação: Facilita a logística).
                - FR-03: Keynote com orador convidado. (Prioridade: Alta, Justificação: Central para o evento).
                Requisitos não funcionais
                - NFR-01: Cumprir normas de segurança e acessibilidade. (Prioridade: Alta, Justificação: Obrigação legal).
                - NFR-02: Planeamento em 2 meses. (Prioridade: Alta, Justificação: Prazo fixo).
                Dependências e restrições
                - Dependência: O local requer aprovação orçamental.
                - Restrição: Orçamento de 30.000 $.
                Perguntas em aberto
                - É necessário streaming do evento?
                Marcas temporais
                - [03:15]: 'Local grande para 500 pessoas com stands'.
                - [08:20]: 'A keynote tornará o evento memorável'.
                Critérios de priorização
                - Alta: Crítico para o sucesso ou urgência.
                - Média: Importante, mas não essencial.
                - Baixa: Desejável, adiável."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Tópico] - Guia\n"
                "## [Secção presente na fonte]\n"
                "- **Conceito:** Definição ou explicação condensada a partir do conteúdo da fonte.\n"
                "## [Outra secção presente na fonte]\n"
                "- **Processo:** Sequência ou mecanismo descrito na fonte.\n"
            ),
            "formula_reference": (
                "# 🔬 [Tópico] - Referência de fórmulas\n"
                "## Fórmulas principais\n"
                "| Fórmula | Significado | Variáveis | Unidades | Condições |\n"
                "|---|---|---|---|---|\n"
                "| [Fórmula presente na fonte] | [Significado indicado na fonte] | [Variáveis definidas na fonte] | [Unidades indicadas] | [Condições indicadas] |\n"
            ),
            "derivation": (
                "# 🔬 [Tópico] - Derivação\n"
                "## Ponto de partida\n"
                "- [Definição, equação, dado, observação ou condição inicial presente na fonte.]\n"
                "## Desenvolvimento\n"
                "1. [Primeiro passo ou transformação explicitamente mostrada na fonte.]\n"
                "2. [Segundo passo, relação ou raciocínio explicitamente mostrado na fonte.]\n"
                "## Resultado\n"
                "- **Resultado:** [Resultado ou conclusão que a fonte obtém explicitamente.]\n"
            ),
            "quick_ref": (
                "**[Tópico] - Referência rápida:**\n"
                "- **Conceito:** [Definição presente na fonte.]\n"
                "- **Princípio/Lei/Teoria:** [Apenas se aparecer na fonte.]\n"
                "- **Processo/Relação:** [Processo ou relação descrita na fonte.]\n"
                "- **Dado/Fórmula:** [Dado ou fórmula presente na fonte.]\n"
                "- **Condição:** [Condição ou limitação indicada na fonte.]\n"
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
            f"**Objetivo:** Criar conteúdo no formato {output_format.value.upper()} otimizado para {category.value.title()}",
            f"**Estilo:** {style.value.title()} ({style_info['tone']})",
            f"**Requisitos essenciais:** {spec.get('needs', 'adaptação ao contexto')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "Não use a primeira pessoa nem finja ser um estudante a tomar notas.",
            "Não invente perguntas, dúvidas, conclusões ou dados ausentes da fonte.",
            "A saída É o resumo. Nunca um menu de ajuda, uma capa ou perguntas ao leitor.",
            "Nunca inclua a etiqueta ```markdown em circunstância alguma. Se usar blocos de código, devem ser não especificados ou numa linguagem diferente de Markdown.",
            "Evite frases genéricas como «O texto está agora livre de repetições e permanece claro e coerente.» Concentre-se em feedback concreto e específico.",
            "Não inclua frases como «Aqui está o texto revisto, removendo redundâncias e repetições, preservando todos os detalhes e a estrutura original.»",
            "A partir de agora, responda apenas em português, independentemente da língua da pergunta original.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Instruções: Extrair os factos distintivos deste fragmento.
            IMPORTANTE: Está a processar APENAS UMA PARTE (chunk) de um documento muito maior.
            - Escreva títulos, listas e prosa em português. Outras línguas apenas no código ou em nomes próprios.
            - NÃO gere uma Introdução global nem uma Conclusão global.
            - NÃO reinicie hierarquias de numeração (ex. ## 1. Introdução).
            - NÃO gere um documento autónomo.
            - Extraia DESTE fragmento segundo o nível de resumo: definições e factos centrais sempre;
              exemplos, números e anedotas apenas na densidade da instrução de comprimento.
            - O nível de resumo controla a densidade de detalhe, não se um tema maior presente aqui pode ser omitido.
            - PRIORIDADE CRÍTICA: preservar a natureza da linguagem ou do sistema (ex. interpretado vs compilado,
              cliente vs servidor, estático vs dinâmico) com o mesmo grau de certeza da fonte.
            - Se o texto contrasta páginas estáticas e dinâmicas, defina AMBAS.
            - Se afirma que algo é multiplataforma apenas em teoria, mantenha essa reserva (não a transforme em facto absoluto).
            - Conserve tabelas ou listas comparativas ponto a ponto (não as reduza a «há diferenças»).
            - Preserve nomes de ferramentas, caminhos de ficheiros, constantes numéricas, fórmulas e citações de código.
            - Preserve condições, exceções e reservas (teoricamente, pode, só se, não implica…).
            - Preserve sintaxe, fórmulas e exemplos exatamente como aparecem neste fragmento.
            - Distinga um índice ou sumário do conteúdo realmente desenvolvido aqui.
            - Se este fragmento é um índice, descreva-o como índice (quais unidades existem) e NÃO extraia essas unidades como se este fragmento as desenvolvesse.
            - Não trate lições nomeadas no índice como explicadas se este fragmento não as desenvolver.
            - Nomeie apenas ferramentas, bibliotecas, APIs, editores e URLs que apareçam literalmente neste fragmento.
            - Não use a primeira pessoa. Não invente perguntas nem um diário de aprendizagem.
            - A saída É o extrato. Nunca um menu de ajuda, capa de livro, perguntas ao leitor, ou «do que precisa?».
            - Isto é um extrato denso para síntese posterior, não um minúsculo recapitulativo autónomo.
            - Use o orçamento de saída disponível para factos distintivos; não pare cedo se restarem detalhes importantes.
            - Prepare o conteúdo para que seja útil a uma síntese global posterior.
            - NÃO inclua qualquer conhecimento externo nem informação ausente do texto.
            - NÃO gere um índice ou sumário.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "É um editor especialista. A sua tarefa é INTEGRAR os blocos de texto fornecidos "
            "num texto unificado.\n\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "- ZERO PREENCHIMENTO: NÃO adicione frases de transição desnecessárias, introduções genéricas ou conclusões. "
            "Vá direto ao ponto.\n"
            "- DEDUPLICAÇÃO ESTRITA: Elimine qualquer conceito, ideia ou argumento repetido entre blocos.\n"
            "- ESTRUTURA ÚNICA: Consolide o conteúdo sob uma única hierarquia. Remova cabeçalhos redundantes, "
            "mas CONSERVE tópicos de secção distintos que representem partes diferentes da fonte.\n"
            "- FIDELIDADE ESTRITA: Mantenha fidelidade absoluta. NÃO invente factos nem adicione conhecimento externo.\n"
            "- COBERTURA PRIMEIRO: Cada bloco fonte com conteúdo substantivo deve ser representado. "
            "O nível de resumo controla a densidade de detalhe, não se um tema maior pode desaparecer.\n"
            "- NÃO COMPRIMA ABAIXO DO OBJETIVO: Una e remova duplicados. "
            "Se a instrução de comprimento pedir mais palavras do que a entrada tem, "
            "conserve TODO o conteúdo não redundante restante; não encurte mais e não invente preenchimento.\n"
            "- RESPEITE A INSTRUÇÃO DE COMPRIMENTO: Se for fornecida uma instrução de comprimento, siga-a. "
            "Ficar muito abaixo do objetivo eliminando temas maiores é um erro.\n"
            "- A saída É o resumo unificado. Nunca um assistente, menu de opções, blurb de capa, "
            "perguntas ao leitor, ou «do que precisa?».\n"
            "- PROIBIDO: primeira pessoa, diários de aprendizagem, perguntas inventadas, "
            "secções «o que aprendi» ou «pontos a esclarecer».\n"
            "- O índice não é conteúdo desenvolvido: não resuma unidades, exemplos ou APIs "
            "que só aparecem no índice se o corpo do documento não as explicar.\n"
            "- Nomeie apenas ferramentas, bibliotecas, APIs, editores e URLs que apareçam literalmente nos blocos.\n"
            "- Não mencione «bloco 1» nem etiquetas internas do pipeline.\n"
            "- Não invente ISBN, títulos de livros ou comparações Java/JVM que a fonte não faça.\n"
            "- LÍNGUA: escreva o resumo INTEIRO em português. Traduza blocos que estejam em espanhol ou noutra língua. "
            "Outras línguas apenas em citações, código ou nomes próprios.\n"
            "- Um bloco que diga «APENAS ÍNDICE» ou liste unidades/páginas sem as explicar "
            "é APENAS um índice: DESCARTE-O. Não o mencione no resumo final. "
            "Não liste unidades do índice. Dedique o resumo ao conteúdo realmente desenvolvido.\n"
            "- PRESERVAR SEM DILUIR: nomes de ferramentas, ficheiros, constantes numéricas, "
            "comparações ponto a ponto e reservas de certeza (teoricamente, pode, não implica, só se).\n"
            "- SEM padding de tokens: não clone secções, não parafraseie o mesmo bloco várias vezes, "
            "não invente ferramentas, APIs, editores ou runtimes ausentes da fonte.\n"
            "- Se um tema já está escrito, não o escreva de novo. "
            "- Ordem de prioridade: factualidade, cobertura, exaustividade, coerência, estrutura e depois concisão. "
            "A concisão não deve destruir a cobertura."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Estilos e tons disponíveis:**"

    def get_semantic_profile_title(self) -> str:
        return "**Perfil semântico (informação a preservar):**"

    def get_length_instruction_title(self) -> str:
        return "**Instrução de comprimento:**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Expresse a tese principal, as conclusões essenciais e os conceitos centrais "
                "de forma altamente condensada. Conserve cada pilar maior. "
                "Omita exemplos secundários, anedotas, dicas de leitura e nuances menores."
            ),
            SummaryLevel.CONCISE: (
                "Preserve os argumentos principais, as justificações essenciais e a estrutura temática primária. "
                "Seja direto; reduza a elaboração secundária sem eliminar secções importantes."
            ),
            SummaryLevel.MODERATE: (
                "Preserve argumentos, justificações, evidência relevante, exemplos representativos "
                "e taxonomias importantes."
            ),
            SummaryLevel.DETAILED: (
                "Preserve subtópicos, metodologia, evidência, implicações, taxonomias completas "
                "e relações entre conceitos."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Preserve detalhes incluindo exceções, nuances, casos particulares, contexto "
                "e particularidades formalmente relevantes. "
                "Em tutoriais técnicos: não omita definições da natureza do sistema "
                "(interpretado/compilado, cliente/servidor), tabelas comparativas, nomes de ferramentas, "
                "ficheiros de exemplo, constantes numéricas ou condições dos exemplos."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "COMPRIMENTO / DENSIDADE: Produza um resumo visivelmente mais curto do que moderate. "
                "Conserve a tese, os pilares e as definições centrais. "
                "Omita exemplos secundários, anedotas, recomendações de leitura e qualquer nota sobre um índice. "
                "No máximo um exemplo curto por pilar, e só se esclarecer a definição. "
                "Ser mais curto do que moderate é correto se os temas maiores sobreviverem. "
                "Não elimine um pilar; não copie cada exemplo do nível moderate. "
                "Prefira formulação densa à enumeração de cada caso."
            ),
            SummaryLevel.CONCISE: (
                "COMPRIMENTO / DENSIDADE: Produza um resumo breve, mais longo do que very_concise e mais curto do que moderate. "
                "Prefira redação compacta à eliminação de secções importantes. "
                "Um exemplo representativo por tema maior basta."
            ),
            SummaryLevel.MODERATE: (
                "COMPRIMENTO / DENSIDADE: Produza um resumo de comprimento médio, visivelmente mais longo do que very_concise "
                "e mais curto do que very_detailed. "
                "Conserve um exemplo representativo por conceito maior, com números ou nomes distintivos da fonte. "
                "Não copie cada caso ou anedota."
            ),
            SummaryLevel.DETAILED: (
                "COMPRIMENTO / DENSIDADE: Produza um resumo detalhado, mais longo do que moderate. "
                "Use o espaço necessário para subtópicos, evidência e vários exemplos da fonte."
            ),
            SummaryLevel.VERY_DETAILED: (
                "COMPRIMENTO / DENSIDADE: Produza um resumo visivelmente mais longo do que moderate. "
                "Conserve cada exemplo, número, nome, exceção e condição desenvolvidos no corpo da fonte. "
                "Não comprima esses factos distintivos. "
                "Nunca preencha repetindo parágrafos, clonando secções, citando o índice "
                "ou adicionando conhecimento externo."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "GARANTIA DE COBERTURA (aplica-se a todos os níveis de resumo): "
            "Ideias principais, conceitos essenciais, tópicos de secções importantes e termos "
            "centrais DEVEM sobreviver. O nível de resumo controla apenas a densidade de detalhe "
            "e a elaboração secundária. Nunca autoriza eliminar uma secção maior "
            "nem a tese central do documento."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Lista de cobertura (apenas se a secção estiver DESENVOLVIDA nos blocos, "
            "não se aparecer apenas num índice):**\n"
            f"{lines}\n"
            "Não invente o conteúdo de um cabeçalho que os blocos não expliquem."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Instrução de encerramento:** "
            "Cubra os factos distintivos DESTE fragmento com a densidade da instrução de comprimento. "
            "Use o orçamento de saída disponível para esses factos; não pare cedo se restarem detalhes importantes. "
            "Não repita parágrafos para preencher. "
            "Termine sempre numa frase completa."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "entradas do índice"
        return (
            "APENAS ÍNDICE — este fragmento é um índice, não lições desenvolvidas. "
            f"Lista: {listed}. "
            "Não apresente estas entradas como se o documento as tivesse explicado aqui."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "É um especialista em síntese documental. Resuma o documento completo "
            "numa única passagem. Preserve a estrutura conceptual importante "
            "(títulos/secções relevantes), ideias principais, definições, "
            "procedimentos, exemplos e termos centrais. "
            "Emita Markdown limpo. Não invente conteúdo. "
            "Não escreva um diário de aprendizagem nem listas de perguntas.\n"
            "O índice ou sumário NÃO É conteúdo desenvolvido: "
            "mencione-o apenas como índice; não apresente unidades ou exemplos do índice "
            "como se o corpo do documento os tivesse explicado.\n"
            "PRIORIDADE CRÍTICA: preservar a natureza da linguagem (interpretado/compilado), "
            "o ambiente de execução (cliente/servidor), o contraste estático/dinâmico, "
            "tabelas comparativas, nomes de ferramentas, ficheiros, constantes numéricas "
            "e reservas de certeza (teoricamente, pode, não implica, só se).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "É um editor de formatação. A sua única tarefa é aplicar formatação Markdown "
            "ao texto fornecido.\n\n"
            "NÃO resuma, encurte, expanda, reinterprete ou omita informação.\n"
            "NÃO adicione introdução, conclusão, título global ou conhecimento externo.\n"
            "Preserve ordem, listas, tabelas, código, URLs e termos técnicos.\n"
            "Se uma restrição de formatação conflitar com preservar informação, preserve a informação."
        )

    def get_format_strict_rules(self) -> str:
        return """
REGRAS CRÍTICAS DE FORMATAÇÃO:
1. Deve preservar toda a informação contida na entrada.
2. Não omita nenhuma secção, parágrafo, item de lista, tabela, exemplo de código, URL, termo técnico ou afirmação factual.
3. Não resuma, encurte, expanda, reinterprete nem adicione informação.
4. A sua tarefa é apenas formatar.
5. A saída deve conter toda a informação da fonte, preservando a ordem original.
6. Se as restrições de formatação conflitarem com preservar informação, preservar tem prioridade.
7. Nunca use conhecimento externo.
8. Nunca complete informação em falta.
9. Nunca invente exemplos ou explicações.
10. Produza APENAS a versão formatada da entrada. NÃO adicione um título no topo. NÃO adicione uma secção «Introdução». NÃO adicione conclusões. NÃO invente títulos de secção.
11. Preserve a estrutura de parágrafos; não prefixe cada parágrafo com marcadores de lista salvo se a entrada já o fizer.
12. Se não couber todo o conteúdo, produza o que couber e PARE num limite de frase. Nunca emita «[texto truncado]» nem marcadores semelhantes.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Aplique o formato e o estilo indicados nas instruções ao seguinte texto. "
            "NÃO resuma nem omita informação:\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nIMPORTANTE: Este é o BLOCO 1 de {total} num documento multiparte. "
                "Formate esta secção como a ABERTURA do documento. "
                "PODE incluir uma introdução se o conteúdo o justificar. "
                "NÃO adicione uma conclusão nem observações de encerramento."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nIMPORTANTE: Este é o BLOCO {idx} de {total} (ÚLTIMO BLOCO) num documento multiparte. "
                "Formate esta secção como o ENCERRAMENTO do documento. "
                "PODE incluir uma conclusão se o conteúdo o justificar. "
                "NÃO adicione uma nova introdução nem reinicie a numeração."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nIMPORTANTE: Este é o BLOCO {idx} de {total} (BLOCO INTERMÉDIO) num documento multiparte. "
            "Formate isto como CONTINUAÇÃO do documento. "
            "NÃO adicione introdução, NÃO adicione conclusão, NÃO reinicie a numeração de secções."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Processe os seguintes blocos de texto. "
            "Escreva a saída unificada apenas em português; traduza quaisquer blocos escritos em espanhol ou noutra língua. "
            "Se um bloco for apenas um índice, ignore-o completamente; não o mencione.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Bloco {block_index} (Fragmentos: {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "INSTRUÇÃO CRÍTICA: É um passo intermédio de redução. "
            "Una e deduplique os blocos fornecidos. "
            f"Comprimento restante objetivo: aproximadamente {pct}% da entrada (~{target_words} palavras). "
            f"Escreva pelo menos {min_words} palavras. NÃO comprima substancialmente abaixo deste objetivo. "
            "Não repita parágrafos para preencher. "
            "Preserve nomes distintivos, exemplos, slogans, conclusões e factos bibliográficos de CADA bloco. "
            "Descarte apenas formulações repetidas e reformulações verbosas. Não invente conteúdo.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "INSTRUÇÃO CRÍTICA: É o passo FINAL de síntese. "
            "Integre os blocos num único resumo em português, sem duplicar secções. "
            f"Piso de cobertura: conserve pelo menos ~{min_words} palavras de conteúdo não redundante "
            f"(objetivo ~{target_words}) se os blocos o contiverem. "
            "Se os blocos tiverem menos do que o objetivo, conserve TODO o conteúdo distintivo; "
            "não comprima mais e não invente preenchimento para atingir a contagem. "
            "Se os blocos tiverem mais, una duplicados mas não elimine temas, números, nomes ou exemplos. "
            "Um índice não é conteúdo desenvolvido: omita esses blocos e não mencione que existe um índice. "
            "Não apresente unidades, exemplos ou APIs que só apareçam no índice. "
            "Nomeie apenas ferramentas e APIs presentes nos blocos.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        """Instruction prepended when REDUCE final output fails the quality gate."""
        return (
            "CRÍTICO: Escreva o resumo em si. Nunca um menu de ajuda, saudação de assistente, "
            "capa de livro ou perguntas ao leitor.\n\n"
        )
