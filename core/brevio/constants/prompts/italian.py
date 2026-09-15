from typing import Any, Dict, Sequence

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel


class ItalianPrompts:
    INSTRUCTIONS_TITLE: str = "**Istruzioni:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Lingua specifica:** Italiano"
    SPECIFIC_LANGUAGE: str = (
        "Da ora in poi, tutte le risposte devono essere esclusivamente in italiano."
    )
    EXAMPLE_TITLE: str = "**Esempio**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["Sintesi diretta senza titoli aggiuntivi"]},
            "styles": {
                "default": {
                    "tone": "Neutrale, adattato al contesto",
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
                "Riassumere il contenuto della fonte: temi, definizioni, fatti, procedure ed esempi importanti",
                "Scrivere in terza persona. Prima persona vietata (ho imparato, ho bisogno di chiarire, mi aiuterebbe)",
                "Non inventare domande, esercizi, dubbi né sezioni di 'punti da chiarire' / 'cosa ho imparato'",
                "Non trasformare il documento in un diario di apprendimento né in compiti da studente",
                "Preservare il titolo originale se presente, senza modifiche, con la sua formulazione e formato esatti (es.: # Titolo, ## Sottotitolo)",
                "Usare intestazioni solo se il documento originale ha sezioni reali equivalenti",
                "Mantenere esempi o concetti chiave nel loro formato originale (es.: elenchi, codice, corsivo)",
                "Non aggiungere conoscenza esterna né affermazioni non supportate dalla fonte",
            ],
            "needs": "Semplicità e fedeltà al contenuto originale",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [Evento] in Diretta",
                    "- **[MM:SS]** Dichiarazione o dato chiave",
                    "- **[MM:SS]** Descrizione di un momento chiave o sviluppo",
                    "- **[MM:SS]** Reazione o analisi dell'evento",
                ],
                "news_wire": [
                    "[Data] - [Luogo] - Sintesi breve e diretta",
                    "### Dettagli Chiave",
                    "- [Fatto chiave 1]",
                    "- [Fatto chiave 2]",
                    "### Contesto",
                    "- [Informazioni di background]",
                    "### Statistiche (se applicabile)",
                    "- [Statistica 1]",
                    "- [Statistica 2]",
                    "### Impatto",
                    "- [Impatto a breve termine]",
                    "- [Implicazioni a lungo termine]",
                ],
                "analysis": [
                    "## [Argomento] Approfondimento",
                    "### Panoramica",
                    "- [Breve riassunto dell'argomento]",
                    "### Aspetti Chiave",
                    "- [Aspetto 1]: [Analisi dettagliata]",
                    "- [Aspetto 2]: [Analisi dettagliata]",
                    "### Implicazioni",
                    "- [Implicazioni a breve termine]",
                    "- [Implicazioni a lungo termine]",
                    "### Opinioni degli Esperti",
                    "- [Citazione o prospettiva di un esperto]",
                    "### Conclusione",
                    "- [Riassunto dei risultati chiave e prospettive future]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, urgente",
                    "elements": ["cronologia", "momenti chiave", "reazioni"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "Diretto, informativo",
                    "elements": [
                        "dettagli chiave",
                        "contesto",
                        "statistiche",
                        "impatto",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "Riflessivo, contestuale",
                    "elements": [
                        "panoramica",
                        "aspetti chiave",
                        "implicazioni",
                        "opinioni esperti",
                        "conclusione",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Includere timestamp precisi per le cronache",
                "Citare le fonti se applicabile",
                "Evitare opinioni nelle notizie flash",
                "Usare punti elenco per i dettagli chiave nelle notizie flash",
                "Includere almeno una statistica o dato nelle notizie flash",
                "Evidenziare sia gli impatti a breve che a lungo termine nelle notizie flash",
                "Per le cronache, focalizzarsi su momenti chiave e reazioni in tempo reale",
                "Per le analisi, fornire un'esplorazione dettagliata dell'argomento, incluse cause, effetti e prospettive esperte",
            ],
            "needs": [
                "Velocità per le notizie flash, dettaglio per le cronache, contesto per le analisi"
            ],
        },
        "marketing": {
            "structures": {
                "highlights": [
                    "# ✨ [Campagna] - Punti Salienti",
                    "🎯 **Chiave:** Valore",
                ],
                "storytelling": [
                    "## [Marca] - Una Storia: [Titolo]",
                    "### Introduzione",
                    "- [Aggancio emotivo o ambientazione]",
                    "### Narrativa Principale",
                    "- [Evento chiave o punto di svolta]",
                    "- [Sfide o conflitti]",
                    "- [Risoluzione o risultato]",
                    "### Impatto Emotivo",
                    "- [Come la storia fa sentire il pubblico]",
                    "### Call to Action",
                    "- [Incoraggiamento a interagire con il brand o prodotto]",
                ],
                "report": [
                    "## [Campagna] - Risultati",
                    "### Panoramica",
                    "- [Breve riassunto della campagna e dei suoi obiettivi]",
                    "### Metriche Chiave",
                    "| **Metrica** | **Obiettivo** | **Effettivo** | **Varianza** |",
                    "|------------|----------|------------|--------------|",
                    "| [Metrica 1] | [Obiettivo 1] | [Effettivo 1] | [Varianza 1] |",
                    "| [Metrica 2] | [Obiettivo 2] | [Effettivo 2] | [Varianza 2] |",
                    "### Analisi",
                    "- [Analisi dettagliata dei risultati, inclusi successi e sfide]",
                    "### Raccomandazioni",
                    "- [Raccomandazioni attuabili basate sui dati]",
                    "### Conclusione",
                    "- [Riassunto dei risultati chiave e prossimi passi]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "Coinvolgente, visivo",
                    "elements": ["emoji", "punti elenco"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "Emotivo, immersivo",
                    "elements": ["narrativa", "aggancio_emotivo", "call_to_action"],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "Analitico, chiaro",
                    "elements": ["tabella", "analisi", "raccomandazioni"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Usare linguaggio coinvolgente per punti salienti e storytelling",
                "Includere KPI nei report",
                "Evitare tecnicismi eccessivi",
                "Per lo storytelling, focalizzarsi su connessione emotiva e flusso narrativo",
            ],
            "needs": "Impatto visivo, connessione emotiva, dati attuabili",
        },
        "health": {
            "structures": {
                "report": [
                    "**[Studio/Trattamento] - Report Clinico:**",
                    "Paragrafo tecnico conciso e basato sui dati, focalizzato su risultati ed efficacia",
                ],
                "summary": [
                    "# 🩺 [Argomento] - Riassunto",
                    "📈 **Indicatore:** Risultato",
                    "| Settimana | Progresso |",
                ],
                "case": ["**[Paziente] - Caso Clinico:**", "Narrazione dettagliata"],
            },
            "styles": {
                "report": {
                    "tone": "Formale, preciso e basato su evidenze",
                    "elements": ["dati_quantitativi", "risultati_clinici"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "Visivo, accessibile",
                    "elements": ["punti elenco", "tabella"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "Narrativo, clinico",
                    "elements": ["narrazione"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "Includere sempre dati quantitativi e misurabili quando disponibili",
                "Mantenere rigore scientifico ed evitare linguaggio soggettivo",
                "Adattare complessità linguistica al pubblico (tecnico per medici, semplificato per pazienti)",
                "Garantire chiarezza, accuratezza e accessibilità delle informazioni mediche",
            ],
            "needs": {
                "doctors": "Dati clinici chiari e precisi per decisioni informate",
                "patients": "Spiegazioni accessibili e comprensibili di condizioni e trattamenti",
                "researchers": "Informazioni robuste e basate sui dati per l'analisi",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [Versione] - Aggiornamento",
                    "✨ **Nuove Funzionalità:**",
                    "- Funzionalità",
                    "🐛 **Correzioni:**",
                    "- Correzione",
                ],
                "proposal": [
                    "# [Progetto] - Proposta Tecnica",
                    "## Introduzione",
                    "Breve descrizione del progetto, dei suoi obiettivi e del problema che intende risolvere.",
                    "## Obiettivi",
                    "- Obiettivo 1: Descrivere il primo obiettivo del progetto.",
                    "- Obiettivo 2: Descrivere il secondo obiettivo del progetto.",
                    "## Approccio Tecnico",
                    "Spiegare la soluzione tecnica, inclusi strumenti, framework e metodologie da utilizzare.",
                    "### Funzionalità Chiave",
                    "- Funzionalità 1: Descrivere la prima funzionalità chiave.",
                    "- Funzionalità 2: Descrivere la seconda funzionalità chiave.",
                    "## Vantaggi",
                    "Evidenziare i vantaggi della soluzione proposta, come efficienza, scalabilità o risparmi.",
                    "## Piano di Implementazione",
                    "Fornire una timeline generale o i passi per implementare la soluzione.",
                    "## Rischi e Mitigazione",
                    "Identificare potenziali rischi e proporre strategie per mitigarli.",
                    "## Conclusione",
                    "Riassumere la proposta e ribadirne il valore.",
                ],
                "diagram": [
                    "# [Processo] - Flusso",
                    "```mermaid",
                    "graph TD",
                    "  A[Inizio] --> B{Decisione?}",
                    "  B -->|Sì| C[Processo 1]",
                    "  B -->|No| D[Processo 2]",
                    "  C --> E[Fine]",
                    "  D --> E",
                    "```",
                    "**Annotazioni:**",
                    "- **A**: Inizio del processo.",
                    "- **B**: Punto decisionale.",
                    "- **C/D**: Percorsi alternativi.",
                    "- **E**: Fine del processo.",
                    "**Colori:**",
                    "- **Verde**: Percorso di successo (es: utente loggato).",
                    "- **Rosso**: Percorso alternativo (es: utente non loggato).",
                    "**Legenda:**",
                    "- **Rettangolo**: Passo del processo.",
                    "- **Rombo**: Punto decisionale.",
                    "- **Cerchio**: Inizio/Fine.",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "Tecnico, conciso",
                    "elements": ["punti elenco"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "Persuasivo, chiaro e strutturato",
                    "elements": ["intestazioni", "punti elenco", "tabelle"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "Visivo, descrittivo e modulare",
                    "elements": ["mermaid", "colori", "annotazioni", "legenda"],
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
                "Usare terminologia tecnica rilevante per il progetto.",
                "Evidenziare i benefici della soluzione per persuadere gli stakeholder.",
                "Includere un piano di implementazione chiaro e strutturato.",
                "Affrontare rischi potenziali e proporre strategie di mitigazione.",
                "Usare punti elenco e intestazioni per migliorare la leggibilità.",
                "Fornire esempi concreti o casi studio a supporto della proposta.",
                "Assicurare che la proposta sia modulare e facilmente aggiornabile.",
                "Includere una conclusione che riassuma il valore della proposta.",
            ],
            "needs": "Persuasione per stakeholder, chiarezza nell'approccio tecnico, documentazione strutturata e insights attuabili",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [Argomento] - Guida",
                    "## [Sezione]",
                    "- **Concetto:** Spiegazione con esempi pratici e applicazioni.",
                ],
                "quick_ref": [
                    "**[Argomento] - Riferimento Rapido:**",
                    "- [Punto chiave]: Riepilogo breve e attuabile con contesto pratico chiaro.",
                ],
                "timeline": [
                    "# 🎥 [Lezione] - Cronologia",
                    "- **[MM:SS]** [Concetto chiave o azione eseguita]: [Spiegazione breve e chiara con risultati o azioni, evidenziando applicazioni reali].",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educativo, strutturato, con esempi per maggiore chiarezza",
                    "elements": [
                        "sottosezioni",
                        "punti elenco",
                        "esempi",
                        "applicazioni_reali",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "Conciso, pratico, progettato per apprendimento rapido",
                    "elements": ["punti elenco", "riepiloghi_chiari"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "Cronologico, orientato all'azione, chiaro con enfasi su applicazioni reali",
                    "elements": [
                        "cronologia",
                        "azioni_passopasso",
                        "segnali_visivi",
                        "contesto_reale",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "Fornire spiegazioni chiare e attuabili con esempi.",
                "Mantenere informazioni concise ma complete, focalizzate su applicazioni pratiche.",
                "Allinearsi agli obiettivi di apprendimento e al contesto.",
                "Enfatizzare chiarezza e usabilità, specialmente per casi d'uso reali.",
            ],
            "needs": "Facilitare studio rapido, riferimento veloce e tracciamento video con insights pratici",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [Progetto] - Cronaca",
                    "- **[MM:SS]** Elemento evidenziato",
                ],
                "report": [
                    "**[Progetto] - Report Tecnico:**",
                    "Paragrafo con dettagli chiave",
                ],
                "list": ["# [Progetto] - Dettagli", "- **Aspetto:** Descrizione"],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, visivo",
                    "elements": ["cronologia"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "Tecnico, dettagliato",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descrittivo, organizzato",
                    "elements": ["punti elenco"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Evidenziare innovazione o sostenibilità",
                "Includere dati tecnici se applicabile",
                "Essere visivamente accattivante",
            ],
            "needs": "Documentazione tecnica, presentazione accattivante, tracciamento video",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [Periodo] - Report Finanziario",
                    "- **Indicatore:** [Valore]",
                ],
                "table": [
                    "## [Periodo] - Riepilogo Finanziario",
                    "| **Indicatore** | **Valore** |",
                ],
                "executive": [
                    "**[Periodo] - Executive Summary:**",
                    "Paragrafo breve e incisivo che evidenzia insight chiave.",
                ],
            },
            "styles": {
                "report": {
                    "tone": "Analitico, formale",
                    "elements": ["punti elenco"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "Visivo, conciso",
                    "elements": ["tabella"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "Diretto, esecutivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "Garantire chiarezza e concisione nella presentazione delle cifre chiave.",
                "Evitare ambiguità nella presentazione dei dati.",
                "Supportare il processo decisionale con insight attuabili.",
                "I titoli delle tabelle devono essere formattati senza spazi extra prima o dopo i doppi asterischi.",
            ],
            "needs": "Dati attuabili, sintesi visiva chiara, riepiloghi esecutivi focalizzati sull'impatto",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [Destinazione] - Cronaca",
                    "- **[MM:SS]** Iniziativa",
                    "- **[MM:SS]** Punto di svolta importante",
                ],
                "report": [
                    "**[Destinazione] - Politiche:**",
                    "Paragrafo formale con enfasi sugli obiettivi della destinazione e impatto sul turismo",
                ],
                "list": [
                    "# [Destinazione] - Iniziative",
                    "- **Area:** Dettaglio (considerare cultura locale o attrazioni)",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "Narrativo, coinvolgente, immersivo",
                    "elements": ["cronologia", "storytelling"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "Formale, informativo, oggettivo",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "Descrittivo, chiaro, informativo",
                    "elements": ["punti elenco", "fatti_concisi"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "Evidenziare sostenibilità, significato culturale e attrattiva turistica",
                "Includere informazioni pratiche per i viaggiatori (es: periodo migliore per visitare, attrazioni locali, contatti essenziali)",
                "Focalizzarsi su descrizioni chiare, concise e accurate di politiche e iniziative",
                "Evitare esagerazioni, rimanere realistici e informativi",
            ],
            "needs": "Promozione coinvolgente con highlight informativi, presentazione chiara delle politiche e dettagli pratici per turisti",
        },
        "requirements": {
            "structures": {
                "elicitation": [
                    "Requisiti per [Progetto/Nome] - Elicitazione",
                    "Contesto",
                    "- Riunione: [Data, partecipanti, obiettivo].",
                    "- Ambito: [Scopo o risultato atteso].",
                    "Requisiti funzionali",
                    "- FR-[ID]: [Descrizione chiara]. (Priorità: [Alta/Media/Bassa], Giustificazione: [Motivo breve]).",
                    "Requisiti non funzionali",
                    "- NFR-[ID]: [Descrizione, es. qualità, tempi]. (Priorità: [Alta/Media/Bassa], Giustificazione: [Motivo]).",
                    "Dipendenze e vincoli",
                    "- Dipendenza: [Relazione con altri requisiti/risorse].",
                    "- Vincolo: [Limitazioni, es. budget, tempo].",
                    "Domande aperte",
                    "- [Domanda da chiarire]",
                    "Timestamp (se applicabile)",
                    "- [MM:SS]: [Citazione breve dalla fonte].",
                    "Criteri di prioritizzazione",
                    "- Alta: Critico per il successo o urgenza.",
                    "- Media: Importante, ma non essenziale.",
                    "- Bassa: Desiderabile, rinviabile.",
                ]
            },
            "styles": {
                "elicitation": {
                    "tone": "Chiaro, obiettivo, adattabile",
                    "elements": ["bullet_points", "IDs", "priorities"],
                    "source_types": [
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                        SourceType.TEXT,
                    ],
                }
            },
            "rules": [
                "Estrarre i requisiti direttamente, senza interpretazioni.",
                "Usare ID (FR-01, NFR-01) per la tracciabilità.",
                "Prioritizzare con giustificazione (impatto/urgenza).",
                "Usare un linguaggio chiaro incentrato sul 'cosa' è necessario.",
                "Elencare le ambiguità sotto 'Domande aperte'.",
                "Timestamp solo per i requisiti chiave.",
            ],
            "needs": "Cattura chiara dei requisiti per qualsiasi progetto, facilitando pianificazione e comunicazione.",
        },
        "sciences": {
            "structures": {
                "guide": [
                    "# 🔬 [Argomento] - Guida",
                    "## [Sezione]",
                    "- **Concetto:** Definizione, principio, relazione, processo, meccanismo, classificazione o evidenza rilevante.",
                ],
                "formula_reference": [
                    "# 🔬 [Argomento] - Riferimento formule",
                    "## Formule principali",
                    "| Formula | Significato | Variabili | Unità | Condizioni |",
                    "|---|---|---|---|---|",
                ],
                "derivation": [
                    "# 🔬 [Argomento] - Derivazione",
                    "## Punto di partenza",
                    "- [Definizione, principio, equazione, osservazione, dato o condizione iniziale presente nella fonte.]",
                    "## Sviluppo",
                    "1. [Primo passo o ragionamento presente nella fonte.]",
                    "2. [Trasformazione, relazione, procedura o ragionamento presente nella fonte.]",
                    "## Risultato",
                    "- **Risultato:** [Risultato o conclusione ottenuta nella fonte.]",
                ],
                "quick_ref": [
                    "**[Argomento] - Riferimento rapido:**",
                    "- **Concetto:** Definizione breve.",
                    "- **Principio/Legge/Teoria:** Relazione fondamentale.",
                    "- **Processo/Relazione:** Descrizione essenziale.",
                    "- **Dato/Formula:** Informazione quantitativa rilevante.",
                    "- **Condizione:** Applicabilità o limitazione.",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "Educativo, rigoroso e strutturato",
                    "elements": [
                        "concetti",
                        "principi",
                        "leggi",
                        "teorie",
                        "modelli",
                        "processi",
                        "meccanismi",
                        "strutture",
                        "relazioni",
                        "dati",
                        "formule",
                        "esempi",
                        "evidenze",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "formula_reference": {
                    "tone": "Tecnico, compatto e preciso, orientato all'applicazione corretta e al riferimento",
                    "elements": [
                        "formule",
                        "variabili",
                        "unità",
                        "relazioni",
                        "condizioni",
                        "tabelle",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "derivation": {
                    "tone": "Formale, logico e rigoroso, preservando il ragionamento effettivamente supportato dalla fonte",
                    "elements": [
                        "equazioni",
                        "procedure",
                        "deduzioni",
                        "sequenze",
                        "ragionamenti",
                        "assunzioni",
                        "condizioni",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
                "quick_ref": {
                    "tone": "Conciso, tecnico e pratico, progettato per una revisione rapida senza perdere precisione scientifica",
                    "elements": [
                        "concetti chiave",
                        "principi",
                        "leggi",
                        "teorie",
                        "processi",
                        "formule",
                        "dati",
                        "condizioni",
                    ],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                    ],
                },
            },
            "rules": [
                "Utilizzare esclusivamente le informazioni presenti nella fonte.",
                "Non introdurre conoscenza esterna anche se scientificamente corretta, nota, ovvia o utile a completare la spiegazione.",
                "Non inventare, completare, correggere né reinterpretare contenuti non supportati dalla fonte.",
                "Le strutture sono solo una guida organizzativa e non obbligano a creare contenuti per completare sezioni.",
                "Non includere una sezione quando la fonte non contiene informazioni sufficienti a giustificarla.",
                "Preservare definizioni, principi, leggi, teorie, ipotesi, modelli, processi, meccanismi, classificazioni, relazioni, dati, formule, variabili, unità, evidenze e condizioni rilevanti presenti nella fonte.",
                "Mantenere il significato originale di termini scientifici, simboli, variabili, grandezze, relazioni, processi e meccanismi.",
                "Non trasformare un'ipotesi, un modello, un'osservazione, una correlazione, un'associazione o un risultato sperimentale in un fatto, una legge o una relazione causale non stabilita dalla fonte.",
                "Non generalizzare risultati, meccanismi o conclusioni oltre le condizioni, la popolazione, il sistema, la scala o il contesto indicati nella fonte.",
                "Preservare eccezioni, limiti, assunzioni, restrizioni, incertezze e condizioni di validità quando influenzano l'interpretazione.",
                "Quando esistono dati quantitativi, conservare valori, unità, relazioni, ordini di grandezza e precisione rilevante.",
                "Quando esistono formule o relazioni matematiche, preservare segni, esponenti, indici, operatori, variabili, unità, approssimazioni e condizioni di validità.",
                "Non eseguire conversioni, calcoli, trasformazioni algebriche o inferenze quantitative aggiuntive non presenti o inequivocabilmente supportate dalla fonte.",
                "Quando esiste una derivazione, dimostrazione, procedura, esperimento o ragionamento sequenziale, conservare solo i passaggi essenziali effettivamente supportati dalla fonte.",
                "Non aggiungere passaggi intermedi, meccanismi, cause o spiegazioni che la fonte non presenta o non consente di stabilire inequivocabilmente.",
                "Conservare relazioni temporali, causali, funzionali, strutturali e gerarchiche quando sono rilevanti per comprendere correttamente il contenuto.",
                "Non confondere correlazione con causalità né associazione con meccanismo.",
                "Non eliminare informazioni la cui assenza potrebbe cambiare il significato, l'interpretazione, il risultato o l'ambito di applicazione del contenuto.",
                "Eliminare ridondanze e formulazioni ripetitive senza eliminare informazioni scientifiche necessarie.",
                "Ridurre la spiegazione, non il significato.",
                "In caso di conflitto, prioritizzare in questo ordine: fedeltà alla fonte, accuratezza scientifica, preservazione del significato e delle condizioni, chiarezza, struttura e infine concisione.",
                "L'obiettivo è rappresentare in modo compatto e preciso la conoscenza contenuta nella fonte, non fornire una spiegazione generale dell'argomento basata su conoscenza esterna.",
            ],
            "needs": (
                "Massima fedeltà e precisione scientifica, preservando concetti, "
                "processi, meccanismi, relazioni, dati, formule, evidenze, "
                "condizioni, limiti e ragionamento essenziale presenti nella fonte, "
                "senza introdurre conoscenza esterna né completare informazioni assenti."
            ),
        },
    }

    EXAMPLES = {
        "simple_summary": {
            "default": "Il contenuto descrive misure economiche annunciate l'8 marzo 2025, inclusi tagli fiscali e linee di credito."
        },
        "journalism": {
            "chronicle": (
                "# Evento Apple in Diretta\n"
                "- **[00:03:00]** Tim Cook presenta Apple Intelligence, un nuovo sistema di IA integrato nei dispositivi Apple.\n"
                "- **[00:05:11]** Presentazione dell'Apple Watch Series 10, con schermo più grande e design più sottile.\n"
                "- **[00:07:03]** Dimostrazione del nuovo display OLED, 40% più luminoso ad angoli obliqui.\n"
                "- **[00:09:06]** Annunciato uno spessore ridotto del 10% rispetto alla Series 9 (solo 9.7 mm).\n"
                "- **[00:10:19]** Ricarica rapida: 80% di batteria in 30 minuti.\n"
                "- **[00:11:03]** Finitura in titanio lucidato, 20% più leggera dell'acciaio inossidabile.\n"
                "- **[00:12:00]** Enfasi sulla sostenibilità: 95% titanio riciclato e 100% energia rinnovabile nella produzione.\n"
                "- **[00:13:50]** Nuove funzionalità salute: rilevamento apnea notturna e monitoraggio temperatura corporea per tracciamento ovulazione.\n"
                "- **[00:15:19]** 80% dei casi di apnea notturna non diagnosticati a livello globale."
            ),
            "news_wire": (
                "[8 marzo 2025] - Capitale - Il presidente annuncia misure economiche.\n"
                "### Dettagli Chiave\n"
                "- Riduzione tasse per famiglie di ceto medio.\n"
                "- Aumento spese infrastrutture.\n"
                "### Contesto\n"
                "- Le misure mirano a stimolare la crescita nonostante l'inflazione.\n"
                "### Statistiche\n"
                "- Previsione crescita PIL 2025: 2.5%.\n"
                "- Tasso disoccupazione: 5.8% (contro 6.3% anno precedente).\n"
                "### Impatto\n"
                "- Breve termine: sollievo immediato per le famiglie.\n"
                "- Lungo termine: stimolo economico e creazione di posti di lavoro."
            ),
            "analysis": (
                "## Riforma Fiscale Approfondimento\n"
                "### Panoramica\n"
                "- La riforma riduce le tasse per le famiglie di ceto medio e aumenta gli investimenti in infrastrutture.\n"
                "### Aspetti Chiave\n"
                "- **Tagli fiscali**: +10% potere d'acquisto per le famiglie.\n"
                "- **Infrastrutture**: Creazione di posti di lavoro e miglioramento servizi pubblici.\n"
                "### Implicazioni\n"
                "- **Breve termine**: Aumento dei consumi.\n"
                "- **Lungo termine**: Crescita economica sostenibile.\n"
                "### Opinioni Esperte\n"
                "- 'Un passo importante contro le disuguaglianze', secondo la Dr.ssa Jane Doe, economista ad Harvard.\n"
                "### Conclusione\n"
                "- Riforma equilibrata, ma il successo dipende dall'implementazione."
            ),
        },
        "marketing": {
            "highlights": "# ✨ Lancio EcoLife - Punti Salienti\n🎯 **Target:** Giovani.\n📈 **Vendite:** +15%.",
            "storytelling": (
                "## EcoLife - Una Storia: Viaggio verso la Sostenibilità\n"
                "### Introduzione\n"
                "- In una città frenetica, Maria, giovane donna, si sente sopraffatta dalle sfide ambientali.\n"
                "### Narrativa Principale\n"
                "- Scopre EcoLife, un brand sostenibile, e cambia il suo stile di vita.\n"
                "- Nonostante lo scetticismo iniziale, il suo impegno ispira gli altri.\n"
                "### Impatto Emotivo\n"
                "- Piccoli cambiamenti, grandi impatti - personali e ambientali.\n"
                "### Call to Action\n"
                "- Unisciti a Maria nel suo viaggio sostenibile con EcoLife!"
            ),
            "report": (
                "## EcoLife - Risultati\n"
                "### Panoramica\n"
                "- Campagna mirata ad aumentare notorietà e vendite tra i giovani promuovendo la sostenibilità.\n"
                "### Metriche Chiave\n"
                "| **Metrica**       | **Obiettivo** | **Effettivo** | **Varianza** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| Incremento vendite | +15%     | +18%       | +3%          |\n"
                "| Portata social media | 1M      | 1.2M       | +200K        |\n"
                "### Analisi\n"
                "- Obiettivi superati grazie al forte engagement sui social e collaborazioni con influencer.\n"
                "### Raccomandazioni\n"
                "- Continuare le partnership con influencer.\n"
                "- Espandere i contenuti educativi sulla sostenibilità.\n"
                "### Conclusione\n"
                "- Campagna di successo che getta basi solide per il futuro."
            ),
        },
        "health": {
            "report": "**Trattamento X - Report Clinico:** Studi clinici mostrano riduzione del 70% dei sintomi dopo 8 settimane di trattamento.",
            "summary": "# 🩺 Trattamento X - Riassunto\n📈 **Efficacia:** 70%.\n| Settimana | Progresso |\n| 8         | 70%       |",
            "case": "**Paziente A - Caso Clinico:** Uomo di 62 anni mostra miglioramenti dopo 2 settimane.",
        },
        "technology": {
            "changelog": "# v3.0 - Aggiornamento\n✨ **Nuove Funzionalità:**\n- OCR.\n🐛 **Correzioni:**\n- Esportazione.",
            "proposal": """
                    # Progetto X - Proposta Tecnica

                    ## Introduzione
                    Sistema automatizzato di integrazione API per migliorare l'efficienza dell'elaborazione dati.

                    ## Obiettivi
                    - Obiettivo 1: Ridurre l'inserimento manuale del 50%.
                    - Obiettivo 2: Aumentare la velocità di elaborazione del 30%.

                    ## Approccio Tecnico
                    Utilizzo di Python con Flask per le API, Docker per i container e Kubernetes per l'orchestrazione.

                    ### Funzionalità Chiave
                    - Funzionalità 1: Raccolta automatica dati da fonti multiple.
                    - Funzionalità 2: Validazione in tempo reale e gestione errori.

                    ## Vantaggi
                    - **Efficienza**: Riduce lo sforzo manuale e accelera i processi.
                    - **Scalabilità**: Gestisce volumi di dati crescenti.
                    - **Risparmi**: Automatizza task ripetitivi.

                    ## Piano di Implementazione
                    1. **Fase 1**: Sviluppo e test API (2 settimane).
                    2. **Fase 2**: Deployment e integrazione (3 settimane).
                    3. **Fase 3**: Monitoraggio e ottimizzazione (1 settimana).

                    ## Rischi e Mitigazione
                    - **Rischio 1**: Downtime API durante il deployment.
                    - **Mitigazione**: Implementare aggiornamenti graduali.
                    - **Rischio 2**: Errori di validazione dati.
                    - **Mitigazione**: Utilizzare test automatizzati.

                    ## Conclusione
                    Soluzione che offre significativi guadagni in efficienza e risparmi.
            """,
            "diagram": "# Autenticazione Utente - Flusso\n```mermaid\ngraph TD\n  A[Inizio] --> B{Utente loggato?}\n  B -->|Sì| C[Mostra Dashboard]\n  B -->|No| D[Reindirizza a Login]\n  C --> E[Fine]\n  D --> E\n```\n**Annotazioni:**\n- **A**: Inizio del processo.\n- **B**: Punto decisionale.\n- **C/D**: Percorsi alternativi.\n- **E**: Fine del processo.\n**Colori:**\n- **Verde**: Percorso di successo (utente loggato).\n- **Rosso**: Percorso alternativo (utente non loggato).\n**Legenda:**\n- **Rettangolo**: Passo del processo.\n- **Rombo**: Decisione.\n- **Cerchio**: Inizio/Fine.",
        },
        "education": {
            "guide": "# 📚 [Argomento] - Guida\n## [Sezione]\n- **Concetto:** Spiegazione con esempi pratici.",
            "quick_ref": "**[Argomento] - Riferimento Rapido:**\n- [Punto chiave]: Riepilogo breve e attuabile.",
            "timeline": "# 🎥 [Lezione] - Cronologia\n- **[MM:SS]** [Concetto chiave o azione]: [Spiegazione breve con risultati].",
        },
        "architecture": {
            "chronicle": "# 🏛️ Torre Verde - Cronaca\n- **[01:15]** Materiali sostenibili.",
            "report": "**Torre Verde - Report Tecnico:** Design che utilizza energia rinnovabile.",
            "list": "# Torre Verde - Dettagli\n- **Materiali:** Riciclati.\n- **Energia:** Solare.",
        },
        "finance": {
            "report": "# 💰 Q1 2025 - Report Finanziario\n- **Ricavi:** Crescita del 5% trainata da progressi tecnologici.",
            "table": "## Q1 2025 - Riepilogo Finanziario\n| **Indicatore** | **Valore** |\n|---------------|-----------|\n| Ricavi        | +5%       |",
            "executive": "**Q1 2025 - Executive Summary:** Crescita del 5% grazie a tecnologia ed espansione strategica, rafforzando le prospettive.",
        },
        "tourism": {
            "chronicle": "# 🌍 Baia Blu - Cronaca\n- **[01:00]** Iniziative di ecoturismo riducono i rifiuti.\n- **[05:00]** Importante sviluppo alberghiero eco-friendly.",
            "report": "**Baia Blu - Politiche:** Promuove sostenibilità riducendo rifiuti e supportando l'ecoturismo. Obiettivo: neutralità carbonica entro il 2030.",
            "list": "# Baia Blu - Iniziative\n- **Ecologia:** Meno plastica, più riciclo.\n- **Attrattive:** Attività tutto l'anno, alta stagione da maggio a settembre.",
        },
        "requirements": {
            "elicitation": """Requisiti per Evento Aziendale 2025 - Elicitazione
                Contesto
                - Riunione: 20/09/2025, team marketing ABC, pianificare evento per 500 partecipanti.
                - Ambito: Evento di networking e lancio prodotto, entro il budget.
                Requisiti funzionali
                - FR-01: Sede per 500 persone con stand. (Priorità: Alta, Giustificazione: Critico per l'evento).
                - FR-02: Registrazione online con email. (Priorità: Media, Giustificazione: Facilita la logistica).
                - FR-03: Keynote con oratore ospite. (Priorità: Alta, Giustificazione: Centrale per l'evento).
                Requisiti non funzionali
                - NFR-01: Conformità agli standard di sicurezza e accessibilità. (Priorità: Alta, Giustificazione: Obbligo legale).
                - NFR-02: Pianificazione entro 2 mesi. (Priorità: Alta, Giustificazione: Scadenza fissa).
                Dipendenze e vincoli
                - Dipendenza: La sede richiede approvazione del budget.
                - Vincolo: Budget di 30.000 $.
                Domande aperte
                - È necessario lo streaming dell'evento?
                Timestamp
                - [03:15]: 'Sede grande per 500 persone con stand'.
                - [08:20]: 'La keynote renderà l'evento memorabile'.
                Criteri di prioritizzazione
                - Alta: Critico per il successo o urgenza.
                - Media: Importante, ma non essenziale.
                - Bassa: Desiderabile, rinviabile."""
        },
        "sciences": {
            "guide": (
                "# 🔬 [Argomento] - Guida\n"
                "## [Sezione presente nella fonte]\n"
                "- **Concetto:** Definizione o spiegazione condensata dal contenuto della fonte.\n"
                "## [Altra sezione presente nella fonte]\n"
                "- **Processo:** Sequenza o meccanismo descritto nella fonte.\n"
            ),
            "formula_reference": (
                "# 🔬 [Argomento] - Riferimento formule\n"
                "## Formule principali\n"
                "| Formula | Significato | Variabili | Unità | Condizioni |\n"
                "|---|---|---|---|---|\n"
                "| [Formula presente nella fonte] | [Significato indicato nella fonte] | [Variabili definite nella fonte] | [Unità indicate] | [Condizioni indicate] |\n"
            ),
            "derivation": (
                "# 🔬 [Argomento] - Derivazione\n"
                "## Punto di partenza\n"
                "- [Definizione, equazione, dato, osservazione o condizione iniziale presente nella fonte.]\n"
                "## Sviluppo\n"
                "1. [Primo passo o trasformazione esplicitamente mostrata nella fonte.]\n"
                "2. [Secondo passo, relazione o ragionamento esplicitamente mostrato nella fonte.]\n"
                "## Risultato\n"
                "- **Risultato:** [Risultato o conclusione che la fonte ottiene esplicitamente.]\n"
            ),
            "quick_ref": (
                "**[Argomento] - Riferimento rapido:**\n"
                "- **Concetto:** [Definizione presente nella fonte.]\n"
                "- **Principio/Legge/Teoria:** [Solo se appare nella fonte.]\n"
                "- **Processo/Relazione:** [Processo o relazione descritta nella fonte.]\n"
                "- **Dato/Formula:** [Dato o formula presente nella fonte.]\n"
                "- **Condizione:** [Condizione o limitazione indicata nella fonte.]\n"
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
            f"# Prompt per {category.value.title()} - {style.value.title()}",
            f"**Obiettivo:** Creare contenuti in formato {output_format.value.upper()} ottimizzati per {category.value.title()}",
            f"**Stile:** {style.value.title()} ({style_info['tone']})",
            f"**Requisiti essenziali:** {spec.get('needs', 'adattamento al contesto')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "Non usare la prima persona né fingere di essere uno studente che prende appunti.",
            "Non inventare domande, dubbi, conclusioni o dati assenti dalla fonte.",
            "L'output È il riassunto. Mai un menu di aiuto, una copertina o domande al lettore.",
            "Non includere mai il tag ```markdown in nessuna circostanza. Se usi blocchi di codice, devono essere non specificati o in un linguaggio diverso da Markdown.",
            "Evita frasi generiche come «Il testo è ora privo di ripetizioni rimanendo chiaro e coerente.» Concentrati su feedback concreti e specifici.",
            "Non includere frasi come «Ecco il testo rivisto, rimuovendo ridondanze e ripetizioni, preservando tutti i dettagli e la struttura originale.»",
            "D'ora in poi, rispondi solo in italiano, indipendentemente dalla lingua della domanda originale.",
        ]

    async def get_map_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = """
            Istruzioni: Estrarre i fatti distintivi da questo frammento.
            IMPORTANTE: Stai elaborando SOLO UNA PARTE (chunk) di un documento molto più grande.
            - Scrivi titoli, elenchi e prosa in italiano. Altre lingue solo nel codice o nei nomi propri.
            - NON generare un'Introduzione globale né una Conclusione globale.
            - NON riavviare le gerarchie di numerazione (es. ## 1. Introduzione).
            - NON generare un documento autonomo.
            - Estrai da QUESTO frammento secondo il livello di riassunto: definizioni e fatti centrali sempre;
              esempi, cifre e aneddoti solo alla densità dell'istruzione di lunghezza.
            - Il livello di riassunto controlla la densità di dettaglio, non se un argomento maggiore presente qui possa essere omesso.
            - PRIORITÀ CRITICA: preservare la natura del linguaggio o del sistema (es. interpretato vs compilato,
              client vs server, statico vs dinamico) con lo stesso grado di certezza della fonte.
            - Se il testo contrappone pagine statiche e dinamiche, definisci ENTRAMBE.
            - Se afferma che qualcosa è multipiattaforma solo in teoria, mantieni quella riserva (non trasformarla in un fatto assoluto).
            - Conserva tabelle o elenchi comparativi punto per punto (non ridurli a «ci sono differenze»).
            - Preserva nomi di strumenti, percorsi di file, costanti numeriche, formule e citazioni di codice.
            - Preserva condizioni, eccezioni e riserve (teoricamente, può, solo se, non implica…).
            - Preserva sintassi, formule ed esempi esattamente come appaiono in questo frammento.
            - Distingui un indice o sommario dal contenuto effettivamente sviluppato qui.
            - Se questo frammento è un indice, descrivilo come indice (quali unità esistono) e NON estrarre quelle unità come se questo frammento le sviluppasse.
            - Non trattare le lezioni nominate nell'indice come spiegate se questo frammento non le sviluppa.
            - Nomina solo strumenti, librerie, API, editor e URL che appaiono letteralmente in questo frammento.
            - Non usare la prima persona. Non inventare domande né un diario di apprendimento.
            - L'output È l'estratto. Mai un menu di aiuto, una copertina di libro, domande al lettore, o «di cosa hai bisogno?».
            - Questo è un estratto denso per una sintesi successiva, non un minuscolo riepilogo autonomo.
            - Usa il budget di output disponibile per i fatti distintivi; non fermarti troppo presto se restano dettagli importanti.
            - Prepara il contenuto affinché sia utile a una sintesi globale successiva.
            - NON includere alcuna conoscenza esterna né informazione assente dal testo.
            - NON generare un indice o sommario.
        """
        return prompt

    async def get_reduce_prompt(
        self, generator: Any, category: Any = None, style: Any = None
    ) -> str:
        prompt = (
            "Sei un editor esperto. Il tuo compito è INTEGRARE i blocchi di testo forniti "
            "in un testo unificato.\n\n"
            "REGOLE OBBLIGATORIE:\n"
            "- ZERO RIEMPITIVO: NON aggiungere frasi di transizione inutili, introduzioni generiche o conclusioni. "
            "Vai dritto al punto.\n"
            "- DEDUPLICAZIONE STRETTA: Elimina ogni concetto, idea o argomento ripetuto tra i blocchi.\n"
            "- STRUTTURA UNICA: Consolida il contenuto sotto un'unica gerarchia. Rimuovi intestazioni ridondanti, "
            "ma CONSERVA argomenti di sezione distinti che rappresentano parti diverse della fonte.\n"
            "- FEDELTÀ STRETTA: Mantieni fedeltà assoluta. NON inventare fatti né aggiungere conoscenza esterna.\n"
            "- COPERTURA PRIMA: Ogni blocco sorgente con contenuto sostanziale deve essere rappresentato. "
            "Il livello di riassunto controlla la densità di dettaglio, non se un argomento maggiore possa scomparire.\n"
            "- NON COMPRIMERE SOTTO L'OBIETTIVO: Unisci e rimuovi i duplicati. "
            "Se l'istruzione di lunghezza chiede più parole di quante ne abbia l'input, "
            "conserva TUTTO il contenuto non ridondante rimanente; non accorciare ulteriormente e non inventare riempitivo.\n"
            "- RISPETTA L'ISTRUZIONE DI LUNGHEZZA: Se è fornita un'istruzione di lunghezza, seguila. "
            "Restare molto sotto l'obiettivo eliminando argomenti maggiori è un errore.\n"
            "- L'output È il riassunto unificato. Mai un assistente, un menu di opzioni, un blurb di copertina, "
            "domande al lettore, o «di cosa hai bisogno?».\n"
            "- VIETATO: prima persona, diari di apprendimento, domande inventate, "
            "sezioni «cosa ho imparato» o «punti da chiarire».\n"
            "- L'indice non è contenuto sviluppato: non riassumere unità, esempi o API "
            "che appaiono solo nell'indice se il corpo del documento non le spiega.\n"
            "- Nomina solo strumenti, librerie, API, editor e URL che appaiono letteralmente nei blocchi.\n"
            "- Non menzionare «blocco 1» né etichette interne della pipeline.\n"
            "- Non inventare ISBN, titoli di libri o confronti Java/JVM che la fonte non fa.\n"
            "- LINGUA: scrivi l'INTERO riassunto in italiano. Traduci i blocchi che sono in spagnolo o in un'altra lingua. "
            "Altre lingue solo in citazioni, codice o nomi propri.\n"
            "- Un blocco che dice «SOLO INDICE» o elenca unità/pagine senza spiegarle "
            "è SOLO un indice: SCARTALO. Non menzionarlo nel riassunto finale. "
            "Non elencare le unità dell'indice. Dedica il riassunto al contenuto effettivamente sviluppato.\n"
            "- PRESERVA SENZA DILUIRE: nomi di strumenti, file, costanti numeriche, "
            "confronti punto per punto e riserve di certezza (teoricamente, può, non implica, solo se).\n"
            "- NESSUN padding di token: non clonare sezioni, non parafrasare lo stesso blocco più volte, "
            "non inventare strumenti, API, editor o runtime assenti dalla fonte.\n"
            "- Se un argomento è già scritto, non scriverlo di nuovo. "
            "- Ordine di priorità: factualità, copertura, completezza, coerenza, struttura, poi concisione. "
            "La concisione non deve distruggere la copertura."
        )
        return prompt

    def get_available_styles_title(self) -> str:
        return "**Stili e toni disponibili:**"

    def get_semantic_profile_title(self) -> str:
        return "**Profilo semantico (informazioni da preservare):**"

    def get_length_instruction_title(self) -> str:
        return "**Istruzione di lunghezza:**"

    def get_semantic_profile(self, summary_level: SummaryLevel) -> str:
        profiles = {
            SummaryLevel.VERY_CONCISE: (
                "Esprimi la tesi principale, le conclusioni essenziali e i concetti centrali "
                "in forma altamente condensata. Conserva ogni pilastro maggiore. "
                "Ometti esempi secondari, aneddoti, consigli di lettura e sfumature minori."
            ),
            SummaryLevel.CONCISE: (
                "Preserva gli argomenti principali, le giustificazioni essenziali e la struttura tematica primaria. "
                "Sii diretto; riduci l'elaborazione secondaria senza eliminare sezioni importanti."
            ),
            SummaryLevel.MODERATE: (
                "Preserva argomenti, giustificazioni, evidenze rilevanti, esempi rappresentativi "
                "e tassonomie importanti."
            ),
            SummaryLevel.DETAILED: (
                "Preserva sottotemi, metodologia, evidenze, implicazioni, tassonomie complete "
                "e relazioni tra concetti."
            ),
            SummaryLevel.VERY_DETAILED: (
                "Preserva i dettagli inclusi eccezioni, sfumature, casi particolari, contesto "
                "e particolarità formalmente rilevanti. "
                "Nei tutorial tecnici: non omettere definizioni della natura del sistema "
                "(interpretato/compilato, client/server), tabelle comparative, nomi di strumenti, "
                "file di esempio, costanti numeriche o condizioni degli esempi."
            ),
        }
        return profiles.get(summary_level, "")

    def get_length_instruction(self, summary_level: SummaryLevel) -> str:
        instructions = {
            SummaryLevel.VERY_CONCISE: (
                "LUNGHEZZA / DENSITÀ: Produci un riassunto visibilmente più corto di moderate. "
                "Conserva la tesi, i pilastri e le definizioni centrali. "
                "Ometti esempi secondari, aneddoti, raccomandazioni di lettura e qualsiasi nota su un indice. "
                "Al massimo un breve esempio per pilastro, e solo se chiarisce la definizione. "
                "Essere più corti di moderate è corretto se gli argomenti maggiori sopravvivono. "
                "Non eliminare un pilastro; non copiare ogni esempio del livello moderate. "
                "Preferisci una formulazione densa all'elencazione di ogni caso."
            ),
            SummaryLevel.CONCISE: (
                "LUNGHEZZA / DENSITÀ: Produci un riassunto breve, più lungo di very_concise e più corto di moderate. "
                "Preferisci una formulazione compatta all'eliminazione di sezioni importanti. "
                "Un esempio rappresentativo per argomento maggiore è sufficiente."
            ),
            SummaryLevel.MODERATE: (
                "LUNGHEZZA / DENSITÀ: Produci un riassunto di lunghezza media, visibilmente più lungo di very_concise "
                "e più corto di very_detailed. "
                "Conserva un esempio rappresentativo per concetto maggiore, con numeri o nomi distintivi della fonte. "
                "Non copiare ogni caso o aneddoto."
            ),
            SummaryLevel.DETAILED: (
                "LUNGHEZZA / DENSITÀ: Produci un riassunto dettagliato, più lungo di moderate. "
                "Prendi lo spazio necessario per sottotemi, evidenze e diversi esempi della fonte."
            ),
            SummaryLevel.VERY_DETAILED: (
                "LUNGHEZZA / DENSITÀ: Produci un riassunto visibilmente più lungo di moderate. "
                "Conserva ogni esempio, cifra, nome, eccezione e condizione sviluppata nel corpo della fonte. "
                "Non comprimere quei fatti distintivi. "
                "Non riempire mai ripetendo paragrafi, clonando sezioni, citando l'indice "
                "o aggiungendo conoscenza esterna."
            ),
        }
        return instructions.get(summary_level, "")

    def get_coverage_guarantee(self) -> str:
        return (
            "GARANZIA DI COPERTURA (si applica a ogni livello di riassunto): "
            "Le idee principali, i concetti essenziali, gli argomenti di sezione importanti e i termini "
            "centrali DEVONO sopravvivere. Il livello di riassunto controlla solo densità di dettaglio "
            "ed elaborazione secondaria. Non autorizza mai a eliminare una sezione maggiore "
            "né la tesi centrale del documento."
        )

    def get_coverage_checklist(self, outline: Sequence[str]) -> str:
        if not outline:
            return ""
        lines = "\n".join(f"- {item}" for item in outline)
        return (
            "**Lista di copertura (solo se la sezione è SVILUPPATA nei blocchi, "
            "non se appare solo in un indice):**\n"
            f"{lines}\n"
            "Non inventare il contenuto di un'intestazione che i blocchi non spiegano."
        )

    def get_map_closing_instruction(self) -> str:
        return (
            "**Istruzione di chiusura:** "
            "Copri i fatti distintivi di QUESTO frammento alla densità dell'istruzione di lunghezza. "
            "Usa il budget di output disponibile per quei fatti; non fermarti troppo presto se restano dettagli importanti. "
            "Non ripetere paragrafi per riempire. "
            "Termina sempre con una frase completa."
        )

    def get_toc_map_stub(self, entry_labels: Sequence[str]) -> str:
        listed = "; ".join(entry_labels) if entry_labels else "voci dell'indice"
        return (
            "SOLO INDICE — questo frammento è un indice, non lezioni sviluppate. "
            f"Elenco: {listed}. "
            "Non presentare queste voci come se il documento le avesse spiegate qui."
        )

    def get_direct_summary_intro(self) -> str:
        return (
            "Sei un esperto di sintesi documentale. Riassumi il documento completo "
            "in un unico passaggio. Preserva la struttura concettuale importante "
            "(titoli/sezioni rilevanti), idee principali, definizioni, "
            "procedure, esempi e termini centrali. "
            "Emitti Markdown pulito. Non inventare contenuti. "
            "Non scrivere un diario di apprendimento né elenchi di domande.\n"
            "L'indice o il sommario NON È contenuto sviluppato: "
            "menzionalo solo come indice; non presentare unità o esempi dell'indice "
            "come se il corpo del documento li avesse spiegati.\n"
            "PRIORITÀ CRITICA: preservare la natura del linguaggio (interpretato/compilato), "
            "l'ambiente di esecuzione (client/server), il contrasto statico/dinamico, "
            "tabelle comparative, nomi di strumenti, file, costanti numeriche "
            "e riserve di certezza (teoricamente, può, non implica, solo se).\n\n"
        )

    def get_format_prompt(self) -> str:
        return (
            "Sei un editor di formattazione. Il tuo unico compito è applicare la formattazione Markdown "
            "al testo fornito.\n\n"
            "NON riassumere, accorciare, espandere, reinterpretare o omettere informazioni.\n"
            "NON aggiungere introduzione, conclusione, titolo globale o conoscenza esterna.\n"
            "Preserva ordine, elenchi, tabelle, codice, URL e termini tecnici.\n"
            "Se un vincolo di formattazione confligge con la preservazione delle informazioni, preserva le informazioni."
        )

    def get_format_strict_rules(self) -> str:
        return """
REGOLE CRITICHE DI FORMATTAZIONE:
1. Devi preservare tutte le informazioni contenute nell'input.
2. Non omettere alcuna sezione, paragrafo, elemento di elenco, tabella, esempio di codice, URL, termine tecnico o affermazione fattuale.
3. Non riassumere, accorciare, espandere, reinterpretare né aggiungere informazioni.
4. Il tuo compito è solo la formattazione.
5. L'output deve contenere tutte le informazioni della fonte, preservando l'ordine originale.
6. Se i vincoli di formattazione confliggono con la preservazione delle informazioni, la preservazione ha priorità.
7. Non usare mai conoscenza esterna.
8. Non completare mai informazioni mancanti.
9. Non inventare mai esempi o spiegazioni.
10. Produci SOLO la versione formattata dell'input. NON aggiungere un titolo in testa. NON aggiungere una sezione «Introduzione». NON aggiungere conclusioni. NON inventare titoli di sezione.
11. Preserva la struttura dei paragrafi; non prefissare ogni paragrafo con elenchi puntati a meno che l'input non lo faccia già.
12. Se non ci sta tutto il contenuto, produci quanto ci sta e FERMATI a un confine di frase. Non emettere mai «[texto truncado]» né segnaposto simili.
"""

    def get_format_user_content(self, text_block: str) -> str:
        return (
            "Applica il formato e lo stile indicati nelle istruzioni al seguente testo. "
            "NON riassumere né omettere informazioni:\n\n"
            f"{text_block}"
        )

    def get_format_position_hint(self, index: int, total_blocks: int) -> str:
        if total_blocks <= 1:
            return ""
        if index == 0:
            return (
                "\n\nIMPORTANTE: Questo è il BLOCCO 1 di {total} in un documento multiparte. "
                "Formatta questa sezione come l'APERTURA del documento. "
                "PUOI includere un'introduzione se il contenuto lo giustifica. "
                "NON aggiungere una conclusione né osservazioni di chiusura."
            ).format(total=total_blocks)
        if index == total_blocks - 1:
            return (
                "\n\nIMPORTANTE: Questo è il BLOCCO {idx} di {total} (ULTIMO BLOCCO) in un documento multiparte. "
                "Formatta questa sezione come la CHIUSURA del documento. "
                "PUOI includere una conclusione se il contenuto lo giustifica. "
                "NON aggiungere una nuova introduzione né riavviare la numerazione."
            ).format(idx=index + 1, total=total_blocks)
        return (
            "\n\nIMPORTANTE: Questo è il BLOCCO {idx} di {total} (BLOCCO INTERMEDIO) in un documento multiparte. "
            "Formatta questo come CONTINUAZIONE del documento. "
            "NON aggiungere introduzione, NON aggiungere conclusione, NON riavviare la numerazione delle sezioni."
        ).format(idx=index + 1, total=total_blocks)

    def get_reduce_user_content(self, batch_text: str) -> str:
        return (
            "Elabora i seguenti blocchi di testo. "
            "Scrivi l'output unificato solo in italiano; traduci qualsiasi blocco scritto in spagnolo o in un'altra lingua. "
            "Se un blocco è solo un indice, ignorarlo completamente; non menzionarlo.\n\n"
            f"{batch_text}"
        )

    def format_reduce_block_header(self, block_index: int, chunk_ids_str: str) -> str:
        return f"--- [Blocco {block_index} (Frammenti: {chunk_ids_str})] ---"

    def get_intermediate_reduce_instruction(
        self,
        batch_input_tokens: int,
        remaining_ratio: float,
    ) -> str:
        target_words = max(1, int((batch_input_tokens * remaining_ratio) * 0.75))
        min_words = max(1, int(target_words * 0.80))
        pct = int(remaining_ratio * 100)
        return (
            "ISTRUZIONE CRITICA: Sei un passaggio intermedio di riduzione. "
            "Unisci e deduplica i blocchi forniti. "
            f"Lunghezza residua obiettivo: circa {pct}% dell'input (~{target_words} parole). "
            f"Scrivi almeno {min_words} parole. NON comprimere sostanzialmente sotto questo obiettivo. "
            "Non ripetere paragrafi per riempire. "
            "Preserva nomi distintivi, esempi, slogan, conclusioni e fatti bibliografici di OGNI blocco. "
            "Scarta solo formulazioni ripetute e riformulazioni verbose. Non inventare contenuti.\n\n"
        )

    def get_final_reduce_instruction(self, target_max_tokens: int) -> str:
        target_words = max(1, int(target_max_tokens * 0.75))
        min_words = max(1, int(target_words * 0.55))
        return (
            "ISTRUZIONE CRITICA: Sei il passaggio FINALE di sintesi. "
            "Integra i blocchi in un unico riassunto in italiano, senza duplicare sezioni. "
            f"Soglia di copertura: conserva almeno ~{min_words} parole di contenuto non ridondante "
            f"(obiettivo ~{target_words}) se i blocchi lo contengono. "
            "Se i blocchi hanno meno dell'obiettivo, conserva TUTTO il contenuto distintivo; "
            "non comprimere ulteriormente e non inventare riempitivo per raggiungere il conteggio. "
            "Se i blocchi hanno di più, unisci i duplicati ma non eliminare argomenti, cifre, nomi o esempi. "
            "Un indice non è contenuto sviluppato: ometti quei blocchi e non menzionare che esiste un indice. "
            "Non presentare unità, esempi o API che appaiono solo nell'indice. "
            "Nomina solo strumenti e API presenti nei blocchi.\n\n"
        )

    def get_reduce_quality_retry_instruction(self) -> str:
        """Instruction prepended when REDUCE final output fails the quality gate."""
        return (
            "CRITICO: Scrivi il riassunto stesso. Mai un menu di aiuto, un saluto da assistente, "
            "una copertina di libro o domande al lettore.\n\n"
        )
