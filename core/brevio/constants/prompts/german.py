from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class GermanPrompts:
    INSTRUCTIONS_TITLE: str = "**Anweisungen:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Spezifische Sprache:** Deutsch"
    SPECIFIC_LANGUAGE: str = (
        "Ab sofort müssen alle Antworten ausschließlich auf Deutsch erfolgen."
    )
    EXAMPLE_TITLE: str = "**Beispiel**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {
                "default": ["Direkte Zusammenfassung ohne zusätzliche Überschriften"]
            },
            "styles": {
                "default": {
                    "tone": "Neutral, kontextangepasst",
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
                "Den Inhalt der Quelle zusammenfassen: Themen, Definitionen, Fakten, Verfahren und wichtige Beispiele",
                "In der dritten Person schreiben. Erste Person verboten (ich habe gelernt, ich muss klären, das würde mir helfen)",
                "Keine Fragen, Übungen, Zweifel oder Abschnitte zu 'zu klärenden Punkten' / 'was ich gelernt habe' erfinden",
                "Das Dokument nicht in ein Lerntagebuch oder Schülerhausaufgaben verwandeln",
                "Den Originaltitel beibehalten, falls vorhanden, ohne Änderung, mit exaktem Wortlaut und Format (z. B. # Titel, ## Untertitel)",
                "Überschriften nur verwenden, wenn das Originaldokument echte entsprechende Abschnitte hat",
                "Wichtige Beispiele oder Konzepte im Originalformat beibehalten (z. B. Listen, Code, Kursivschrift)",
                "Kein externes Wissen und keine Behauptungen hinzufügen, die die Quelle nicht stützt",
            ],
            "needs": "Einfachheit und Treue zum Originalinhalt",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Ereignis] Live",
                    "- **[MM:SS]** Aussage oder Schlüsselfakt",
                    "- **[MM:SS]** Beschreibung eines Schlüsselmoments oder Fortschritts",
                    "- **[MM:SS]** Reaktion oder Analyse des Ereignisses",
                ],
                "news_wire": [
                    "[Datum] - [Ort] - Kurze und direkte Zusammenfassung",
                    "### Wichtige Details",
                    "- [Schlüsselfakt 1]",
                    "- [Schlüsselfakt 2]",
                    "### Kontext",
                    "- [Hintergrundinformationen]",
                    "### Statistiken (falls zutreffend)",
                    "- [Statistik 1]",
                    "- [Statistik 2]",
                    "### Auswirkungen",
                    "- [Kurzfristige Auswirkungen]",
                    "- [Langfristige Folgen]",
                ],
                "analysis": [
                    "## [Thema] Vertiefung",
                    "### Überblick",
                    "- [Kurze Zusammenfassung des Themas]",
                    "### Schlüsselaspekte",
                    "- [Aspekt 1]: [Detaillierte Analyse]",
                    "- [Aspekt 2]: [Detaillierte Analyse]",
                    "### Folgen",
                    "- [Kurzfristige Folgen]",
                    "- [Langfristige Folgen]",
                    "### Expertenmeinungen",
                    "- [Zitat oder Perspektive eines Experten]",
                    "### Fazit",
                    "- [Zusammenfassung der wichtigsten Erkenntnisse und Zukunftsaussichten]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Erzählend, dringlich",
                    "elements": ["Zeitstrahl", "Schlüsselmomente", "Reaktionen"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Direkt, informativ",
                    "elements": [
                        "Schlüsseldetails",
                        "Kontext",
                        "Statistiken",
                        "Auswirkungen",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "Reflektierend, kontextuell",
                    "elements": [
                        "Überblick",
                        "Schlüsselaspekte",
                        "Folgen",
                        "Expertenmeinungen",
                        "Fazit",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Präzise Zeitangaben für Chroniken einfügen",
                "Quellen angeben (falls zutreffend)",
                "In Nachrichtenmeldungen Meinungen vermeiden",
                "Aufzählungspunkte für Schlüsseldetails in Nachrichtenmeldungen verwenden",
                "Mindestens eine Statistik oder einen Datenpunkt in Nachrichtenmeldungen einbinden",
                "Sowohl kurz- als auch langfristige Auswirkungen in Nachrichtenmeldungen hervorheben",
                "Bei Chroniken auf Schlüsselmomente und Echtzeit-Reaktionen fokussieren",
                "Bei Analysen eine detaillierte Themenbearbeitung mit Ursachen, Effekten und Expertenperspektiven liefern",
            ],
            "needs": [
                "Geschwindigkeit in Nachrichtenmeldungen, Detailtreue in Chroniken, Kontext in Analysen"
            ],
        },
        "marketing": {
            "structures": {
                "highlights": [
                    "# ✨ [Kampagne] - Highlights",
                    "🎯 **Schlüssel:** Wert",
                ],
                "storytelling": [
                    "## [Marke] - Eine Geschichte: [Titel]",
                    "### Einleitung",
                    "- [Emotionaler Haken oder Setting]",
                    "### Hauptgeschichte",
                    "- [Schlüsselereignis oder Wendepunkt]",
                    "- [Herausforderungen oder Konflikte]",
                    "- [Lösung oder Ergebnis]",
                    "### Emotionaler Impact",
                    "- [Wie die Geschichte das Publikum fühlen lässt]",
                    "### Handlungsaufforderung",
                    "- [Aufforderung zur Interaktion mit Marke oder Produkt]",
                ],
                "report": [
                    "## [Kampagne] - Ergebnisse",
                    "### Überblick",
                    "- [Kurze Zusammenfassung der Kampagne und ihrer Ziele]",
                    "### Kennzahlen",
                    "| **Metrik** | **Ziel** | **Ist-Wert** | **Abweichung** |",
                    "|------------|----------|------------|--------------|",
                    "| [Metrik 1] | [Ziel 1] | [Ist-Wert 1] | [Abweichung 1] |",
                    "| [Metrik 2] | [Ziel 2] | [Ist-Wert 2] | [Abweichung 2] |",
                    "### Analyse",
                    "- [Detaillierte Analyse der Ergebnisse, inkl. Erfolge und Herausforderungen]",
                    "### Empfehlungen",
                    "- [Umsetzbare Empfehlungen basierend auf den Daten]",
                    "### Fazit",
                    "- [Zusammenfassung der wichtigsten Erkenntnisse und nächsten Schritte]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Ansprechend, visuell",
                    "elements": ["Emojis", "Aufzählungspunkte"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Emotional, immersiv",
                    "elements": [
                        "Erzählung",
                        "emotionaler_Haken",
                        "Handlungsaufforderung",
                    ],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analytisch, klar",
                    "elements": ["Tabelle", "Analyse", "Empfehlungen"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Ansprechende Sprache für Highlights und Storytelling verwenden",
                "KPIs in Berichten einbeziehen",
                "Übermäßige Fachbegriffe vermeiden",
                "Beim Storytelling auf emotionale Verbindung und Erzählfluss achten",
            ],
            "needs": "Visuelle Wirkung, emotionale Verbindung, umsetzbare Daten",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Studie/Behandlung] - Klinischer Bericht:**",
                    "Prägnanter, datengetriebener technischer Absatz mit Fokus auf Ergebnisse und Wirksamkeit",
                ],
                "summary": [
                    "# 🩺 [Thema] - Zusammenfassung",
                    "📈 **Indikator:** Ergebnis",
                    "| Woche | Fortschritt |",
                ],
                "case": ["**[Patient] - Klinischer Fall:**", "Detaillierte Erzählung"],
            },
            "styles": {
                "report": {
                    "tone": "Formell, präzise und evidenzbasiert",
                    "elements": ["quantitative_Daten", "klinische_Ergebnisse"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visuell, zugänglich",
                    "elements": ["Aufzählungspunkte", "Tabelle"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "Erzählend, klinisch",
                    "elements": ["Erzählung"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "Immer quantitative und messbare Daten einbeziehen (falls verfügbar)",
                "Wissenschaftliche Strenge wahren und subjektive Sprache vermeiden",
                "Sprachkomplexität an Zielgruppe anpassen (technisch für Ärzte, vereinfacht für Patienten)",
                "Klarheit, Genauigkeit und Zugänglichkeit medizinischer Informationen sicherstellen",
            ],
            "needs": {
                "doctors": "Klar präsentierte klinische Daten für informierte Entscheidungen",
                "patients": "Verständliche Erklärungen von Zuständen und Behandlungen",
                "researchers": "Robuste, datengetriebene Informationen für Analysen",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Version] - Update",
                    "✨ **Neue Funktionen:**",
                    "- Funktion",
                    "🐛 **Korrekturen:**",
                    "- Korrektur",
                ],
                "proposal": [
                    "# [Projekt] - Technischer Vorschlag",
                    "## Einleitung",
                    "Kurze Beschreibung des Projekts, seiner Ziele und des zu lösenden Problems.",
                    "## Ziele",
                    "- Ziel 1: Erstes Ziel beschreiben.",
                    "- Ziel 2: Zweites Ziel beschreiben.",
                    "## Technischer Ansatz",
                    "Technische Lösung erläutern, inkl. Tools, Frameworks und Methoden.",
                    "### Hauptfunktionen",
                    "- Funktion 1: Erste Schlüsselfunktion beschreiben.",
                    "- Funktion 2: Zweite Schlüsselfunktion beschreiben.",
                    "## Vorteile",
                    "Vorteile der Lösung hervorheben (z.B. Effizienz, Skalierbarkeit, Kosteneinsparungen).",
                    "## Umsetzungsplan",
                    "Grober Zeitplan oder Schritte zur Implementierung.",
                    "## Risiken und Gegenmaßnahmen",
                    "Potenzielle Risiken identifizieren und Strategien zur Minimierung vorschlagen.",
                    "## Fazit",
                    "Den Wert des Vorschlags zusammenfassen und bekräftigen.",
                ],
                "diagram": [
                    "# [Prozess] - Ablauf",
                    "```mermaid",
                    "graph TD",
                    "  A[Start] --> B{Entscheidung?}",
                    "  B -->|Ja| C[Prozess 1]",
                    "  B -->|Nein| D[Prozess 2]",
                    "  C --> E[Ende]",
                    "  D --> E",
                    "```",
                    "**Anmerkungen:**",
                    "- **A**: Prozessbeginn.",
                    "- **B**: Entscheidungspunkt.",
                    "- **C/D**: Alternative Pfade.",
                    "- **E**: Prozessende.",
                    "**Farben:**",
                    "- **Grün**: Erfolgspfad (z.B. eingeloggter Benutzer).",
                    "- **Rot**: Alternativer Pfad (z.B. nicht eingeloggter Benutzer).",
                    "**Legende:**",
                    "- **Rechteck**: Prozessschritt.",
                    "- **Raute**: Entscheidungspunkt.",
                    "- **Kreis**: Start/Ende.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Technisch, prägnant",
                    "elements": ["Aufzählungspunkte"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Überzeugend, klar und strukturiert",
                    "elements": ["Überschriften", "Aufzählungspunkte", "Tabellen"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visuell, deskriptiv und modular",
                    "elements": ["mermaid", "Farben", "Anmerkungen", "Legende"],
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
                "Relevante technische Begriffe verwenden.",
                "Vorteile der Lösung hervorheben, um Stakeholder zu überzeugen.",
                "Klar strukturierten Umsetzungsplan einbeziehen.",
                "Risiken und Gegenmaßnahmen adressieren.",
                "Aufzählungspunkte und Überschriften zur besseren Lesbarkeit nutzen.",
                "Konkrete Beispiele oder Fallstudien zur Untermauerung liefern.",
                "Modularität und einfache Aktualisierbarkeit sicherstellen.",
                "Zusammenfassung des Mehrwerts im Fazit einbinden.",
            ],
            "needs": "Überzeugungskraft für Stakeholder, klarer technischer Ansatz, strukturierte Dokumentation und umsetzbare Erkenntnisse",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Thema] - Leitfaden",
                    "## [Abschnitt]",
                    "- **Konzept:** Erklärung mit praktischen Beispielen und Anwendungen.",
                ],
                "quick_ref": [
                    "**[Thema] - Kurzreferenz:**",
                    "- [Schlüsselpunkt]: Knappe, handlungsorientierte Zusammenfassung mit klarem Praxisbezug.",
                ],
                "timeline": [
                    "# 🎥 [Klasse] - Zeitstrahl",
                    "- **[MM:SS]** [Schlüsselkonzept oder Aktion]: [Kurze, klare Erklärung mit Ergebnissen oder Handlungen, unter Betonung realer Anwendungen].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Bildend, strukturiert, mit Beispielen für bessere Verständlichkeit",
                    "elements": [
                        "Unterabschnitte",
                        "Aufzählungspunkte",
                        "Beispiele",
                        "reale_Anwendungen",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Prägnant, praxisorientiert, für schnelles Lernen und Anwenden",
                    "elements": ["Aufzählungspunkte", "klare_Zusammenfassungen"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Chronologisch, handlungsorientiert, klar mit Fokus auf reale Anwendungen",
                    "elements": [
                        "Zeitstrahl",
                        "Schritt-für-Schritt-Aktionen",
                        "visuelle_Hinweise",
                        "realer_Kontext",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Klar verständliche, handlungsorientierte Erklärungen mit Beispielen liefern.",
                "Informationen prägnant aber umfassend halten, mit Fokus auf Praxisbezug.",
                "An Lernziele und Kontext anpassen, um Retention zu fördern.",
                "Klarheit und Nutzbarkeit betonen, besonders für reale Anwendungsfälle.",
            ],
            "needs": "Erleichterung des Lernens, schnelle Referenz und Video-Nachverfolgung mit praktischen Insights",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Projekt] - Chronik",
                    "- **[MM:SS]** Hervorgehobenes Element",
                ],
                "report": [
                    "**[Projekt] - Technischer Bericht:**",
                    "Absatz mit Schlüsseldetails",
                ],
                "list": ["# [Projekt] - Details", "- **Aspekt:** Beschreibung"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativ, visuell",
                    "elements": ["Zeitstrahl"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Technisch, detailliert",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Deskriptiv, organisiert",
                    "elements": ["Aufzählungspunkte"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Innovation oder Nachhaltigkeit hervorheben",
                "Technische Daten einbeziehen (falls zutreffend)",
                "Visuell ansprechend gestalten",
            ],
            "needs": "Technische Dokumentation, ansprechende Präsentation, Video-Nachverfolgung",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Zeitraum] - Finanzbericht",
                    "- **Indikator**: [Wert]",
                ],
                "table": [
                    "## [Zeitraum] - Finanzzusammenfassung",
                    "| **Indikator** | **Wert** |",
                ],
                "executive": [
                    "**[Zeitraum] - Executive Summary:**",
                    "Kurzer, prägnanter Absatz mit Schlüsselerkenntnissen.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analytisch, formal",
                    "elements": ["Aufzählungspunkte"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "Visuell, prägnant",
                    "elements": ["Tabelle"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Direkt, führungsorientiert",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Klarheit und Prägnanz bei der Präsentation von Kennzahlen gewährleisten.",
                "Mehrdeutigkeit in der Datenpräsentation vermeiden.",
                "Handlungsorientierte Erkenntnisse für Entscheidungsträger liefern.",
                "Tabellentitel müssen ohne Leerzeichen vor oder nach den doppelten Sternen formatiert sein.",
            ],
            "needs": "Umsetzbare Daten, klare visuelle Synthese und führungsorientierte Zusammenfassungen mit Fokus auf Impact",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Reiseziel] - Chronik",
                    "- **[MM:SS]** Initiative",
                    "- **[MM:SS]** Wichtiger Meilenstein",
                ],
                "report": [
                    "**[Reiseziel] - Richtlinien:**",
                    "Formaler Absatz mit Fokus auf Ziele des Reiseziels und Auswirkungen auf den Tourismus",
                ],
                "list": [
                    "# [Reiseziel] - Initiativen",
                    "- **Bereich:** Detail (lokale Kultur oder Attraktionen einbeziehen)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativ, ansprechend, immersiv",
                    "elements": ["Zeitstrahl", "Storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formell, informativ, objektiv",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Deskriptiv, klar, informativ",
                    "elements": ["Aufzählungspunkte", "prägnante_Fakten"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Nachhaltigkeit, kulturelle Bedeutung und touristische Attraktivität betonen",
                "Praktische Reiseinfos einbeziehen (z.B. beste Reisezeit, lokale Attraktionen, Notfallkontakte)",
                "Klar präsentierte Richtlinien und Initiativen beschreiben",
                "Übertreibungen vermeiden, realistisch und informativ bleiben",
            ],
            "needs": "Ansprechende Promotion mit informativen Highlights, klare Richtlinienpräsentation und praktische Reisende-fokussierte Details",
        },
        "requirements": {
            "structures": {
                "elicitation": [
                    "Anforderungen für [Projekt/Name] - Erhebung",
                    "Kontext",
                    "- Besprechung: [Datum, Teilnehmer, Ziel].",
                    "- Umfang: [Zweck oder erwartetes Ergebnis].",
                    "Funktionale Anforderungen",
                    "- FR-[ID]: [Klare Beschreibung]. (Priorität: [Hoch/Mittel/Niedrig], Begründung: [Kurzer Grund]).",
                    "Nichtfunktionale Anforderungen",
                    "- NFR-[ID]: [Beschreibung, z. B. Qualität, Timing]. (Priorität: [Hoch/Mittel/Niedrig], Begründung: [Grund]).",
                    "Abhängigkeiten und Einschränkungen",
                    "- Abhängigkeit: [Beziehung zu anderen Anforderungen/Ressourcen].",
                    "- Einschränkung: [Limitierungen, z. B. Budget, Zeit].",
                    "Offene Fragen",
                    "- [Zu klärende Frage]",
                    "Zeitstempel (falls zutreffend)",
                    "- [MM:SS]: [Kurzes Zitat aus der Quelle].",
                    "Priorisierungskriterien",
                    "- Hoch: Kritisch für den Erfolg oder dringend.",
                    "- Mittel: Wichtig, aber nicht wesentlich.",
                    "- Niedrig: Wünschenswert, aufschiebbar.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Klar, objektiv, anpassungsfähig",
                    "elements": ["bullet_points", "IDs", "priorities"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Anforderungen direkt extrahieren, ohne Interpretationen.",
                "IDs (FR-01, NFR-01) für Nachverfolgbarkeit verwenden.",
                "Mit Begründung priorisieren (Wirkung/Dringlichkeit).",
                "Klare Sprache verwenden, die auf das 'Was' fokussiert ist.",
                "Mehrdeutigkeiten unter 'Offene Fragen' auflisten.",
                "Zeitstempel nur für Schlüsselanforderungen.",
            ],
            "needs": "Klare Erfassung von Anforderungen für jedes Projekt, um Planung und Kommunikation zu erleichtern.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Thema] - Leitfaden",
                    "## [Abschnitt]",
                    "- **Konzept:** Definition, Prinzip, Beziehung, Prozess, Mechanismus, Klassifikation oder relevante Evidenz.",
                ],
                "formula_reference": [
                    "# 🔬 [Thema] - Formelreferenz",
                    "## Hauptformeln",
                    "| Formel | Bedeutung | Variablen | Einheiten | Bedingungen |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Thema] - Herleitung",
                    "## Ausgangspunkt",
                    "- [Definition, Prinzip, Gleichung, Beobachtung, Datum oder Anfangsbedingung, die in der Quelle vorhanden ist.]",
                    "## Entwicklung",
                    "1. [Erster Schritt oder Argumentation, die in der Quelle vorhanden ist.]",
                    "2. [Transformation, Beziehung, Verfahren oder Argumentation, die in der Quelle vorhanden ist.]",
                    "## Ergebnis",
                    "- **Ergebnis:** [Ergebnis oder Schlussfolgerung, die in der Quelle erzielt wurde.]",
                ],
                "quick_ref": [
                    "**[Thema] - Schnellreferenz:**",
                    "- **Konzept:** Kurze Definition.",
                    "- **Prinzip/Gesetz/Theorie:** Grundlegende Beziehung.",
                    "- **Prozess/Beziehung:** Wesentliche Beschreibung.",
                    "- **Datum/Formel:** Relevante quantitative Information.",
                    "- **Bedingung:** Anwendbarkeit oder Einschränkung.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Bildend, rigoros und strukturiert",
                    "elements": [
                        "Konzepte",
                        "Prinzipien",
                        "Gesetze",
                        "Theorien",
                        "Modelle",
                        "Prozesse",
                        "Mechanismen",
                        "Strukturen",
                        "Beziehungen",
                        "Daten",
                        "Formeln",
                        "Beispiele",
                        "Evidenz",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Technisch, kompakt und präzise, ausgerichtet auf korrekte Anwendung und Nachschlagewerk",
                    "elements": [
                        "Formeln",
                        "Variablen",
                        "Einheiten",
                        "Beziehungen",
                        "Bedingungen",
                        "Tabellen",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formal, logisch und rigoros, unter Bewahrung der tatsächlich von der Quelle gestützten Argumentation",
                    "elements": [
                        "Gleichungen",
                        "Verfahren",
                        "Ableitungen",
                        "Sequenzen",
                        "Argumentation",
                        "Annahmen",
                        "Bedingungen",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Prägnant, technisch und praktisch, für schnelle Überprüfung ohne Verlust wissenschaftlicher Präzision",
                    "elements": [
                        "Schlüsselkonzepte",
                        "Prinzipien",
                        "Gesetze",
                        "Theorien",
                        "Prozesse",
                        "Formeln",
                        "Daten",
                        "Bedingungen",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
            },
            "rules": [
                "Ausschließlich die in der Quelle vorhandenen Informationen verwenden.",
                "Kein externes Wissen einführen, auch wenn es wissenschaftlich korrekt, bekannt, offensichtlich oder nützlich ist, um die Erklärung zu vervollständigen.",
                "Keinen Inhalt erfinden, ergänzen, korrigieren oder umdeuten, der nicht von der Quelle gestützt wird.",
                "Die Strukturen sind nur ein Organisationsleitfaden und verpflichten nicht dazu, Inhalt zu erzeugen, um Abschnitte zu füllen.",
                "Einen Abschnitt nicht einbeziehen, wenn die Quelle nicht genügend Informationen enthält, um ihn zu rechtfertigen.",
                "Relevante Definitionen, Prinzipien, Gesetze, Theorien, Hypothesen, Modelle, Prozesse, Mechanismen, Klassifikationen, Beziehungen, Daten, Formeln, Variablen, Einheiten, Evidenz und Bedingungen der Quelle bewahren.",
                "Die ursprüngliche Bedeutung wissenschaftlicher Begriffe, Symbole, Variablen, Größen, Beziehungen, Prozesse und Mechanismen beibehalten.",
                "Eine Hypothese, ein Modell, eine Beobachtung, Korrelation, Assoziation oder ein experimentelles Ergebnis nicht in eine Tatsache, ein Gesetz oder eine von der Quelle nicht etablierte Kausalbeziehung verwandeln.",
                "Ergebnisse, Mechanismen oder Schlussfolgerungen nicht über die in der Quelle angegebenen Bedingungen, Population, System, Skala oder Kontext hinaus verallgemeinern.",
                "Ausnahmen, Grenzen, Annahmen, Einschränkungen, Unsicherheiten und Gültigkeitsbedingungen bewahren, wenn sie die Interpretation beeinflussen.",
                "Wenn quantitative Daten vorhanden sind, Werte, Einheiten, Beziehungen, Größenordnungen und relevante Präzision erhalten.",
                "Wenn Formeln oder mathematische Beziehungen vorhanden sind, Zeichen, Exponenten, Indizes, Operatoren, Variablen, Einheiten, Näherungen und Gültigkeitsbedingungen bewahren.",
                "Keine Umrechnungen, Berechnungen, algebraischen Transformationen oder zusätzlichen quantitativen Inferenzen durchführen, die nicht in der Quelle vorhanden oder eindeutig gestützt sind.",
                "Wenn eine Herleitung, Beweisführung, ein Verfahren, Experiment oder sequenzielles Denken vorhanden ist, nur die wesentlichen, tatsächlich von der Quelle gestützten Schritte behalten.",
                "Keine Zwischenschritte, Mechanismen, Ursachen oder Erklärungen hinzufügen, die die Quelle nicht darstellt oder nicht eindeutig festzulegen erlaubt.",
                "Zeitliche, kausale, funktionale, strukturelle und hierarchische Beziehungen bewahren, wenn sie zum korrekten Verständnis des Inhalts relevant sind.",
                "Korrelation nicht mit Kausalität und Assoziation nicht mit Mechanismus verwechseln.",
                "Keine Information eliminieren, deren Fehlen Bedeutung, Interpretation, Ergebnis oder Anwendungsbereich des Inhalts ändern könnte.",
                "Redundanzen und repetitive Formulierungen entfernen, ohne notwendige wissenschaftliche Information zu eliminieren.",
                "Die Erklärung reduzieren, nicht die Bedeutung.",
                "Im Konfliktfall in dieser Reihenfolge priorisieren: Treue zur Quelle, wissenschaftliche Genauigkeit, Bewahrung von Bedeutung und Bedingungen, Klarheit, Struktur und schließlich Prägnanz.",
                "Das Ziel ist es, das in der Quelle enthaltene Wissen kompakt und präzise darzustellen, nicht eine allgemeine Erklärung des Themas auf Basis externen Wissens zu liefern.",
            ],
            "needs": (
                "Maximale wissenschaftliche Treue und Präzision unter Bewahrung von Konzepten, "
                "Prozessen, Mechanismen, Beziehungen, Daten, Formeln, Evidenz, "
                "Bedingungen, Grenzen und wesentlicher Argumentation der Quelle, "
                "ohne externes Wissen einzuführen oder fehlende Informationen zu ergänzen."
            ),
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "Der Inhalt beschreibt am 08. März 2025 angekündigte Wirtschaftsmaßnahmen, inklusive Steuersenkungen und Kreditlinien."
        },
        "journalism": {
            "chronicle": (
                "# Apple-Event Live\n"
                "- **[00:03:00]** Tim Cook betritt die Bühne und stellt Apple Intelligence vor, ein neues KI-System für Apple-Geräte.\n"
                "- **[00:05:11]** Präsentation der Apple Watch Series 10 mit größerem Display und dünnerem Design.\n"
                "- **[00:07:03]** Demo des neuen OLED-Displays, 40% heller bei schrägem Blickwinkel.\n"
                "- **[00:09:06]** Series 10 ist 10% dünner als Series 9 (nur 9.7 mm).\n"
                "- **[00:10:19]** Schnellladung: 80% Akku in 30 Minuten.\n"
                "- **[00:11:03]** Polierte Titan-Optik, 20% leichter als Edelstahl.\n"
                "- **[00:12:00]** Nachhaltigkeit: 95% recyceltes Titan, 100% erneuerbare Energie in der Produktion.\n"
                "- **[00:13:50]** Neue Gesundheitsfunktionen: Schlafapnoe-Erkennung und Körpertemperatur-Monitoring für Ovulations-Tracking.\n"
                "- **[00:15:19]** 80% der Schlafapnoe-Fälle global unerkannt – Bedeutung der Funktion."
            ),
            "news_wire": (
                "[08. März 2025] - Hauptstadt - Präsident kündigt Wirtschaftsmaßnahmen an.\n"
                "### Wichtige Details\n"
                "- Steuersenkungen für Mittelstandsfamilien.\n"
                "- Erhöhte Infrastrukturausgaben.\n"
                "### Kontext\n"
                "- Maßnahmen sollen Wirtschaftswachstum bei steigender Inflation ankurbeln.\n"
                "### Statistiken\n"
                "- BIP-Wachstumsprognose 2025: 2.5%.\n"
                "- Arbeitslosenquote: 5.8% (gegenüber 6.3% im Vorjahr).\n"
                "### Auswirkungen\n"
                "- Kurzfristig: Entlastung für Mittelstandsfamilien.\n"
                "- Langfristig: Erwartete Stimulierung von Wachstum und Jobs."
            ),
            "analysis": (
                "## Steuerreform Vertiefung\n"
                "### Überblick\n"
                "- Die Reform senkt Steuern für Mittelstandsfamilien und erhöht Infrastrukturausgaben.\n"
                "### Schlüsselaspekte\n"
                "- **Steuersenkungen**: 10% weniger Steuern für Mittelstand – mehr verfügbares Einkommen und Konsum.\n"
                "- **Infrastruktur**: Mehr Jobs und bessere öffentliche Dienstleistungen.\n"
                "### Folgen\n"
                "- **Kurzfristig**: Höhere Kaufkraft und Wirtschaftsaktivität.\n"
                "- **Langfristig**: Stärkere Wirtschaft und bessere Infrastruktur.\n"
                "### Expertenmeinungen\n"
                "- „Ein wichtiger Schritt gegen Ungleichheit“, sagt Dr. Jane Doe, Harvard-Ökonomin.\n"
                "### Fazit\n"
                "- Ausgewogene Reform, deren Erfolg von der Umsetzung abhängt."
            ),
        },
        "marketing": {
            "highlights": "# ✨ EcoLife-Launch - Highlights\n🎯 **Zielgruppe:** Jugendliche.\n📈 **Verkäufe:** +15%.",
            "storytelling": (
                "## EcoLife - Eine Geschichte: Nachhaltigkeitsreise\n"
                "### Einleitung\n"
                "- Maria, eine junge Frau in einer hektischen Stadt, fühlt sich von Umweltproblemen überwältigt.\n"
                "### Hauptgeschichte\n"
                "- Sie entdeckt EcoLife, eine nachhaltige Marke, und ändert ihren Lebensstil.\n"
                "- Trotz anfänglichem Spott inspiriert ihr Engagement andere.\n"
                "### Emotionaler Impact\n"
                "- Kleine Veränderungen, große Wirkung – persönlich und ökologisch.\n"
                "### Handlungsaufforderung\n"
                "- Begleite Maria auf ihrer Reise – starte mit EcoLife!"
            ),
            "report": (
                "## EcoLife - Ergebnisse\n"
                "### Überblick\n"
                "- Kampagne zielte auf Markenbekanntheit und Verkäufe bei Jugendlichen durch Nachhaltigkeitspromotion.\n"
                "### Kennzahlen\n"
                "| **Metrik**       | **Ziel** | **Ist-Wert** | **Abweichung** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Verkaufsanstieg  | +15%     | +18%       | +3%          |\n"
                "| Social-Media-Reichweite | 1M      | 1.2M       | +200K        |\n"
                "### Analyse\n"
                "- Übererfüllte Ziele dank starker Social-Media-Präsenz und Influencer-Kooperationen.\n"
                "### Empfehlungen\n"
                "- Influencer-Partnerschaften fortsetzen.\n"
                "- Bildungsinhalte zu Nachhaltigkeit ausbauen.\n"
                "### Fazit\n"
                "- Erfolgreiche Kampagne als Grundlage für zukünftige Initiativen."
            ),
        },
        "health": {
            "report": "**Behandlung X - Klinischer Bericht:** Klinische Studien zeigen 70% weniger Symptome nach 8-wöchiger Behandlung.",
            "summary": "# 🩺 Behandlung X - Zusammenfassung\n📈 **Wirksamkeit:** 70%.\n| Woche | Fortschritt |\n| 8     | 70%       |",
            "case": "**Patient A - Klinischer Fall:** 62-jähriger Mann zeigt Besserung nach 2 Wochen.",
        },
        "technology": {
            "changelog": "# v3.0 - Update\n✨ **Neue Funktionen:**\n- OCR.\n🐛 **Korrekturen:**\n- Export.",
            "proposal": """
                    # Projekt X - Technischer Vorschlag

                    ## Einleitung
                    Automatisierte API-Integration zur Effizienzsteigerung der Datenverarbeitung.

                    ## Ziele
                    - Ziel 1: Manuelle Dateneingabe um 50% reduzieren.
                    - Ziel 2: Datenverarbeitungsgeschwindigkeit um 30% erhöhen.

                    ## Technischer Ansatz
                    Lösung nutzt Python mit Flask für APIs, Docker für Container und Kubernetes zur Orchestrierung.

                    ### Hauptfunktionen
                    - Funktion 1: Automatisierte Datenerfassung aus multiplen Quellen.
                    - Funktion 2: Echtzeit-Datenvalidierung und Fehlerbehandlung.

                    ## Vorteile
                    - **Effizienz**: Reduziert manuellen Aufwand und beschleunigt Prozesse.
                    - **Skalierbarkeit**: Bewältigt wachsende Datenmengen.
                    - **Kosteneinsparungen**: Automatisierung repetitiver Tasks.

                    ## Umsetzungsplan
                    1. **Phase 1**: API-Entwicklung und Tests (2 Wochen).
                    2. **Phase 2**: Deployment und Integration (3 Wochen).
                    3. **Phase 3**: Monitoring und Optimierung (1 Woche).

                    ## Risiken und Gegenmaßnahmen
                    - **Risiko 1**: API-Ausfall während des Deployments.
                    - **Gegenmaßnahme**: Rollierende Updates nutzen.
                    - **Risiko 2**: Datenvalidierungsfehler.
                    - **Gegenmaßnahme**: Automatisierte Tests implementieren.

                    ## Fazit
                    Die Lösung bietet signifikante Effizienz- und Kostenvorteile.
            """,
            "diagram": "# Benutzerauthentifizierung - Ablauf\n```mermaid\ngraph TD\n  A[Start] --> B{Eingeloggt?}\n  B -->|Ja| C[Dashboard anzeigen]\n  B -->|Nein| D[Zum Login weiterleiten]\n  C --> E[Ende]\n  D --> E\n```\n**Anmerkungen:**\n- **A**: Prozessstart.\n- **B**: Entscheidungspunkt.\n- **C/D**: Alternative Pfade.\n- **E**: Prozessende.\n**Farben:**\n- **Grün**: Erfolgspfad (eingeloggt).\n- **Rot**: Alternativer Pfad (nicht eingeloggt).\n**Legende:**\n- **Rechteck**: Prozessschritt.\n- **Raute**: Entscheidungspunkt.\n- **Kreis**: Start/Ende.",
        },
        "education": {
            "guide": "# 📚 [Thema] - Leitfaden\n## [Abschnitt]\n- **Konzept:** Erklärung mit Praxisbeispielen.",
            "quick_ref": "**[Thema] - Kurzreferenz:**\n- [Schlüsselpunkt]: Knappe, handlungsorientierte Zusammenfassung.",
            "timeline": "# 🎥 [Klasse] - Zeitstrahl\n- **[MM:SS]** [Schlüsselkonzept oder Aktion]: [Kurze Erklärung mit Ergebnissen oder Handlungen].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Grüner Turm - Chronik\n- **[01:15]** Nachhaltige Materialien.",
            "report": "**Grüner Turm - Technischer Bericht:** Design nutzt erneuerbare Energie.",
            "list": "# Grüner Turm - Details\n- **Materialien:** Recycelt.\n- **Energie:** Solar.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Finanzbericht\n- **Umsatz:** 5% Wachstum durch Technologiefortschritte und Marktexpansion.",
            "table": "## Q1 2025 - Finanzzusammenfassung\n| **Indikator** | **Wert** |\n|---------------|-----------|\n| Umsatz        | +5%       |",
            "executive": "**Q1 2025 - Executive Summary:** 5% Wachstum durch Technologie und strategische Expansion – stärkere Finanzperspektiven.",
        },
        "tourism": {
            "chronicle": "# 🌍 Blaue Bucht - Chronik\n- **[01:00]** Ökotourismus-Initiativen reduzieren Abfall.\n- **[05:00]** Wichtiger umweltfreundlicher Hotelbau.",
            "report": "**Blaue Bucht - Richtlinien:** Fördert Nachhaltigkeit durch Abfallreduktion und Ökotourismus. Lokale Regierung strebt CO2-Neutralität bis 2030 an.",
            "list": "# Blaue Bucht - Initiativen\n- **Ökologie:** Weniger Plastik, mehr Recycling.\n- **Touristische Attraktivität:** Ganzjährige Aktivitäten, Hauptsaison Mai bis September.",
        },
        "requirements": {
            "elicitation": """Anforderungen für Corporate Event 2025 - Erhebung
                Kontext
                - Besprechung: 20/09/2025, ABC-Marketingteam, Event für 500 Teilnehmer planen.
                - Umfang: Networking- und Produktlaunch-Event, im Budget.
                Funktionale Anforderungen
                - FR-01: Veranstaltungsort für 500 Personen mit Ständen. (Priorität: Hoch, Begründung: Kritisch für das Event).
                - FR-02: Online-Registrierung mit E-Mail. (Priorität: Mittel, Begründung: Erleichtert die Logistik).
                - FR-03: Keynote mit Gastredner. (Priorität: Hoch, Begründung: Zentral für das Event).
                Nichtfunktionale Anforderungen
                - NFR-01: Sicherheits- und Barrierefreiheitsstandards einhalten. (Priorität: Hoch, Begründung: Gesetzliche Pflicht).
                - NFR-02: Planung innerhalb von 2 Monaten. (Priorität: Hoch, Begründung: Fester Termin).
                Abhängigkeiten und Einschränkungen
                - Abhängigkeit: Veranstaltungsort erfordert Budgetfreigabe.
                - Einschränkung: Budget von 30.000 $.
                Offene Fragen
                - Ist Event-Streaming erforderlich?
                Zeitstempel
                - [03:15]: 'Großer Veranstaltungsort für 500 Personen mit Ständen'.
                - [08:20]: 'Die Keynote macht das Event unvergesslich'.
                Priorisierungskriterien
                - Hoch: Kritisch für den Erfolg oder dringend.
                - Mittel: Wichtig, aber nicht wesentlich.
                - Niedrig: Wünschenswert, aufschiebbar."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Thema] - Leitfaden\n"
                "## [In der Quelle vorhandener Abschnitt]\n"
                "- **Konzept:** Definition oder verdichtete Erklärung aus dem Quellininhalt.\n"
                "## [Weiterer in der Quelle vorhandener Abschnitt]\n"
                "- **Prozess:** In der Quelle beschriebene Sequenz oder Mechanismus.\n"
            ),
            "formula_reference": (
                "# 🔬 [Thema] - Formelreferenz\n"
                "## Hauptformeln\n"
                "| Formel | Bedeutung | Variablen | Einheiten | Bedingungen |\n"
                "|---|---|---|---|---|\n"
                "| [In der Quelle vorhandene Formel] | [In der Quelle angegebene Bedeutung] | [In der Quelle definierte Variablen] | [Angegebene Einheiten] | [Angegebene Bedingungen] |\n"
            ),
            "derivation": (
                "# 🔬 [Thema] - Herleitung\n"
                "## Ausgangspunkt\n"
                "- [Definition, Gleichung, Datum, Beobachtung oder Anfangsbedingung, die in der Quelle vorhanden ist.]\n"
                "## Entwicklung\n"
                "1. [Erster Schritt oder Transformation, die in der Quelle explizit gezeigt wird.]\n"
                "2. [Zweiter Schritt, Beziehung oder Argumentation, die in der Quelle explizit gezeigt wird.]\n"
                "## Ergebnis\n"
                "- **Ergebnis:** [Ergebnis oder Schlussfolgerung, die die Quelle explizit erzielt.]\n"
            ),
            "quick_ref": (
                "**[Thema] - Schnellreferenz:**\n"
                "- **Konzept:** [In der Quelle vorhandene Definition.]\n"
                "- **Prinzip/Gesetz/Theorie:** [Nur wenn es in der Quelle erscheint.]\n"
                "- **Prozess/Beziehung:** [In der Quelle beschriebener Prozess oder Beziehung.]\n"
                "- **Datum/Formel:** [In der Quelle vorhandenes Datum oder Formel.]\n"
                "- **Bedingung:** [In der Quelle angegebene Bedingung oder Einschränkung.]\n"
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
            f"# Prompt für {category.value.title()} - {style.value.title()}",
            f"**Ziel:** Erstelle Inhalte im Format {output_format.value.upper()}, optimiert für {category.value.title()}",
            f"**Stil:** {style.value.title()} ({style_info['tone']})",
            f"**Grundlegende Anforderungen:** {spec.get('needs', 'Anpassung an den Kontext')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "Verwenden Sie nicht die erste Person und geben Sie nicht vor, ein Student zu sein, der Notizen macht.",
            "Erfinden Sie keine Fragen, Zweifel, Schlussfolgerungen oder Daten, die nicht in der Quelle stehen.",
            "Die Ausgabe IST die Zusammenfassung. Niemals ein Hilfemenü, ein Cover oder Fragen an den Leser.",
            "Fügen Sie unter keinen Umständen die ```markdown-Kennzeichnung ein. Wenn Sie Codeblöcke verwenden, müssen sie nicht spezifiziert sein oder eine andere Sprache als Markdown verwenden.",
            "Vermeiden Sie allgemeine Phrasen wie „Der Text ist jetzt frei von Wiederholungen und bleibt klar und kohärent.“ Konzentrieren Sie sich auf konkrete und spezifische Rückmeldungen.",
            "Fügen Sie keine Phrasen wie „Hier ist der überarbeitete Text, Redundanzen und Wiederholungen wurden entfernt, alle Details und die ursprüngliche Struktur bleiben erhalten.“ ein.",
            "Ab sofort antworten Sie nur auf Deutsch, unabhängig von der Sprache der ursprünglichen Frage.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Anweisungen: Extrahieren Sie die charakteristischen Fakten aus diesem Fragment.
            WICHTIG: Sie verarbeiten NUR EINEN TEIL (Chunk) eines viel größeren Dokuments.
            - Schreiben Sie Überschriften, Listen und Prosa auf Deutsch. Andere Sprachen nur in Code oder Eigennamen.
            - Erzeugen Sie KEINE globale Einleitung und KEINEN globalen Schluss.
            - Beginnen Sie Nummerierungshierarchien NICHT neu (z. B. ## 1. Einleitung).
            - Erzeugen Sie KEIN eigenständiges Dokument.
            - Extrahieren Sie aus DIESEM Fragment gemäß der Zusammenfassungsstufe: Definitionen und zentrale Fakten immer;
              Beispiele, Zahlen und Anekdoten nur in der Dichte der Längenanweisung.
            - Die Zusammenfassungsstufe steuert die Detaildichte, nicht ob ein hier vorhandenes Hauptthema weggelassen werden darf.
            - KRITISCHE PRIORITÄT: bewahren Sie die Natur der Sprache oder des Systems (z. B. interpretiert vs. kompiliert,
              Client vs. Server, statisch vs. dynamisch) mit demselben Gewissheitsgrad wie die Quelle.
            - Wenn der Text statische und dynamische Seiten gegenüberstellt, definieren Sie BEIDE.
            - Wenn behauptet wird, etwas sei nur theoretisch multiplattformfähig, behalten Sie diese Einschränkung (machen Sie daraus keinen absoluten Fakt).
            - Behalten Sie Vergleichstabellen oder Listen Punkt für Punkt (reduzieren Sie sie nicht auf „es gibt Unterschiede“).
            - Bewahren Sie Namen von Tools, Dateipfaden, numerischen Konstanten, Formeln und Codezitaten.
            - Bewahren Sie Bedingungen, Ausnahmen und Einschränkungen (theoretisch, kann, nur wenn, impliziert nicht…).
            - Bewahren Sie Syntax, Formeln und Beispiele genau so, wie sie in diesem Fragment erscheinen.
            - Unterscheiden Sie ein Inhaltsverzeichnis oder einen Index von hier tatsächlich ausgearbeitetem Inhalt.
            - Wenn dieses Fragment ein Index ist, beschreiben Sie es als Index (welche Einheiten existieren) und extrahieren Sie diese Einheiten NICHT so, als hätte dieses Fragment sie ausgearbeitet.
            - Behandeln Sie im Index genannte Lektionen nicht als erklärt, wenn dieses Fragment sie nicht ausarbeitet.
            - Nennen Sie nur Tools, Bibliotheken, APIs, Editoren und URLs, die wörtlich in diesem Fragment erscheinen.
            - Verwenden Sie nicht die erste Person. Erfinden Sie keine Fragen und kein Lerntagebuch.
            - Die Ausgabe IST der Extrakt. Niemals ein Hilfemenü, Buchcover, Fragen an den Leser oder „was brauchen Sie?“.
            - Dies ist ein dichter Extrakt für spätere Synthese, kein winziges eigenständiges Resümee.
            - Nutzen Sie das verfügbare Ausgabebudget für charakteristische Fakten; hören Sie nicht früh auf, wenn wichtige Details bleiben.
            - Bereiten Sie den Inhalt so vor, dass er für eine spätere globale Synthese nützlich ist.
            - Fügen Sie KEIN externes Wissen und keine Informationen hinzu, die nicht im Text stehen.
            - Erzeugen Sie KEIN Inhaltsverzeichnis und KEINEN Index.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "Sie sind ein Expertenredakteur. Ihre Aufgabe ist es, die bereitgestellten Textblöcke "
            "zu einem einheitlichen Text zu INTEGRIEREN.\n\n"
            "VERPFLICHTENDE REGELN:\n"
            "- KEIN FÜLLTEXT: Fügen Sie KEINE unnötigen Übergangssätze, generischen Einleitungen oder Schlüsse hinzu. "
            "Kommen Sie direkt zum Punkt.\n"
            "- STRIKTE DEDUPLIZIERUNG: Eliminieren Sie jedes Konzept, jede Idee oder jedes Argument, das über Blöcke hinweg wiederholt wird.\n"
            "- EINHEITLICHE STRUKTUR: Konsolidieren Sie den Inhalt unter einer einzigen Hierarchie. Entfernen Sie redundante Überschriften, "
            "aber BEHALTEN Sie unterschiedliche Abschnittssthemen, die verschiedene Teile der Quelle darstellen.\n"
            "- STRIKTE TREUE: Bewahren Sie absolute Treue. Erfinden Sie KEINE Fakten und fügen Sie kein externes Wissen hinzu.\n"
            "- ABDECKUNG ZUERST: Jeder Quellblock mit substantiellem Inhalt muss vertreten sein. "
            "Die Zusammenfassungsstufe steuert die Detaildichte, nicht ob ein Hauptthema verschwinden darf.\n"
            "- NICHT UNTER DAS ZIEL KOMPRIMIEREN: Zusammenführen und Duplikate entfernen. "
            "Wenn die Längenanweisung mehr Wörter verlangt als die Eingabe hat, "
            "behalten Sie ALLEN verbleibenden nicht-redundanten Inhalt; kürzen Sie nicht weiter und erfinden Sie keinen Fülltext.\n"
            "- LÄNGENANWEISUNG BEACHTEN: Wenn eine Längenanweisung vorliegt, folgen Sie ihr. "
            "Weit unter dem Ziel zu bleiben und dabei Hauptthemen zu streichen ist ein Fehler.\n"
            "- Die Ausgabe IST die einheitliche Zusammenfassung. Niemals ein Assistent, Optionsmenü, Cover-Blurb, "
            "Fragen an den Leser oder „was brauchen Sie?“.\n"
            "- VERBOTEN: erste Person, Lerntagebücher, erfundene Fragen, "
            "Abschnitte „was ich gelernt habe“ oder „zu klärende Punkte“.\n"
            "- Der Index ist kein ausgearbeiteter Inhalt: fassen Sie keine Einheiten, Beispiele oder APIs zusammen, "
            "die nur im Inhaltsverzeichnis erscheinen, wenn der Dokumentkörper sie nicht erklärt.\n"
            "- Nennen Sie nur Tools, Bibliotheken, APIs, Editoren und URLs, die wörtlich in den Blöcken erscheinen.\n"
            "- Erwähnen Sie nicht „Block 1“ oder interne Pipeline-Labels.\n"
            "- Erfinden Sie keine ISBN, Buchtitel oder Java/JVM-Vergleiche, die die Quelle nicht macht.\n"
            "- SPRACHE: schreiben Sie die GESAMTE Zusammenfassung auf Deutsch. Übersetzen Sie Blöcke, die auf Spanisch oder in einer anderen Sprache sind. "
            "Andere Sprachen nur in Zitaten, Code oder Eigennamen.\n"
            "- Ein Block, der „NUR INDEX“ sagt oder Einheiten/Seiten auflistet, ohne sie zu erklären, "
            "ist NUR ein Index: VERWERFEN SIE IHN. Erwähnen Sie ihn nicht in der Endzusammenfassung. "
            "Listen Sie keine Indexeinheiten auf. Widmen Sie die Zusammenfassung tatsächlich ausgearbeitetem Inhalt.\n"
            "- BEWAHREN OHNE ZU VERWÄSSERN: Toolnamen, Dateien, numerische Konstanten, "
            "Punkt-für-Punkt-Vergleiche und Gewissheitseinschränkungen (theoretisch, kann, impliziert nicht, nur wenn).\n"
            "- KEIN Token-Padding: klonen Sie keine Abschnitte, paraphrasieren Sie denselben Block nicht mehrmals, "
            "erfinden Sie keine Tools, APIs, Editoren oder Runtimes, die nicht in der Quelle stehen.\n"
            "- Wenn ein Thema bereits geschrieben ist, schreiben Sie es nicht erneut. "
            "- Prioritätsreihenfolge: Faktentreue, Abdeckung, Vollständigkeit, Kohärenz, Struktur, dann Prägnanz. "
            "Prägnanz darf die Abdeckung nicht zerstören."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Verfügbare Stile und Töne:**"

    def get_semantic_profile_title(self) -> str:
        return "**Semantisches Profil (zu bewahrende Informationen):**"

    def get_length_instruction_title(self) -> str:
        return "**Längenanweisung:**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Drücken Sie die Hauptthese, wesentliche Schlussfolgerungen und zentrale Konzepte "
                "stark verdichtet aus. Behalten Sie jeden großen Pfeiler. "
                "Lassen Sie sekundäre Beispiele, Anekdoten, Lesetipps und kleinere Nuancen weg."
            ),
            SummaryLevel.CONCISE: (
                "Bewahren Sie Hauptargumente, wesentliche Begründungen und die primäre thematische Struktur. "
                "Seien Sie direkt; kürzen Sie sekundäre Ausarbeitung, ohne wichtige Abschnitte zu streichen."
            ),
            SummaryLevel.MODERATE: (
                "Bewahren Sie Argumente, Begründungen, relevante Belege, repräsentative Beispiele "
                "und wichtige Taxonomien."
            ),
            SummaryLevel.DETAILED: (
                "Bewahren Sie Unterthemen, Methodik, Belege, Implikationen, vollständige Taxonomien "
                "und Beziehungen zwischen Konzepten."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Bewahren Sie Details einschließlich Ausnahmen, Nuancen, Einzelfälle, Kontext "
                "und formal relevante Besonderheiten. "
                "In technischen Tutorials: lassen Sie Definitionen der Systemnatur "
                "(interpretiert/kompiliert, Client/Server), Vergleichstabellen, Toolnamen, "
                "Beispieldateien, numerische Konstanten oder Beispielbedingungen nicht weg."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "LÄNGE / DICHTE: Erzeugen Sie eine Zusammenfassung, die sichtbar kürzer ist als moderate. "
                "Behalten Sie These, Pfeiler und zentrale Definitionen. "
                "Lassen Sie sekundäre Beispiele, Anekdoten, Leseempfehlungen und jede Anmerkung zu einem Index weg. "
                "Höchstens ein kurzes Beispiel pro Pfeiler, und nur wenn es die Definition klärt. "
                "Kürzer als moderate zu sein ist korrekt, wenn Hauptthemen erhalten bleiben. "
                "Streichen Sie keinen Pfeiler; kopieren Sie nicht jedes Beispiel der Stufe moderate. "
                "Bevorzugen Sie dichte Formulierung gegenüber dem Auflisten jedes Falls."
            ),
            SummaryLevel.CONCISE: (
                "LÄNGE / DICHTE: Erzeugen Sie eine kurze Zusammenfassung, länger als very_concise und kürzer als moderate. "
                "Bevorzugen Sie kompakte Formulierung gegenüber dem Löschen wichtiger Abschnitte. "
                "Ein repräsentatives Beispiel pro Hauptthema reicht."
            ),
            SummaryLevel.MODERATE: (
                "LÄNGE / DICHTE: Erzeugen Sie eine Zusammenfassung mittlerer Länge, sichtbar länger als very_concise "
                "und kürzer als very_detailed. "
                "Behalten Sie ein repräsentatives Beispiel pro Hauptkonzept mit charakteristischen Zahlen oder Namen aus der Quelle. "
                "Kopieren Sie nicht jeden Fall oder jede Anekdote."
            ),
            SummaryLevel.DETAILED: (
                "LÄNGE / DICHTE: Erzeugen Sie eine detaillierte Zusammenfassung, länger als moderate. "
                "Nehmen Sie den nötigen Raum für Unterthemen, Belege und mehrere Quellbeispiele."
            ),
            SummaryLevel.VERY_DETAILED: (
                "LÄNGE / DICHTE: Erzeugen Sie eine Zusammenfassung, die sichtbar länger ist als moderate. "
                "Behalten Sie jedes Beispiel, jede Zahl, jeden Namen, jede Ausnahme und Bedingung, die im Quellkörper ausgearbeitet ist. "
                "Komprimieren Sie diese charakteristischen Fakten nicht. "
                "Füllen Sie niemals auf, indem Sie Absätze wiederholen, Abschnitte klonen, den Index zitieren "
                "oder externes Wissen hinzufügen."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "ABDECKUNGSGARANTIE (gilt für jede Zusammenfassungsstufe): "
            "Hauptideen, wesentliche Konzepte, wichtige Abschnittsthemen und zentrale Begriffe MÜSSEN erhalten bleiben. "
            "Die Zusammenfassungsstufe steuert nur Detaildichte und sekundäre Ausarbeitung. "
            "Sie erlaubt niemals, einen Hauptabschnitt oder die Kernthese des Dokuments zu streichen."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Abdeckungs-Checkliste (nur wenn der Abschnitt in den Blöcken AUSGEARBEITET ist, "
            "nicht wenn er nur in einem Index erscheint):**\n"
            f"{lines}\n"
            "Erfinden Sie nicht den Inhalt einer Überschrift, die die Blöcke nicht erklären."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Abschlussanweisung:** "
            "Decken Sie die besonderen Fakten DIESES Fragments in der Dichte der Längenanweisung ab. "
            "Nutzen Sie das verfügbare Ausgabebudget für diese Fakten; hören Sie nicht früh auf, wenn wichtige Details bleiben. "
            "Wiederholen Sie keine Absätze zum Auffüllen. "
            "Beenden Sie immer mit einem vollständigen Satz."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "Indexeinträge"
        return (
            "NUR INDEX — dieses Fragment ist ein Inhaltsverzeichnis, keine ausgearbeiteten Lektionen. "
            f"Liste: {listed}. "
            "Stellen Sie diese Einträge nicht so dar, als hätte das Dokument sie hier erklärt."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "Sie sind ein Experte für Dokumentensynthese. Fassen Sie das gesamte Dokument "
            "in einem Durchgang zusammen. Bewahren Sie wichtige konzeptionelle Struktur "
            "(relevante Titel/Abschnitte), Hauptideen, Definitionen, "
            "Verfahren, Beispiele und zentrale Begriffe. "
            "Geben Sie sauberes Markdown aus. Erfinden Sie keinen Inhalt. "
            "Schreiben Sie kein Lerntagebuch und keine Fragenlisten.\n"
            "Der Index oder das Inhaltsverzeichnis IST KEIN ausgearbeiteter Inhalt: "
            "erwähnen Sie ihn nur als Index; stellen Sie Einheiten oder Beispiele aus dem Index nicht so dar, "
            "als hätte der Dokumentkörper sie erklärt.\n"
            "KRITISCHE PRIORITÄT: bewahren Sie die Sprachnatur (interpretiert/kompiliert), "
            "die Ausführungsumgebung (Client/Server), den Kontrast statisch/dynamisch, "
            "Vergleichstabellen, Toolnamen, Dateien, numerische Konstanten "
            "und Gewissheitseinschränkungen (theoretisch, kann, impliziert nicht, nur wenn).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "Sie sind ein Formatierungsredakteur. Ihre einzige Aufgabe ist es, Markdown-Formatierung "
            "auf den bereitgestellten Text anzuwenden.\n\n"
            "Fassen Sie NICHT zusammen, kürzen, erweitern, reinterpretieren oder lassen Sie Informationen weg.\n"
            "Fügen Sie KEINE Einleitung, keinen Schluss, keinen globalen Titel und kein externes Wissen hinzu.\n"
            "Bewahren Sie Reihenfolge, Listen, Tabellen, Code, URLs und Fachbegriffe.\n"
            "Wenn eine Formatierungsbeschränkung mit der Informationsbewahrung kollidiert, bewahren Sie die Information."
        )

    def get_format_strict_rules(self) -> str:
        return """
KRITISCHE FORMATIERUNGSREGELN:
1. Sie müssen alle Informationen der Eingabe bewahren.
2. Lassen Sie keinen Abschnitt, Absatz, Listenpunkt, Tabelle, Codebeispiel, URL, Fachbegriff oder faktische Aussage weg.
3. Fassen Sie nicht zusammen, kürzen, erweitern, reinterpretieren oder fügen Sie Informationen hinzu.
4. Ihre Aufgabe ist nur die Formatierung.
5. Die Ausgabe muss alle Quellinformationen enthalten und die Originalreihenfolge bewahren.
6. Wenn Formatierungsbeschränkungen mit der Informationsbewahrung kollidieren, hat die Bewahrung Vorrang.
7. Verwenden Sie niemals externes Wissen.
8. Ergänzen Sie niemals fehlende Informationen.
9. Erfinden Sie niemals Beispiele oder Erklärungen.
10. Geben Sie NUR die formatierte Version der Eingabe aus. Fügen Sie KEINEN Titelkopf hinzu. Fügen Sie KEINE „Einleitung“ hinzu. Fügen Sie KEINE Schlüsse hinzu. Erfinden Sie KEINE Abschnittsüberschriften.
11. Bewahren Sie die Absatzstruktur; setzen Sie nicht vor jeden Absatz Aufzählungszeichen, es sei denn, die Eingabe tut das bereits.
12. Wenn nicht alles passt, geben Sie so viel wie möglich aus und STOPPEN Sie an einer Satzgrenze. Geben Sie niemals „[texto truncado]“ oder ähnliche Platzhalter aus.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Bitte wenden Sie Format und Stil gemäß den Anweisungen auf den folgenden Text an. "
            "Fassen Sie NICHT zusammen und lassen Sie KEINE Informationen weg:\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nWICHTIG: Dies ist BLOCK 1 von {total} in einem mehrteiligen Dokument. "
                "Formatieren Sie diesen Abschnitt als ERÖFFNUNG des Dokuments. "
                "Sie DÜRFEN eine Einleitung einfügen, wenn der Inhalt es rechtfertigt. "
                "Fügen Sie KEINEN Schluss und keine Abschlussbemerkungen hinzu."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nWICHTIG: Dies ist BLOCK {idx} von {total} (LETZTER BLOCK) in einem mehrteiligen Dokument. "
                "Formatieren Sie diesen Abschnitt als ABSCHLUSS des Dokuments. "
                "Sie DÜRFEN einen Schluss einfügen, wenn der Inhalt es rechtfertigt. "
                "Fügen Sie KEINE neue Einleitung hinzu und starten Sie die Nummerierung nicht neu."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nWICHTIG: Dies ist BLOCK {idx} von {total} (MITTLERER BLOCK) in einem mehrteiligen Dokument. "
            "Formatieren Sie dies als FORTSETZUNG des Dokuments. "
            "Fügen Sie KEINE Einleitung, KEINEN Schluss hinzu und starten Sie die Abschnittsnummerierung nicht neu."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Verarbeiten Sie die folgenden Textblöcke. "
            "Schreiben Sie die vereinheitlichte Ausgabe nur auf Deutsch; übersetzen Sie alle Blöcke, die auf Spanisch oder in einer anderen Sprache geschrieben sind. "
            "Wenn ein Block nur ein Index ist, ignorieren Sie ihn vollständig; erwähnen Sie ihn nicht.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Block {block_index} (Fragmente: {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "KRITISCHE ANWEISUNG: Sie sind ein Zwischenschritt der Reduktion. "
            "Führen Sie die bereitgestellten Blöcke zusammen und deduplizieren Sie sie. "
            f"Ziel-Restlänge: etwa {pct}% der Eingabe (~{target_words} Wörter). "
            f"Schreiben Sie mindestens {min_words} Wörter. Komprimieren Sie NICHT wesentlich unter dieses Ziel. "
            "Wiederholen Sie keine Absätze zum Auffüllen. "
            "Bewahren Sie charakteristische Namen, Beispiele, Slogans, Schlussfolgerungen und bibliografische Fakten aus JEDEM Block. "
            "Verwerfen Sie nur wiederholte Formulierungen und wortreiche Umschreibungen. Erfinden Sie keinen Inhalt.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "KRITISCHE ANWEISUNG: Sie sind der FINALE Syntheseschritt. "
            "Integrieren Sie die Blöcke zu einer einzigen Zusammenfassung auf Deutsch, ohne Abschnitte zu duplizieren. "
            f"Abdeckungsuntergrenze: behalten Sie mindestens ~{min_words} Wörter nicht-redundanten Inhalts "
            f"(Ziel ~{target_words}), wenn die Blöcke ihn enthalten. "
            "Wenn die Blöcke weniger als das Ziel haben, behalten Sie ALLEN charakteristischen Inhalt; "
            "komprimieren Sie nicht weiter und erfinden Sie keinen Fülltext, um die Zahl zu erreichen. "
            "Wenn die Blöcke mehr haben, führen Sie Duplikate zusammen, löschen Sie aber keine Themen, Zahlen, Namen oder Beispiele. "
            "Ein Index ist kein ausgearbeiteter Inhalt: lassen Sie diese Blöcke weg und erwähnen Sie nicht, dass ein Index existiert. "
            "Stellen Sie keine Einheiten, Beispiele oder APIs dar, die nur im Inhaltsverzeichnis erscheinen. "
            "Nennen Sie nur Tools und APIs, die in den Blöcken stehen.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        """Instruction prepended when REDUCE final output fails the quality gate."""
        return (
            "KRITISCH: Schreiben Sie die Zusammenfassung selbst. Niemals ein Hilfemenü, eine Assistentenbegrüßung, "
            "ein Buchcover oder Fragen an den Leser.\n\n"
        )
