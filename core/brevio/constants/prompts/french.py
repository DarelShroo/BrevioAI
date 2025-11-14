from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


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
                "Résumer de manière concise, en supprimant les redondances",
                "Conserver le titre original s'il est présent, sans modification, en utilisant sa formulation et son format exacts (ex : # Titre, ## Sous-titre)",
                "S'adapter complètement au ton, à l'intention et à la structure implicite du contenu source",
                "Ne pas introduire de titres, sous-titres ou en-têtes à moins qu'ils ne soient explicitement présents dans le texte original",
                "Conserver les exemples ou concepts clés dans leur format original (ex : listes, code, italiques)",
                "Éviter les interprétations subjectives ou les modifications inutiles",
                "Produire un seul bloc de texte continu à moins que le contenu original ne spécifie autrement",
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
            "Évitez les phrases génériques comme « Le texte est maintenant exempt de répétitions tout en restant clair et cohérent ». Concentrez-vous sur des commentaires concrets et précis.",
            "Ne pas inclure des phrases comme « Voici le texte révisé, supprimant les redondances et répétitions, tout en conservant tous les détails et la structure originale. »",
            "Ne jamais inclure l’étiquette ```markdown. Si vous utilisez des blocs de code, ils doivent être non spécifiés ou utiliser un langage autre que Markdown.",
            f"À partir de maintenant, veuillez répondre uniquement en français, quelle que soit la langue de la question originale.",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- Résumez le document de manière complète, en mettant en évidence les thèmes principaux, les points clés et l’objectif général en environ {word_limit} mots."

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            Contexte du texte précédent : {previous_context}\n
            Instructions : Fournissez un résumé détaillé du texte suivant, en intégrant les nouvelles informations de manière cohérente avec le contexte précédent.
            Incluez des exemples, des explications et tous les détails qui facilitent l’étude du sujet.
            Organisez le résumé en sections ou points clés pour une meilleure compréhension."""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""Vous êtes un éditeur expert en amélioration de textes en supprimant les redondances.
            Vérifiez le résumé suivant et supprimez uniquement les informations répétitives ou redondantes,
            comme les phrases, idées ou contenus répétés.
            Ne simplifiez, ne réduisez ni ne résumez le contenu de quelque manière que ce soit ; conservez tous les détails, données et éléments importants tels quels.
            Assurez-vous que le texte final soit clair, cohérent et bien structuré, sans en altérer la structure ni le sens original."""
        return prompt
