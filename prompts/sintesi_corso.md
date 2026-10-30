# Prompt — sintesi del corso

Hai a disposizione le **edizioni rivedute** di tutte le lezioni di un corso italiano di
OSINT (una cartella per lezione, file `editoriale.md`). Devi produrre **un solo file**
`SINTESI_CORSO.md` alla radice del pacchetto.

Non inventare contenuti: ogni affermazione deve trovare riscontro in almeno una lezione.
Quando citi un concetto, indica la lezione tra parentesi, es. *(Report Osint Socmint)*.

## Struttura del file

```markdown
---
title: "Sintesi del corso"
fonte: "80 lezioni, edizione riveduta"
---

# Investigatore Digitale — OSINT e AI

## In una pagina
150–200 parole: cosa insegna il corso, a chi serve, cosa si è in grado di fare alla fine.

## Il percorso
Per ogni capitolo del corso (non per ogni lezione): 3–6 righe su cosa viene insegnato e
perché viene prima degli altri. Usa i titoli dei capitoli come sottotitoli.

## Il metodo, in sequenza
Il flusso di lavoro che il corso costruisce, numerato: dalla richiesta del committente
al report. Per ogni passo, la lezione di riferimento e lo strumento principale.

## Strumenti per fase
| Fase | Strumenti citati | Lezione |
Tabella. Solo strumenti realmente nominati; se un tool è indicato come a pagamento o
non più funzionante nella lezione, scrivilo.

## Cosa il corso non copre
3–6 punti: argomenti dati per scontati, strumenti non aggiornati, aspetti legali solo
accennati.

## Avvertenze pratiche
Errori ricorrenti segnalati dal relatore, limiti dei tool, rischi operativi (attribuzione
dell'identità, falsi positivi, dati di minori, questioni GDPR).
```

## Regole

1. **Fedeltà**: se un'informazione è incerta o contraddittoria tra lezioni, dillo.
2. **Nomi dei tool**: non correggerli e non tradurli. Se in lezioni diverse compaiono
   grafie differenti, scegli quella usata più spesso e segnala la variante.
3. **Niente marketing**: nessun "potente", "rivoluzionario", "al giorno d'oggi".
4. **Lunghezza**: 1.200–1.800 parole complessive. Se un capitolo è povero, poche righe.
5. Scrivi il file e rispondi in chat solo con `OK SINTESI_CORSO.md` più eventuali
   incoerenze rilevate tra lezioni.
