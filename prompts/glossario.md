Sei un esperto di politiche abitative e analisi del mercato immobiliare svizzero.

Ti fornisco un rapporto tecnico intitolato "Analisi dello scompenso dei canoni locativi sostenibili nel Canton Ticino" (Osservatorio cantonale sull'alloggio, SUPSI, Dicembre 2025).

Il tuo compito è generare un capitolo **Glossario** da aggiungere al report.

---

## ISTRUZIONI

### 1. Termini obbligatori

Definisci **esclusivamente** i termini elencati sotto, raggruppati per categoria. Non aggiungere altre voci, anche se compaiono nel report.

#### Mercato locativo

- Mercato locativo offerto
- Mercato locativo praticato
- Canone mediano
- Campione (natura campionaria dei dati RS)



#### Reddito

- Reddito equivalente per economia domestica



#### Indicatori di accessibilità abitativa

- Tasso di sforzo (mercato praticato vs offerto)
- Punti percentuali (differenza tra due tassi di sforzo)
- Pigione sostenibile
- Offerta a pigione sostenibile *(distinta da «pigione sostenibile»: alloggi effettivamente disponibili sul mercato offerto entro la soglia di sostenibilità calcolata)*
- Scompenso di pigione sostenibile



#### Scenari e metodologia

- Scenario A, B, C, D (superficie minima garantita per numero di persone — cfr. Tabella~\ref{table_1})
- Scenario AB *(aggregato scenari A e B)*
- Scenario CD *(aggregato scenari C e D)*
- Superficie minima garantita
- Categorie dimensionali per locali (es. 2–2.5 locali / 50–70 m², 3–3.5 / 70–90 m², 4–4.5 / 90–110 m²)



#### Fonti dati

- Wüest & Partner AG
- Rilevazione Strutturale (RS) — Ufficio federale di statistica (UST)
- Imposta federale diretta (IFD) — Amministrazione federale delle contribuzioni (AFC)

Per RS e IFD, integra le informazioni essenziali da `prompts/fonte_rs.md` e `prompts/fonte_ifd.md`.

---



### 2. Formato di ogni voce

**[Termine]**
*Categoria: [Indicatore / Fonte dati / Concetto metodologico]*
Definizione: [2–4 frasi chiare, in italiano, adattate al contesto del report. Includi, se pertinente, l'unità di misura e la fonte utilizzata.]

**Rimandi ai capitoli (opzionali):**

- Usa `\rightarrow` cfr. [nome sezione]` solo se utile e **non circolare**.
- **Non** rimandare un termine a se stesso.
- Preferisci: Introduzione, Mercato locativo offerto, Mercato locativo praticato, Reddito, Tasso di sforzo, Offerta a pigione sostenibile, Scompenso di pigione sostenibile.

---



### 3. Contenuti specifici da chiarire


| Termine                                  | Cosa deve comparire nella definizione                                                                 |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Mercato locativo offerto / praticato** | Offerto = annunci; praticato = contratti esistenti (RS)                                               |
| **Campione RS**                          | Dati non censuari; indicare periodo (es. 2019–2023)                                                   |
| **Canone mediano**                       | Valore mediano; nel report spesso in CHF/m² anno                                                      |
| **Reddito equivalente**                  | kCHF/anno per economia domestica; fonte IFD/AFC                                                       |
| **Scenario A–D**                         | Tabella superficie minima per 1–5 persone; A = minimo, D = massimo                                    |
| **Scenario AB / CD**                     | AB = aggregato A e B; CD = aggregato C e D; usati nello scompenso cantonale                           |
| **Tasso di sforzo**                      | Rapporto % spesa annua alloggio / reddito; praticato vs offerto                                       |
| **Punti percentuali**                    | Differenza assoluta tra due percentuali (es. 24.6 % − 22.6 % = 2.0 punti percentuali)                 |
| **Offerta a pigione sostenibile**        | Conteggio alloggi in annuncio; non confondere con il valore teorico di pigione sostenibile            |
| **Scompenso di pigione sostenibile**     | Quantificazione degli alloggi a pigione sostenibile necessari considerando lo scenario di riferimento |


---



### 4. Requisiti stilistici

- Linguaggio tecnico ma accessibile, coerente con lo stile del report
- Tono neutro e istituzionale
- Ordine **alfabetico** all'interno di ogni sottosezione
- Ogni definizione autonoma
- Indica le sigle (RS, UST, IFD, AFC) alla prima occorrenza nelle voci pertinenti
- Non ripetere interi paragrafi del report: sintetizza

---



### 5. Struttura del capitolo da produrre

Output in LaTeX, pronto per `\begin{multicols}{2}`:

```
\section{Glossario}

[Nota introduttiva ~3 righe]

\subsection{Mercato locativo}
[voci]

\subsection{Reddito}
[voci]

\subsection{Indicatori di accessibilità abitativa}
[voci]

\subsection{Scenari e metodologia}
[voci]

\subsection{Fonti dati}
[voci]
```

Formato voce in LaTeX:

```
\textbf{Termine} \\
\textit{Categoria: ...} \\
Definizione: ... $\rightarrow$ cfr. ...
```

---



### 6. Note aggiuntive

- Ripeti le unità di misura quando pertinenti (CHF/m², kCHF/anno, CHF, %)
- Per scenari, tasso di sforzo e scompenso: logica sintetica, senza formule complesse
- Non inventare dati numerici non presenti nel report

