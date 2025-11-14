from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


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
                "Kurz und prägnant zusammenfassen, Redundanzen entfernen",
                "Originaltitel (falls vorhanden) unverändert beibehalten, exakte Formulierung und Formatierung verwenden (z.B. # Titel, ## Untertitel)",
                "Vollständig an Ton, Absicht und implizite Struktur des Quellinhalts anpassen",
                "Keine Titel, Untertitel oder Überschriften einführen, sofern nicht im Originaltext vorhanden",
                "Schlüsselbeispiele oder Konzepte im Originalformat belassen (z.B. Listen, Code, Kursivschrift)",
                "Subjektive Interpretationen oder unnötige Änderungen vermeiden",
                "Einzelnen, fortlaufenden Textblock erstellen, sofern der Originalinhalt nichts anderes vorsieht",
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
            "Vermeide allgemeine Formulierungen wie „Der Text ist jetzt frei von Wiederholungen und bleibt klar und kohärent.“ Konzentriere dich auf konkrete und spezifische Rückmeldungen.",
            "Enthalten Sie keine Formulierungen wie „Hier ist der überarbeitete Text, Redundanzen und Wiederholungen wurden entfernt, alle Details und die ursprüngliche Struktur bleiben erhalten.“",
            "Füge unter keinen Umständen die ```markdown-Kennzeichnung ein. Wenn Codeblöcke verwendet werden, müssen sie nicht spezifiziert sein oder eine andere Sprache als Markdown verwenden.",
            f"Ab sofort bitte nur auf Deutsch antworten, unabhängig von der ursprünglichen Sprache der Frage.",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- Fasse das Dokument umfassend zusammen, hebe die Hauptthemen, Schlüsselpunkte und das allgemeine Ziel in etwa {word_limit} Wörtern hervor."

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            Kontext des vorherigen Textes: {previous_context}\n
            Anweisungen: Gib eine detaillierte Zusammenfassung des folgenden Textes, wobei neue Informationen kohärent in den vorherigen Kontext integriert werden.
            Füge Beispiele, Erklärungen und alle Details hinzu, die das Studium des Themas erleichtern.
            Organisiere die Zusammenfassung in Abschnitte oder Hauptpunkte, um das Verständnis zu erleichtern."""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""Du bist ein erfahrener Editor, der Texte durch das Entfernen von Redundanzen verbessert.
            Überprüfe die folgende Zusammenfassung und entferne nur wiederholte oder redundante Informationen,
            wie wiederholte Texte, Phrasen oder Ideen.
            Vereinfache, reduziere oder kürze den Inhalt in keiner Weise; behalte alle Details, Daten und wichtigen Elemente unverändert.
            Stelle sicher, dass der endgültige Text klar, kohärent und gut strukturiert ist, ohne seine Struktur oder ursprüngliche Bedeutung zu verändern."""
        return prompt
