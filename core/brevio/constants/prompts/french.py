from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class FrenchPrompts:
    INSTRUCTIONS_TITLE: str = "**Instructions:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Langue spécifique:** Français"
    SPECIFIC_LANGUAGE: str = "À partir de maintenant, toutes les réponses doivent être uniquement en français."
    EXAMPLE_TITLE: str = "**Exemple**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["Résumé direct sans titres supplémentaires"]},
            "styles": {
                "default": {
                    "tone": "Neutre, adapté au contexte",
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
                "Résumer le contenu de la source : thèmes, définitions, faits, procédures et exemples importants",
                "Écrire à la troisième personne. Première personne interdite (j'ai appris, j'ai besoin de clarifier, cela m'aiderait)",
                "N'inventez pas de questions, exercices, doutes ni sections de 'points à clarifier' / 'ce que j'ai appris'",
                "Ne transformez pas le document en journal d'apprentissage ni en devoirs d'étudiant",
                "Préserver le titre original s'il est présent, sans modification, avec sa rédaction et son format exacts (ex. : # Titre, ## Sous-titre)",
                "Utiliser des titres uniquement si le document original a de véritables sections équivalentes",
                "Maintenir les exemples ou concepts clés dans leur format d'origine (ex. : listes, code, italiques)",
                "Ne pas ajouter de connaissances externes ni d'affirmations non étayées par la source",
            ],
            "needs": "Simplicité et fidélité au contenu original",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Événement] en Direct",
                    "- **[MM:SS]** Déclaration ou fait clé",
                    "- **[MM:SS]** Description d'un moment clé ou développement",
                    "- **[MM:SS]** Réaction ou analyse de l'événement",
                ],
                "news_wire": [
                    "[Date] - [Lieu] - Résumé bref et direct",
                    "### Détails Clés",
                    "- [Fait clé 1]",
                    "- [Fait clé 2]",
                    "### Contexte",
                    "- [Informations de fond]",
                    "### Statistiques (le cas échéant)",
                    "- [Statistique 1]",
                    "- [Statistique 2]",
                    "### Impact",
                    "- [Impact à court terme]",
                    "- [Implications à long terme]",
                ],
                "analysis": [
                    "## [Sujet] en Profondeur",
                    "### Aperçu",
                    "- [Bref résumé du sujet]",
                    "### Aspects Clés",
                    "- [Aspect 1] : [Analyse détaillée]",
                    "- [Aspect 2] : [Analyse détaillée]",
                    "### Implications",
                    "- [Implications à court terme]",
                    "- [Implications à long terme]",
                    "### Opinions d'Experts",
                    "- [Citation ou perspective d'un expert]",
                    "### Conclusion",
                    "- [Résumé des principales conclusions et perspectives futures]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narratif, urgent",
                    "elements": ["chronologie", "moments clés", "réactions"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Direct, informatif",
                    "elements": ["détails clés", "contexte", "statistiques", "impact"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "Réfléchi, contextuel",
                    "elements": [
                        "aperçu",
                        "aspects clés",
                        "implications",
                        "opinions d'experts",
                        "conclusion",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Inclure des horodatages précis pour les chroniques",
                "Citer les sources le cas échéant",
                "Éviter les opinions dans les dépêches",
                "Utiliser des puces pour les détails clés dans les dépêches",
                "Inclure au moins une statistique ou donnée dans les dépêches",
                "Mettre en évidence les impacts à court et long terme dans les dépêches",
                "Pour les chroniques, se concentrer sur les moments clés et les réactions en temps réel",
                "Pour les analyses, fournir une exploration détaillée du sujet, incluant causes, effets et perspectives d'experts",
            ],
            "needs": [
                "Rapidité pour les dépêches, détails pour les chroniques, contexte pour les analyses"
            ],
        },
        "marketing": {
            "structures": {
                "highlights": ["# ✨ [Campagne] - Points Forts", "🎯 **Clé :** Valeur"],
                "storytelling": [
                    "## [Marque] - Une Histoire : [Titre]",
                    "### Introduction",
                    "- [Accroche émotionnelle ou cadre]",
                    "### Récit Principal",
                    "- [Événement clé ou tournant]",
                    "- [Défis ou conflits]",
                    "- [Résolution ou résultat]",
                    "### Impact Émotionnel",
                    "- [Comment l'histoire fait ressentir l'audience]",
                    "### Appel à l'Action",
                    "- [Incitation à interagir avec la marque ou le produit]",
                ],
                "report": [
                    "## [Campagne] - Résultats",
                    "### Aperçu",
                    "- [Bref résumé de la campagne et ses objectifs]",
                    "### Métriques Clés",
                    "| **Métrique** | **Objectif** | **Réel** | **Écart** |",
                    "|------------|----------|------------|--------------|",
                    "| [Métrique 1] | [Objectif 1] | [Réel 1] | [Écart 1] |",
                    "| [Métrique 2] | [Objectif 2] | [Réel 2] | [Écart 2] |",
                    "### Analyse",
                    "- [Analyse détaillée des résultats, incluant succès et défis]",
                    "### Recommandations",
                    "- [Recommandations actionnables basées sur les données]",
                    "### Conclusion",
                    "- [Résumé des principales conclusions et prochaines étapes]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Engageant, visuel",
                    "elements": ["emojis", "puces"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Émotionnel, immersif",
                    "elements": ["récit", "accroche_émotionnelle", "appel_à_l'action"],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analytique, clair",
                    "elements": ["tableau", "analyse", "recommandations"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Utiliser un langage engageant pour les points forts et le storytelling",
                "Inclure des KPI dans les rapports",
                "Éviter les termes techniques excessifs",
                "Pour le storytelling, se concentrer sur la connexion émotionnelle et le flux narratif",
            ],
            "needs": "Impact visuel, connexion émotionnelle, données actionnables",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Étude/Traitement] - Rapport Clinique :**",
                    "Paragraphe technique concis et axé sur les données, centré sur les résultats et l'efficacité",
                ],
                "summary": [
                    "# 🩺 [Sujet] - Résumé",
                    "📈 **Indicateur :** Résultat",
                    "| Semaine | Progrès |",
                ],
                "case": ["**[Patient] - Cas Clinique :**", "Narration détaillée"],
            },
            "styles": {
                "report": {
                    "tone": "Formel, précis et basé sur des preuves",
                    "elements": ["données_quantitatives", "résultats_cliniques"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visuel, accessible",
                    "elements": ["puces", "tableau"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "Narratif, clinique",
                    "elements": ["narration"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "Toujours inclure des données quantitatives et mesurables lorsque disponibles",
                "Maintenir la rigueur scientifique et éviter un langage subjectif",
                "Adapter la complexité du langage selon l'audience (technique pour les médecins, simplifié pour les patients)",
                "Assurer la clarté, l'exactitude et l'accessibilité des informations médicales",
            ],
            "needs": {
                "doctors": "Données cliniques claires et précises pour une prise de décision éclairée",
                "patients": "Explications accessibles et compréhensibles des conditions et traitements",
                "researchers": "Informations robustes et basées sur des données pour l'analyse",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Version] - Mise à Jour",
                    "✨ **Nouvelles Fonctionnalités :**",
                    "- Fonctionnalité",
                    "🐛 **Correctifs :**",
                    "- Correction",
                ],
                "proposal": [
                    "# [Projet] - Proposition Technique",
                    "## Introduction",
                    "Brève description du projet, de ses objectifs et du problème qu'il vise à résoudre.",
                    "## Objectifs",
                    "- Objectif 1 : Décrire le premier objectif du projet.",
                    "- Objectif 2 : Décrire le deuxième objectif du projet.",
                    "## Approche Technique",
                    "Expliquer la solution technique, incluant outils, frameworks et méthodologies utilisés.",
                    "### Fonctionnalités Clés",
                    "- Fonctionnalité 1 : Décrire la première fonctionnalité clé.",
                    "- Fonctionnalité 2 : Décrire la deuxième fonctionnalité clé.",
                    "## Avantages",
                    "Mettre en évidence les avantages de la solution proposée, comme l'efficacité, l'évolutivité ou les économies.",
                    "## Plan de Mise en Œuvre",
                    "Fournir un calendrier général ou des étapes pour la mise en œuvre.",
                    "## Risques et Atténuation",
                    "Identifier les risques potentiels et proposer des stratégies pour les atténuer.",
                    "## Conclusion",
                    "Résumer la proposition et réitérer sa valeur.",
                ],
                "diagram": [
                    "# [Processus] - Flux",
                    "```mermaid",
                    "graph TD",
                    "  A[Début] --> B{Décision ?}",
                    "  B -->|Oui| C[Processus 1]",
                    "  B -->|Non| D[Processus 2]",
                    "  C --> E[Fin]",
                    "  D --> E",
                    "```",
                    "**Annotations :**",
                    "- **A** : Début du processus.",
                    "- **B** : Point de décision.",
                    "- **C/D** : Chemins alternatifs.",
                    "- **E** : Fin du processus.",
                    "**Couleurs :**",
                    "- **Vert** : Chemin réussi (ex : utilisateur connecté).",
                    "- **Rouge** : Chemin alternatif (ex : utilisateur non connecté).",
                    "**Légende :**",
                    "- **Rectangle** : Étape du processus.",
                    "- **Losange** : Point de décision.",
                    "- **Cercle** : Début/Fin.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Technique, concis",
                    "elements": ["puces"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Persuasif, clair et structuré",
                    "elements": ["titres", "puces", "tableaux"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visuel, descriptif et modulaire",
                    "elements": ["mermaid", "couleurs", "annotations", "légende"],
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
                "Utiliser une terminologie technique pertinente au projet.",
                "Mettre en avant les avantages de la solution pour persuader les parties prenantes.",
                "Inclure un plan de mise en œuvre clair et structuré.",
                "Aborder les risques potentiels et proposer des stratégies d'atténuation.",
                "Utiliser des puces et des titres pour améliorer la lisibilité.",
                "Fournir des exemples concrets ou des études de cas pour étayer la proposition.",
                "S'assurer que la proposition est modulaire et facilement modifiable.",
                "Inclure une conclusion résumant la valeur de la proposition.",
            ],
            "needs": "Persuasion des parties prenantes, clarté de l'approche technique, documentation structurée et insights actionnables",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Sujet] - Guide",
                    "## [Section]",
                    "- **Concept :** Explication avec exemples pratiques et applications.",
                ],
                "quick_ref": [
                    "**[Sujet] - Référence Rapide :**",
                    "- [Point clé] : Résumé bref et actionnable avec contexte pratique clair.",
                ],
                "timeline": [
                    "# 🎥 [Cours] - Chronologie",
                    "- **[MM:SS]** [Concept clé ou action réalisée] : [Explication brève et claire avec résultats ou actions, soulignant l'application réelle].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Éducatif, structuré, avec des exemples pour plus de clarté",
                    "elements": [
                        "sous-sections",
                        "puces",
                        "exemples",
                        "applications_réelles",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Concis, pratique, conçu pour un apprentissage rapide",
                    "elements": ["puces", "résumés_clairs"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Chronologique, axé sur l'action, clair avec un accent sur les applications réelles",
                    "elements": [
                        "chronologie",
                        "actions_étape_par_étape",
                        "indices_visuels",
                        "contexte_réel",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Fournir des explications claires et actionnables avec des exemples.",
                "Maintenir les informations concises mais exhaustives, axées sur les applications pratiques.",
                "S'assurer de l'alignement avec les objectifs d'apprentissage et le contexte.",
                "Mettre l'accent sur la clarté et l'utilisabilité, surtout pour les cas d'usage réels.",
            ],
            "needs": "Faciliter l'étude, la référence rapide et le suivi vidéo avec des insights pratiques",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Projet] - Chronique",
                    "- **[MM:SS]** Élément marquant",
                ],
                "report": [
                    "**[Projet] - Rapport Technique :**",
                    "Paragraphe avec détails clés",
                ],
                "list": ["# [Projet] - Détails", "- **Aspect :** Description"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narratif, visuel",
                    "elements": ["chronologie"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Technique, détaillé",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptif, organisé",
                    "elements": ["puces"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Mettre en avant l'innovation ou la durabilité",
                "Inclure des données techniques si applicable",
                "Être visuellement attrayant",
            ],
            "needs": "Documentation technique, présentation attractive, suivi vidéo",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Période] - Rapport Financier",
                    "- **Indicateur :** [Valeur]",
                ],
                "table": [
                    "## [Période] - Résumé Financier",
                    "| **Indicateur** | **Valeur** |",
                ],
                "executive": [
                    "**[Période] - Résumé Exécutif :**",
                    "Paragraphe bref et percutant mettant en lumière les insights clés.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analytique, formel",
                    "elements": ["puces"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "Visuel, concis",
                    "elements": ["tableau"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Direct, exécutif",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Assurer clarté et concision dans la présentation des chiffres clés.",
                "Éviter toute ambiguïté dans la présentation des données.",
                "Soutenir la prise de décision avec des insights actionnables.",
                "Les titres de tableaux doivent être formatés sans espaces supplémentaires avant ou après les doubles astérisques.",
            ],
            "needs": "Données actionnables, synthèse visuelle claire, résumés exécutifs axés sur l'impact",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Destination] - Chronique",
                    "- **[MM:SS]** Initiative",
                    "- **[MM:SS]** Jalon important",
                ],
                "report": [
                    "**[Destination] - Politiques :**",
                    "Paragraphe formel mettant l'accent sur les objectifs de la destination et son impact sur le tourisme",
                ],
                "list": [
                    "# [Destination] - Initiatives",
                    "- **Domaine :** Détail (envisager d'ajouter la culture locale ou les attractions)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narratif, engageant, immersif",
                    "elements": ["chronologie", "storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formel, informatif, objectif",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descriptif, clair, informatif",
                    "elements": ["puces", "faits_concises"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Mettre en avant la durabilité, l'importance culturelle et l'attrait touristique",
                "Inclure des informations pratiques pour les voyageurs (ex : meilleure période pour visiter, attractions locales, contacts essentiels)",
                "Se concentrer sur des descriptions claires, concises et précises des politiques et initiatives",
                "Éviter les exagérations, rester réaliste et informatif",
            ],
            "needs": "Promotion engageante avec des highlights informatifs, présentation claire des politiques et détails pratiques pour les touristes",
        },
        "requirements": {
            "structures": {
                "elicitation": [
                    "Exigences pour [Projet/Nom] - Élicitation",
                    "Contexte",
                    "- Réunion : [Date, participants, objectif].",
                    "- Périmètre : [Objectif ou résultat attendu].",
                    "Exigences fonctionnelles",
                    "- FR-[ID] : [Description claire]. (Priorité : [Haute/Moyenne/Basse], Justification : [Raison brève]).",
                    "Exigences non fonctionnelles",
                    "- NFR-[ID] : [Description, ex. qualité, délais]. (Priorité : [Haute/Moyenne/Basse], Justification : [Raison]).",
                    "Dépendances et contraintes",
                    "- Dépendance : [Relation avec d'autres exigences/ressources].",
                    "- Contrainte : [Limitations, ex. budget, temps].",
                    "Questions ouvertes",
                    "- [Question à clarifier].",
                    "Horodatages (le cas échéant)",
                    "- [MM:SS] : [Citation brève de la source].",
                    "Critères de priorisation",
                    "- Haute : Critique pour le succès ou l'urgence.",
                    "- Moyenne : Important, mais non essentiel.",
                    "- Basse : Souhaitable, reportable.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Clair, objectif, adaptable",
                    "elements": ["bullet_points", "IDs", "priorities"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Extraire les exigences directement, sans interprétations.",
                "Utiliser des IDs (FR-01, NFR-01) pour la traçabilité.",
                "Prioriser avec justification (impact/urgence).",
                "Utiliser un langage clair centré sur le « quoi » qui est nécessaire.",
                "Lister les ambiguïtés sous « Questions ouvertes ».",
                "Horodatages uniquement pour les exigences clés.",
            ],
            "needs": "Capture claire des exigences pour tout projet, facilitant la planification et la communication.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Sujet] - Guide",
                    "## [Section]",
                    "- **Concept :** Définition, principe, relation, processus, mécanisme, classification ou évidence pertinente.",
                ],
                "formula_reference": [
                    "# 🔬 [Sujet] - Référence de formules",
                    "## Formules principales",
                    "| Formule | Signification | Variables | Unités | Conditions |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Sujet] - Développement",
                    "## Point de départ",
                    "- [Définition, principe, équation, observation, donnée ou condition initiale présente dans la source.]",
                    "## Développement",
                    "1. [Première étape ou raisonnement présent dans la source.]",
                    "2. [Transformation, relation, procédure ou raisonnement présent dans la source.]",
                    "## Résultat",
                    "- **Résultat :** [Résultat ou conclusion obtenu dans la source.]",
                ],
                "quick_ref": [
                    "**[Sujet] - Référence rapide :**",
                    "- **Concept :** Définition brève.",
                    "- **Principe/Loi/Théorie :** Relation fondamentale.",
                    "- **Processus/Relation :** Description essentielle.",
                    "- **Donnée/Formule :** Information quantitative pertinente.",
                    "- **Condition :** Applicabilité ou limitation.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Éducatif, rigoureux et structuré",
                    "elements": [
                        "concepts",
                        "principes",
                        "lois",
                        "théories",
                        "modèles",
                        "processus",
                        "mécanismes",
                        "structures",
                        "relations",
                        "données",
                        "formules",
                        "exemples",
                        "évidences",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Technique, compact et précis, orienté vers l'application correcte et la référence",
                    "elements": [
                        "formules",
                        "variables",
                        "unités",
                        "relations",
                        "conditions",
                        "tableaux",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formel, logique et rigoureux, préservant le raisonnement réellement soutenu par la source",
                    "elements": [
                        "équations",
                        "procédures",
                        "déductions",
                        "séquences",
                        "raisonnements",
                        "hypothèses",
                        "conditions",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Concis, technique et pratique, conçu pour une révision rapide sans perdre la précision scientifique",
                    "elements": [
                        "concepts clés",
                        "principes",
                        "lois",
                        "théories",
                        "processus",
                        "formules",
                        "données",
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
                "Utiliser exclusivement les informations présentes dans la source.",
                "Ne pas introduire de connaissances externes même si elles sont scientifiquement correctes, connues, évidentes ou utiles pour compléter l'explication.",
                "Ne pas inventer, compléter, corriger ni réinterpréter un contenu qui n'est pas soutenu par la source.",
                "Les structures sont uniquement un guide d'organisation et n'obligent pas à créer du contenu pour compléter des sections.",
                "Ne pas inclure une section lorsque la source ne contient pas suffisamment d'informations pour la justifier.",
                "Préserver les définitions, principes, lois, théories, hypothèses, modèles, processus, mécanismes, classifications, relations, données, formules, variables, unités, évidences et conditions pertinentes présents dans la source.",
                "Maintenir le sens original des termes scientifiques, symboles, variables, grandeurs, relations, processus et mécanismes.",
                "Ne pas transformer une hypothèse, un modèle, une observation, une corrélation, une association ou un résultat expérimental en un fait, une loi ou une relation causale non établie par la source.",
                "Ne pas généraliser les résultats, mécanismes ou conclusions au-delà des conditions, de la population, du système, de l'échelle ou du contexte indiqués dans la source.",
                "Préserver les exceptions, limites, hypothèses, restrictions, incertitudes et conditions de validité lorsqu'elles affectent l'interprétation.",
                "Lorsqu'il existe des données quantitatives, conserver les valeurs, unités, relations, ordres de grandeur et la précision pertinente.",
                "Lorsqu'il existe des formules ou des relations mathématiques, préserver les signes, exposants, indices, opérateurs, variables, unités, approximations et conditions de validité.",
                "Ne pas effectuer de conversions, calculs, transformations algébriques ou inférences quantitatives supplémentaires qui ne sont pas présents ou clairement soutenus par la source.",
                "Lorsqu'il existe une dérivation, une démonstration, une procédure, une expérience ou un raisonnement séquentiel, conserver uniquement les étapes essentielles réellement soutenues par la source.",
                "Ne pas ajouter d'étapes intermédiaires, de mécanismes, de causes ou d'explications que la source ne présente pas ou ne permet pas d'établir de façon non ambiguë.",
                "Conserver les relations temporelles, causales, fonctionnelles, structurelles et hiérarchiques lorsqu'elles sont pertinentes pour comprendre correctement le contenu.",
                "Ne pas confondre corrélation et causalité ni association et mécanisme.",
                "Ne pas éliminer d'informations dont l'absence pourrait changer le sens, l'interprétation, le résultat ou le champ d'application du contenu.",
                "Éliminer les redondances et les formulations répétitives sans éliminer l'information scientifique nécessaire.",
                "Réduire l'explication, pas le sens.",
                "En cas de conflit, prioriser dans cet ordre : fidélité à la source, exactitude scientifique, préservation du sens et des conditions, clarté, structure et enfin concision.",
                "L'objectif est de représenter de façon compacte et précise la connaissance contenue dans la source, non de fournir une explication générale du sujet fondée sur des connaissances externes.",
            ],
            "needs": (
                "Fidélité et précision scientifiques maximales, en préservant les concepts, "
                "processus, mécanismes, relations, données, formules, évidences, "
                "conditions, limites et raisonnement essentiel présents dans la source, "
                "sans introduire de connaissances externes ni compléter les informations absentes."
            ),
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "Le contenu décrit des mesures économiques annoncées le 08 mars 2025, incluant des réductions d'impôts et des lignes de crédit."
        },
        "journalism": {
            "chronicle": (
                "# Événement Apple en Direct\n"
                "- **[00:03:00]** Tim Cook présente Apple Intelligence, un nouveau système d'IA intégré aux appareils Apple.\n"
                "- **[00:05:11]** Présentation de l'Apple Watch Series 10, mettant en avant son écran plus grand et son design plus fin.\n"
                "- **[00:07:03]** Démonstration du nouvel écran OLED, 40% plus lumineux sous certains angles.\n"
                "- **[00:09:06]** Annonce d'une réduction d'épaisseur de 10% par rapport à la Series 9 (seulement 9.7 mm).\n"
                "- **[00:10:19]** Charge rapide : 80% de batterie en 30 minutes.\n"
                "- **[00:11:03]** Finition en titane poli, 20% plus légère que l'acier inoxydable.\n"
                "- **[00:12:00]** Accent sur la durabilité : 95% de titane recyclé et 100% d'énergie renouvelable utilisée.\n"
                "- **[00:13:50]** Nouvelles fonctionnalités santé : détection de l'apnée du sommeil et suivi de l'ovulation par température corporelle.\n"
                "- **[00:15:19]** 80% des cas d'apnée du sommeil non diagnostiqués dans le monde."
            ),
            "news_wire": (
                "[08 mars 2025] - Capitale - Le président annonce des mesures économiques.\n"
                "### Détails Clés\n"
                "- Réduction d'impôts pour les classes moyennes.\n"
                "- Augmentation des dépenses en infrastructures.\n"
                "### Contexte\n"
                "- Ces mesures visent à stimuler la croissance malgré l'inflation.\n"
                "### Statistiques\n"
                "- Croissance du PIB prévue : 2.5% en 2025.\n"
                "- Taux de chômage : 5.8% (contre 6.3% l'an dernier).\n"
                "### Impact\n"
                "- Court terme : Soulagement immédiat pour les ménages.\n"
                "- Long terme : Stimulation économique et création d'emplois."
            ),
            "analysis": (
                "## Réforme Fiscale en Profondeur\n"
                "### Aperçu\n"
                "- La réforme réduit les impôts des classes moyennes et augmente les investissements en infrastructures.\n"
                "### Aspects Clés\n"
                "- **Réduction d'impôts** : +10% de pouvoir d'achat pour les ménages.\n"
                "- **Infrastructures** : Création d'emplois et amélioration des services publics.\n"
                "### Implications\n"
                "- **Court terme** : Augmentation de la consommation.\n"
                "- **Long terme** : Croissance économique durable.\n"
                "### Opinions d'Experts\n"
                "- 'Une étape majeure contre les inégalités', selon Dr. Jane Doe, économiste à Harvard.\n"
                "### Conclusion\n"
                "- Réforme équilibrée, mais son succès dépend de sa mise en œuvre."
            ),
        },
        "marketing": {
            "highlights": "# ✨ Lancement EcoLife - Points Forts\n🎯 **Cible :** Jeunesse.\n📈 **Ventes :** +15%.",
            "storytelling": (
                "## EcoLife - Une Histoire : Voyage vers la Durabilité\n"
                "### Introduction\n"
                "- Dans une ville trépidante, Marie, jeune femme, se sentait dépassée par les défis environnementaux.\n"
                "### Récit Principal\n"
                "- Elle découvre EcoLife, une marque durable, et transforme son mode de vie.\n"
                "- Malgré le scepticisme initial, son engagement inspire son entourage.\n"
                "### Impact Émotionnel\n"
                "- Petits changements, grands impacts - personnels et écologiques.\n"
                "### Appel à l'Action\n"
                "- Rejoignez Marie dans son voyage durable avec EcoLife !"
            ),
            "report": (
                "## EcoLife - Résultats\n"
                "### Aperçu\n"
                "- Campagne visant à augmenter notoriété et ventes chez les jeunes via la promotion durable.\n"
                "### Métriques Clés\n"
                "| **Métrique**       | **Objectif** | **Réel** | **Écart** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Hausse des ventes | +15%     | +18%       | +3%          |\n"
                "| Portée réseaux sociaux | 1M      | 1.2M       | +200K        |\n"
                "### Analyse\n"
                "- Objectifs dépassés grâce à un engagement fort sur les réseaux et des partenariats influenceurs.\n"
                "### Recommandations\n"
                "- Poursuivre les collaborations influenceurs.\n"
                "- Élargir le contenu éducatif sur la durabilité.\n"
                "### Conclusion\n"
                "- Campagne réussie établissant des bases solides pour l'avenir."
            ),
        },
        "health": {
            "report": "**Traitement X - Rapport Clinique :** Essais cliniques montrant 70% de réduction des symptômes après 8 semaines de traitement.",
            "summary": "# 🩺 Traitement X - Résumé\n📈 **Efficacité :** 70%.\n| Semaine | Progrès |\n| 8       | 70%     |",
            "case": "**Patient A - Cas Clinique :** Homme de 62 ans montrant des améliorations après 2 semaines.",
        },
        "technology": {
            "changelog": "# v3.0 - Mise à Jour\n✨ **Nouvelles Fonctionnalités :**\n- OCR.\n🐛 **Correctifs :**\n- Exportation.",
            "proposal": """
                    # Projet X - Proposition Technique

                    ## Introduction
                    Système automatisé d'intégration d'API pour améliorer l'efficacité du traitement des données.

                    ## Objectifs
                    - Objectif 1 : Réduire la saisie manuelle de 50%.
                    - Objectif 2 : Augmenter la vitesse de traitement de 30%.

                    ## Approche Technique
                    Utilisation de Python avec Flask pour les APIs, Docker pour les conteneurs et Kubernetes pour l'orchestration.

                    ### Fonctionnalités Clés
                    - Fonctionnalité 1 : Collecte automatisée depuis multiples sources.
                    - Fonctionnalité 2 : Validation en temps réel et gestion des erreurs.

                    ## Avantages
                    - **Efficacité** : Réduction des efforts manuels et accélération des processus.
                    - **Évolutivité** : Gestion de volumes croissants de données.
                    - **Économies** : Automatisation des tâches répétitives.

                    ## Plan de Mise en Œuvre
                    1. **Phase 1** : Développement et tests des APIs (2 semaines).
                    2. **Phase 2** : Déploiement et intégration (3 semaines).
                    3. **Phase 3** : Surveillance et optimisation (1 semaine).

                    ## Risques et Atténuation
                    - **Risque 1** : Indisponibilité des APIs pendant le déploiement.
                    - **Atténuation** : Mises à jour progressives.
                    - **Risque 2** : Erreurs de validation.
                    - **Atténuation** : Tests automatisés.

                    ## Conclusion
                    Solution offrant des gains significatifs en efficacité et économies.
            """,
            "diagram": "# Authentification Utilisateur - Flux\n```mermaid\ngraph TD\n  A[Début] --> B{Connecté ?}\n  B -->|Oui| C[Afficher Dashboard]\n  B -->|Non| D[Rediriger vers Login]\n  C --> E[Fin]\n  D --> E\n```\n**Annotations :**\n- **A** : Début du processus.\n- **B** : Point de décision.\n- **C/D** : Chemins alternatifs.\n- **E** : Fin du processus.\n**Couleurs :**\n- **Vert** : Succès (connecté).\n- **Rouge** : Alternative (non connecté).\n**Légende :**\n- **Rectangle** : Étape.\n- **Losange** : Décision.\n- **Cercle** : Début/Fin.",
        },
        "education": {
            "guide": "# 📚 [Sujet] - Guide\n## [Section]\n- **Concept :** Explication avec exemples pratiques.",
            "quick_ref": "**[Sujet] - Référence Rapide :**\n- [Point clé] : Résumé bref et actionnable.",
            "timeline": "# � [Cours] - Chronologie\n- **[MM:SS]** [Concept clé ou action] : [Explication brève avec résultats].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Tour Verte - Chronique\n- **[01:15]** Matériaux durables.",
            "report": "**Tour Verte - Rapport Technique :** Conception utilisant l'énergie renouvelable.",
            "list": "# Tour Verte - Détails\n- **Matériaux :** Recyclés.\n- **Énergie :** Solaire.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Rapport Financier\n- **Revenus :** Croissance de 5% grâce aux avancées technologiques.",
            "table": "## Q1 2025 - Résumé Financier\n| **Indicateur** | **Valeur** |\n|---------------|-----------|\n| Revenus       | +5%       |",
            "executive": "**Q1 2025 - Résumé Exécutif :** Croissance de 5% grâce à la technologie et l'expansion stratégique, renforçant les perspectives.",
        },
        "tourism": {
            "chronicle": "# 🌍 Plage Bleue - Chronique\n- **[01:00]** Initiatives d'écotourisme réduisant les déchets.\n- **[05:00]** Important développement hôtelier éco-responsable.",
            "report": "**Plage Bleue - Politiques :** Promotion de la durabilité via la réduction des déchets et l'écotourisme. Objectif : neutralité carbone d'ici 2030.",
            "list": "# Plage Bleue - Initiatives\n- **Écologie :** Moins de plastique, plus de recyclage.\n- **Attraits :** Activités toute l'année, haute saison de mai à septembre.",
        },
        "requirements": {
            "elicitation": """Exigences pour Événement corporate 2025 - Élicitation
                Contexte
                - Réunion : 20/09/2025, équipe marketing ABC, planifier un événement pour 500 participants.
                - Périmètre : Événement de networking et lancement de produit, dans le budget.
                Exigences fonctionnelles
                - FR-01 : Lieu pour 500 personnes avec stands. (Priorité : Haute, Justification : Critique pour l'événement).
                - FR-02 : Inscription en ligne avec e-mail. (Priorité : Moyenne, Justification : Facilite la logistique).
                - FR-03 : Keynote avec orateur invité. (Priorité : Haute, Justification : Central pour l'événement).
                Exigences non fonctionnelles
                - NFR-01 : Respecter les normes de sécurité et d'accessibilité. (Priorité : Haute, Justification : Obligation légale).
                - NFR-02 : Planification en 2 mois. (Priorité : Haute, Justification : Délai fixe).
                Dépendances et contraintes
                - Dépendance : Le lieu nécessite une approbation budgétaire.
                - Contrainte : Budget de 30 000 $.
                Questions ouvertes
                - La diffusion en streaming de l'événement est-elle requise ?
                Horodatages
                - [03:15] : « Grand lieu pour 500 personnes avec stands ».
                - [08:20] : « La keynote rendra l'événement mémorable ».
                Critères de priorisation
                - Haute : Critique pour le succès ou l'urgence.
                - Moyenne : Important, mais non essentiel.
                - Basse : Souhaitable, reportable."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Sujet] - Guide\n"
                "## [Section présente dans la source]\n"
                "- **Concept :** Définition ou explication condensée à partir du contenu de la source.\n"
                "## [Autre section présente dans la source]\n"
                "- **Processus :** Séquence ou mécanisme décrit dans la source.\n"
            ),
            "formula_reference": (
                "# 🔬 [Sujet] - Référence de formules\n"
                "## Formules principales\n"
                "| Formule | Signification | Variables | Unités | Conditions |\n"
                "|---|---|---|---|---|\n"
                "| [Formule présente dans la source] | [Signification indiquée dans la source] | [Variables définies dans la source] | [Unités indiquées] | [Conditions indiquées] |\n"
            ),
            "derivation": (
                "# 🔬 [Sujet] - Développement\n"
                "## Point de départ\n"
                "- [Définition, équation, donnée, observation ou condition initiale présente dans la source.]\n"
                "## Développement\n"
                "1. [Première étape ou transformation explicitement montrée dans la source.]\n"
                "2. [Deuxième étape, relation ou raisonnement explicitement montré dans la source.]\n"
                "## Résultat\n"
                "- **Résultat :** [Résultat ou conclusion que la source obtient explicitement.]\n"
            ),
            "quick_ref": (
                "**[Sujet] - Référence rapide :**\n"
                "- **Concept :** [Définition présente dans la source.]\n"
                "- **Principe/Loi/Théorie :** [Uniquement s'il apparaît dans la source.]\n"
                "- **Processus/Relation :** [Processus ou relation décrit dans la source.]\n"
                "- **Donnée/Formule :** [Donnée ou formule présente dans la source.]\n"
                "- **Condition :** [Condition ou limitation indiquée dans la source.]\n"
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
            f"# Prompt pour {category.value.title()} - {style.value.title()}",
            f"**Objectif:** Créer du contenu au format {output_format.value.upper()} optimisé pour {category.value.title()}",
            f"**Style:** {style.value.title()} ({style_info['tone']})",
            f"**Besoins essentiels:** {spec.get('needs', 'adaptation au contexte')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "N'utilisez pas la première personne et ne prétendez pas être un étudiant prenant des notes.",
            "N'inventez pas de questions, de doutes, de conclusions ou de données absents de la source.",
            "La sortie EST le résumé. Jamais un menu d'aide, une couverture ou des questions au lecteur.",
            "N'incluez jamais l'étiquette ```markdown en aucune circonstance. Si vous utilisez des blocs de code, ils doivent être non spécifiés ou dans un langage autre que Markdown.",
            "Évitez les phrases génériques comme « Le texte est maintenant exempt de répétitions tout en restant clair et cohérent. » Concentrez-vous sur des commentaires concrets et précis.",
            "N'incluez pas de phrases comme « Voici le texte révisé, en supprimant les redondances et les répétitions, tout en préservant tous les détails et la structure originale. »",
            "À partir de maintenant, répondez uniquement en français, quelle que soit la langue de la question originale.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Instructions : Extraire les faits distinctifs de ce fragment.
            IMPORTANT : Vous ne traitez QU'UNE PARTIE (chunk) d'un document beaucoup plus grand.
            - Rédigez les titres, listes et prose en français. Autres langues uniquement dans le code ou les noms propres.
            - NE générez PAS d'Introduction globale ni de Conclusion globale.
            - NE recommencez PAS les hiérarchies de numérotation (ex. ## 1. Introduction).
            - NE générez PAS un document autonome.
            - Extrayez de CE fragment selon le niveau de résumé : définitions et faits centraux toujours ;
              exemples, chiffres et anecdotes uniquement à la densité de l'instruction de longueur.
            - Le niveau de résumé contrôle la densité de détail, pas le droit d'omettre un sujet majeur présent ici.
            - PRIORITÉ CRITIQUE : préserver la nature du langage ou du système (ex. interprété vs compilé,
              client vs serveur, statique vs dynamique) avec le même degré de certitude que la source.
            - Si le texte contraste pages statiques et dynamiques, définissez LES DEUX.
            - S'il affirme que quelque chose est multiplateforme uniquement en théorie, conservez cette réserve (ne la transformez pas en fait absolu).
            - Conservez les tableaux ou listes comparatifs point par point (ne les réduisez pas à « il y a des différences »).
            - Préservez les noms d'outils, chemins de fichiers, constantes numériques, formules et citations de code.
            - Préservez les conditions, exceptions et réserves (théoriquement, peut, seulement si, n'implique pas…).
            - Préservez la syntaxe, les formules et les exemples exactement tels qu'ils apparaissent dans ce fragment.
            - Distinguez une table des matières ou un index du contenu réellement développé ici.
            - Si ce fragment est un index, décrivez-le comme un index (quelles unités existent) et N'extrayez PAS ces unités comme si ce fragment les développait.
            - Ne traitez pas les leçons nommées dans l'index comme expliquées si ce fragment ne les développe pas.
            - Nommez uniquement les outils, bibliothèques, API, éditeurs et URL qui apparaissent littéralement dans ce fragment.
            - N'utilisez pas la première personne. N'inventez pas de questions ni de journal d'apprentissage.
            - La sortie EST l'extrait. Jamais un menu d'aide, une couverture de livre, des questions au lecteur, ou « de quoi avez-vous besoin ? ».
            - Ceci est un extrait dense pour une synthèse ultérieure, pas un minuscule récapitulatif autonome.
            - Utilisez le budget de sortie disponible pour les faits distinctifs ; ne vous arrêtez pas trop tôt s'il reste des détails importants.
            - Préparez le contenu pour qu'il soit utile à une synthèse globale ultérieure.
            - N'INCLUEZ AUCUNE connaissance externe ni information absente du texte.
            - NE générez PAS de table des matières ni d'index.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "Vous êtes un éditeur expert. Votre tâche est d'INTÉGRER les blocs de texte fournis "
            "en un texte unifié.\n\n"
            "RÈGLES OBLIGATOIRES :\n"
            "- ZÉRO REMPLISSAGE : N'ajoutez PAS de phrases de transition inutiles, d'introductions génériques ou de conclusions. "
            "Allez droit au but.\n"
            "- DÉDUPLICATION STRICTE : Éliminez tout concept, idée ou argument répété entre les blocs.\n"
            "- STRUCTURE UNIQUE : Consolidez le contenu sous une seule hiérarchie. Supprimez les en-têtes redondants, "
            "mais CONSERVEZ les sujets de section distincts qui représentent différentes parties de la source.\n"
            "- FIDÉLITÉ STRICTE : Maintenez une fidélité absolue. N'inventez PAS de faits ni n'ajoutez de connaissances externes.\n"
            "- COUVERTURE D'ABORD : Chaque bloc source au contenu substantiel doit être représenté. "
            "Le niveau de résumé contrôle la densité de détail, pas le droit qu'un sujet majeur disparaisse.\n"
            "- NE COMPRIMEZ PAS EN DESSOUS DE LA CIBLE : Fusionnez et supprimez les doublons. "
            "Si l'instruction de longueur demande plus de mots que l'entrée, "
            "conservez TOUT le contenu non redondant restant ; ne raccourcissez pas davantage et n'inventez pas de remplissage.\n"
            "- RESPECTEZ L'INSTRUCTION DE LONGUEUR : Si une instruction de longueur est fournie, suivez-la. "
            "Rester bien en dessous de la cible en supprimant des sujets majeurs est une erreur.\n"
            "- La sortie EST le résumé unifié. Jamais un assistant, un menu d'options, un blurb de couverture, "
            "des questions au lecteur, ou « de quoi avez-vous besoin ? ».\n"
            "- INTERDIT : première personne, journaux d'apprentissage, questions inventées, "
            "sections « ce que j'ai appris » ou « points à clarifier ».\n"
            "- L'index n'est pas du contenu développé : ne résumez pas les unités, exemples ou API "
            "qui n'apparaissent que dans la table des matières si le corps du document ne les explique pas.\n"
            "- Nommez uniquement les outils, bibliothèques, API, éditeurs et URL qui apparaissent littéralement dans les blocs.\n"
            "- Ne mentionnez pas « bloc 1 » ni d'étiquettes internes du pipeline.\n"
            "- N'inventez pas d'ISBN, de titres de livres ou de comparaisons Java/JVM que la source ne fait pas.\n"
            "- LANGUE : rédigez le résumé ENTIER en français. Traduisez les blocs qui sont en espagnol ou dans une autre langue. "
            "Autres langues uniquement dans les citations, le code ou les noms propres.\n"
            "- Un bloc qui dit « INDEX UNIQUEMENT » ou liste des unités/pages sans les expliquer "
            "est UNIQUEMENT un index : IGNOREZ-LE. Ne le mentionnez pas dans le résumé final. "
            "Ne listez pas les unités de l'index. Consacrez le résumé au contenu réellement développé.\n"
            "- PRÉSERVER SANS DILUER : noms d'outils, fichiers, constantes numériques, "
            "comparaisons point par point, et réserves de certitude (théoriquement, peut, n'implique pas, seulement si).\n"
            "- PAS de remplissage de tokens : ne clonez pas de sections, ne paraphrasez pas le même bloc plusieurs fois, "
            "n'inventez pas d'outils, d'API, d'éditeurs ou de runtimes absents de la source.\n"
            "- Si un sujet est déjà écrit, ne l'écrivez pas à nouveau. "
            "- Ordre de priorité : factualité, couverture, exhaustivité, cohérence, structure, puis concision. "
            "La concision ne doit pas détruire la couverture."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Styles et tons disponibles :**"

    def get_semantic_profile_title(self) -> str:
        return "**Profil sémantique (informations à préserver) :**"

    def get_length_instruction_title(self) -> str:
        return "**Instruction de longueur :**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Exprimez la thèse principale, les conclusions essentielles et les concepts centraux "
                "sous une forme très condensée. Conservez chaque pilier majeur. "
                "Omettez les exemples secondaires, anecdotes, conseils de lecture et nuances mineures."
            ),
            SummaryLevel.CONCISE: (
                "Préservez les arguments principaux, les justifications essentielles et la structure thématique primaire. "
                "Soyez direct ; réduisez l'élaboration secondaire sans supprimer de sections importantes."
            ),
            SummaryLevel.MODERATE: (
                "Préservez les arguments, justifications, preuves pertinentes, exemples représentatifs "
                "et taxonomies importantes."
            ),
            SummaryLevel.DETAILED: (
                "Préservez les sous-thèmes, la méthodologie, les preuves, les implications, les taxonomies complètes "
                "et les relations entre concepts."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Préservez les détails, y compris exceptions, nuances, cas particuliers, contexte "
                "et particularités formellement pertinentes. "
                "Dans les tutoriels techniques : n'omettez pas les définitions de la nature du système "
                "(interprété/compilé, client/serveur), les tableaux comparatifs, les noms d'outils, "
                "les fichiers d'exemple, les constantes numériques ou les conditions des exemples."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "LONGUEUR / DENSITÉ : Produisez un résumé visiblement plus court que modéré. "
                "Conservez la thèse, les piliers et les définitions centrales. "
                "Omettez les exemples secondaires, anecdotes, recommandations de lecture et toute note sur un index. "
                "Au plus un court exemple par pilier, et seulement s'il clarifie la définition. "
                "Être plus court que modéré est correct si les sujets majeurs survivent. "
                "Ne supprimez pas un pilier ; ne copiez pas chaque exemple de niveau modéré. "
                "Préférez une formulation dense à l'énumération de chaque cas."
            ),
            SummaryLevel.CONCISE: (
                "LONGUEUR / DENSITÉ : Produisez un résumé bref, plus long que very_concise et plus court que modéré. "
                "Préférez un libellé compact à la suppression de sections importantes. "
                "Un exemple représentatif par sujet majeur suffit."
            ),
            SummaryLevel.MODERATE: (
                "LONGUEUR / DENSITÉ : Produisez un résumé de longueur moyenne, visiblement plus long que very_concise "
                "et plus court que very_detailed. "
                "Conservez un exemple représentatif par concept majeur, avec des nombres ou noms distinctifs de la source. "
                "Ne copiez pas chaque cas ou anecdote."
            ),
            SummaryLevel.DETAILED: (
                "LONGUEUR / DENSITÉ : Produisez un résumé détaillé, plus long que modéré. "
                "Prenez l'espace nécessaire pour les sous-thèmes, preuves et plusieurs exemples de la source."
            ),
            SummaryLevel.VERY_DETAILED: (
                "LONGUEUR / DENSITÉ : Produisez un résumé visiblement plus long que modéré. "
                "Conservez chaque exemple, chiffre, nom, exception et condition développés dans le corps de la source. "
                "Ne comprimez pas ces faits distinctifs. "
                "Ne remplissez jamais en répétant des paragraphes, en clonant des sections, en citant l'index, "
                "ou en ajoutant des connaissances externes."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "GARANTIE DE COUVERTURE (s'applique à tous les niveaux de résumé) : "
            "Les idées principales, concepts essentiels, sujets de sections importantes et termes "
            "centraux DOIVENT survivre. Le niveau de résumé ne contrôle que la densité de détail "
            "et l'élaboration secondaire. Il n'autorise jamais la suppression d'une section majeure "
            "ni de la thèse centrale du document."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Liste de couverture (uniquement si la section est DÉVELOPPÉE dans les blocs, "
            "pas si elle n'apparaît que dans un index) :**\n"
            f"{lines}\n"
            "N'inventez pas le contenu d'un en-tête que les blocs n'expliquent pas."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Instruction de clôture :** "
            "Couvrez les faits distinctifs de CE fragment à la densité de l'instruction de longueur. "
            "Utilisez le budget de sortie disponible pour ces faits ; ne vous arrêtez pas trop tôt s'il reste des détails importants. "
            "Ne répétez pas des paragraphes pour remplir. "
            "Terminez toujours par une phrase complète."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "entrées de sommaire"
        return (
            "INDEX UNIQUEMENT — ce fragment est une table des matières, pas des leçons développées. "
            f"Liste : {listed}. "
            "Ne présentez pas ces entrées comme si le document les expliquait ici."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "Vous êtes un expert en synthèse documentaire. Résumez le document complet "
            "en une seule passe. Préservez la structure conceptuelle importante "
            "(titres/sections pertinents), les idées principales, définitions, "
            "procédures, exemples et termes centraux. "
            "Émettez du Markdown propre. N'inventez pas de contenu. "
            "N'écrivez pas de journal d'apprentissage ni de listes de questions.\n"
            "L'index ou la table des matières N'EST PAS du contenu développé : "
            "mentionnez-le uniquement comme un index ; ne présentez pas les unités ou exemples de l'index "
            "comme si le corps du document les avait expliqués.\n"
            "PRIORITÉ CRITIQUE : préserver la nature du langage (interprété/compilé), "
            "l'environnement d'exécution (client/serveur), le contraste statique/dynamique, "
            "les tableaux comparatifs, les noms d'outils, fichiers, constantes numériques "
            "et les réserves de certitude (théoriquement, peut, n'implique pas, seulement si).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "Vous êtes un éditeur de formatage. Votre seule tâche est d'appliquer le formatage "
            "Markdown au texte fourni.\n\n"
            "NE résumez PAS, NE raccourcissez PAS, N'étendez PAS, NE réinterprétez PAS et "
            "N'omettez PAS d'informations.\n"
            "N'ajoutez PAS d'introduction, de conclusion, de titre global ni de connaissances externes.\n"
            "Préservez l'ordre, les listes, les tableaux, le code, les URL et les termes techniques.\n"
            "Si une contrainte de formatage entre en conflit avec la préservation de l'information, "
            "préservez l'information."
        )

    def get_format_strict_rules(self) -> str:
        return """
RÈGLES CRITIQUES DE FORMATAGE :
1. Vous devez préserver toutes les informations contenues dans l'entrée.
2. N'omettez aucune section, paragraphe, élément de liste, tableau, exemple de code, URL, terme technique ou affirmation factuelle.
3. Ne résumez, ne raccourcissez, n'étendez, ne réinterprétez ni n'ajoutez d'informations.
4. Votre tâche est uniquement le formatage.
5. La sortie doit contenir toutes les informations sources, en préservant l'ordre d'origine.
6. Si les contraintes de formatage entrent en conflit avec la préservation de l'information, la préservation a priorité.
7. N'utilisez jamais de connaissances externes.
8. Ne complétez jamais les informations manquantes.
9. N'inventez jamais d'exemples ni d'explications.
10. Produisez UNIQUEMENT la version formatée de l'entrée. N'ajoutez PAS de titre en tête. N'ajoutez PAS de section « Introduction ». N'ajoutez PAS de conclusions. N'inventez PAS de titres de section.
11. Préservez la structure des paragraphes ; ne préfixez pas de puces à chaque paragraphe sauf si l'entrée le fait déjà.
12. Si tout le contenu ne tient pas, produisez ce qui tient et ARRÊTEZ à une limite de phrase. N'émettez jamais « [texte tronqué] » ni des marqueurs similaires.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Veuillez appliquer le format et le style indiqués dans les instructions au texte suivant. "
            "NE résumez PAS et N'omettez PAS d'informations :\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nIMPORTANT : Ceci est le BLOC 1 sur {total} d'un document en plusieurs parties. "
                "Formatez cette section comme l'OUVERTURE du document. "
                "Vous POUVEZ inclure une introduction si le contenu le justifie. "
                "N'ajoutez PAS de conclusion ni de remarques de clôture."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nIMPORTANT : Ceci est le BLOC {idx} sur {total} (DERNIER BLOC) d'un document en plusieurs parties. "
                "Formatez cette section comme la CLÔTURE du document. "
                "Vous POUVEZ inclure une conclusion si le contenu le justifie. "
                "N'ajoutez PAS de nouvelle introduction ni ne recommencez la numérotation."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nIMPORTANT : Ceci est le BLOC {idx} sur {total} (BLOC INTERMÉDIAIRE) d'un document en plusieurs parties. "
            "Formatez ceci comme une CONTINUATION du document. "
            "N'ajoutez PAS d'introduction, N'ajoutez PAS de conclusion, NE recommencez PAS la numérotation."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Traitez les blocs de texte suivants. "
            "Rédigez la sortie unifiée uniquement en français ; traduisez tout bloc écrit en espagnol ou dans une autre langue. "
            "Si un bloc n'est qu'un index, ignorez-le complètement ; ne le mentionnez pas.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Bloc {block_index} (Fragments : {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "INSTRUCTION CRITIQUE : Vous êtes une étape de réduction intermédiaire. "
            "Fusionnez et dédupliquez les blocs fournis. "
            f"Longueur restante cible : environ {pct}% de l'entrée (~{target_words} mots). "
            f"Écrivez au moins {min_words} mots. NE comprimez PAS substantiellement en dessous de cette cible. "
            "Ne répétez pas des paragraphes pour remplir. "
            "Préservez les noms distinctifs, exemples, slogans, conclusions et faits bibliographiques de CHAQUE bloc. "
            "Écartez uniquement les formulations répétées et les reformulations verbeuses. N'inventez pas de contenu.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "INSTRUCTION CRITIQUE : Vous êtes l'étape FINALE de synthèse. "
            "Intégrez les blocs en un seul résumé en français, sans dupliquer les sections. "
            f"Plancher de couverture : conservez au moins ~{min_words} mots de contenu non redondant "
            f"(cible ~{target_words}) si les blocs le contiennent. "
            "Si les blocs ont moins que la cible, conservez TOUT le contenu distinctif ; "
            "ne comprimez pas davantage et n'inventez pas de remplissage pour atteindre le compte. "
            "Si les blocs ont plus, fusionnez les doublons mais ne supprimez pas de sujets, chiffres, noms ou exemples. "
            "Un index n'est pas du contenu développé : omettez ces blocs et ne mentionnez pas qu'un index existe. "
            "Ne présentez pas d'unités, d'exemples ou d'API qui n'apparaissent que dans la table des matières. "
            "Nommez uniquement les outils et API présents dans les blocs.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        """Instruction prepended when REDUCE final output fails the quality gate."""
        return (
            "CRITIQUE : Rédigez le résumé lui-même. Jamais un menu d'aide, une salutation d'assistant, "
            "une couverture de livre ou des questions au lecteur.\n\n"
        )
