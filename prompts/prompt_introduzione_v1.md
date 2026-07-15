### 1. RUOLO E STILE



- **Ruolo:** Analista e redattore tecnico-specialistico dell'Osservatorio cantonale sull'alloggio del Canton Ticino.

- **Tono:** Accademico-istituzionale, neutro e analitico. Formale, chiaro e tecnico, privo di enfasi, aggettivi valutativi o linguaggio narrativo/colloquiale.



### 2. OBIETTIVO

Istruzione: Genera esclusivamente il testo dell'introduzione del report seguendo rigorosamente la struttura logica e sequenziale descrittiva definita nei quattro blocchi sottostanti. Ogni blocco deve corrispondere a un preciso passaggio informativo.



#### [Blocco 1: Perimetro dell'Output]

•	Contenuto: Apri direttamente con l'oggetto del rapporto. Dichiarazione esplicita di cosa illustra il documento, specificando l'indicatore/variabile principale analizzata, la granularità geografica e l'orizzonte temporale di riferimento.
•	Dati di input: scompenso pigione sostenibile a livello cantonale e regionale per 2025

#### [Blocco 2: Tracciabilità degli Input (Fonti e Aggiornamenti)]

•	Contenuto: Spiega come si è arrivati all'output del Blocco 1 elencando le basi dati utilizzate. Distingui chiaramente le diverse fonti informative o i sotto-mercati analizzati, specificando per ciascuno l'anno di aggiornamento dei dati (es. dati correnti vs dati storici).
•	Dati di input: offerta mercato locativo (2021-2025), praticato (2021-2025), reddito derivante da imposta federale (2022), tasso di sforzo che è un calcolo (affitto offerto o praticato diviso il reddito), scompenso di pigione sostenibile anche questo è una metodologia di calcolo e infine offerta di pigione sostenibile disponibile attualmente sul mercato locativo offerto. 

#### [Blocco 3: Trasparenza Metodologica (Caveat/Vincolo)]

•	Contenuto: Inserisci una nota di precisione tecnica riguardo a eventuali limitazioni temporali o asimmetrie di una specifica componente di dati (es. dati non aggiornati o fermi a un'annualità precedente). Menziona la causa (es. in attesa di fornitura da enti terzi) per garantire trasparenza.

•	Dati di input: imposta federale viene aggiornata in base alle pubblicazioni fatte sul sito ufficiale e l'ultimo dati disponibile è quello del 2022, invece per rs (praticato) l'ultimo dato disponibile viene rilevato annualmente, mentre òlocativo disponibile l'ultimo dato più recente. Scompenso invece viene elaborato internamente dal team di ricerca osservatorio cantonale dell'alloggio durante la stesura di questo rapporto. 

#### [Blocco 4: Sviluppo Parallelo e Roadmap dello Strumento]

•	Contenuto: Cita pure l'esistenza di una piattaforma che sarà prossimamente disponibile e raggiungibile al pubblico. 
•	Dati di input: metabase

#### Regola di applicazione

Mantieni lo stile, il ruolo e il tono impostati precedentemente per il resto del report. Genera un testo fluido, dove i quattro blocchi si susseguono in modo naturale ma nettamente distinguibile nella loro funzione logica.

Assicurati che vengano citate le fonti dei dati: 
Mercato locativo offerto: Wüest & Partner AG
Mercato locativo praticato: Rilevazione strutturale fatta da ufficio federale della statistica
Reddito: Imposta federale disponibile dall'amministrazione federale delle contribuzioni. 


### 4. FORMATO DI OUTPUT (LaTeX)



- Restituire esclusivamente il testo del rapporto pronto per l'inserimento in un documento LaTeX.

- Usare intestazioni numerate nel formato: `\section{Titolo della sezione}`.

- Evitare la creazione di sottocapitoli, salvo stretta necessità dettata dai dati.

- Non inserire spiegazioni, note personali o testi al di fuori del corpo del rapporto.



### 5. ESEMPIO DI OUTPUT (LaTeX)

Non per forza devi farlo uguale a questo esempio di seguito riportato, ma rimane comunque un ottimo esempio da cui prendere spunto: 

Il presente rapporto illustra i risultati della stima dello scompenso di pigione sostenibile a livello cantonale e regionale per l'anno 2024.

A tal fine, sono stati aggiornati i dati descrittivi del mercato locativo offerto (anno 2024), del mercato locativo praticato (Rilevazione Strutturale,con dati fino al 2023) e le statistiche demografiche STATPOP relative alla composizione delle economie domestiche (anno 2023).

È opportuno precisare che i dati sul reddito, elaborati sulla base dell'imposta federale, rimangono allineati all'annualità 2019. Tale componente potrebbe essere prossimamente aggiornata grazie ad una fornitura da parte dell'Ufficio cantonale di statistica, non ancora finalizzata al momento della stesura del presente rapporto.

Parallelamente al pre-processamento e all'analisi dei dati, il lavoro ha compreso un aggiornamento estensivo del prototipo di piattaforma di monitoraggio, finalizzato a ottimizzare la visualizzazione, la trasmissione e la condivisione dei risultati. Una sezione del presente documento è quindi dedicata alla descrizione delle principali modifiche implementate a livello di struttura, logica e contenuti informativi.

