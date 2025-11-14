from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


class ItalianPrompts:
    INSTRUCTIONS_TITLE: str = "**Istruzioni:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**Lingua specifica:** Italiano"
    SPECIFIC_LANGUAGE: str = (
        "Da ora in poi, tutte le risposte devono essere esclusivamente in italiano."
    )
    EXPECTED_FORMAT_TITLE: str = "Riepilogo diretto senza titoli aggiuntivi"
    EXAMPLE_TITLE: str = "Esempio:"

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
                "Riassumere in modo conciso, rimuovendo ridondanze",
                "Preservare il titolo originale se presente, senza modifiche, usando la formulazione esatta (es: # Titolo, ## Sottotitolo)",
                "Adattarsi completamente al tono, intento e struttura implicita del contenuto originale",
                "Non introdurre titoli, sottotitoli o intestazioni a meno che non siano esplicitamente presenti nel testo originale",
                "Mantenere esempi o concetti chiave nel formato originale (es: elenchi, codice, corsivi)",
                "Evitare interpretazioni soggettive o modifiche non necessarie",
                "Produrre un unico blocco di testo continuo a meno che il contenuto originale non specifichi diversamente",
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
            "Evita frasi generiche come 'Il testo ora è privo di ripetizioni e rimane chiaro e coerente.' Concentrati su feedback concreti e specifici.",
            "Non includere frasi come 'Ecco il testo modificato, rimuovendo ridondanze e ripetizioni, mantenendo tutti i dettagli e la struttura originale.'",
            "Non includere mai l’etichetta ```markdown. Se usi blocchi di codice, devono essere non specificati o in un linguaggio diverso da Markdown.",
            f"Da ora in poi, rispondi solo in italiano, indipendentemente dalla lingua della domanda originale.",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- Riassumi il documento in modo completo, evidenziando temi principali, punti chiave e obiettivo generale in circa {word_limit} parole."

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            Contesto del testo precedente: {previous_context}\n
            Istruzioni: Fornisci un riassunto dettagliato del testo seguente, integrando le nuove informazioni in modo coerente con il contesto precedente.
            Includi esempi, spiegazioni e dettagli che facilitino lo studio dell’argomento.
            Organizza il riassunto in sezioni o punti chiave per una migliore comprensione."""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""Sei un editor esperto nel migliorare i testi eliminando ridondanze.
            Controlla il seguente riassunto e rimuovi solo informazioni ripetute o ridondanti,
            come testi, frasi o idee ripetute.
            Non semplificare, ridurre o condensare il contenuto in alcun modo; mantieni tutti i dettagli, dati ed elementi importanti così come sono.
            Assicurati che il testo finale sia chiaro, coerente e ben strutturato, senza alterarne struttura o significato originale."""
        return prompt
