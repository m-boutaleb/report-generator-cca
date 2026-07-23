# Fonte dati — Rilevazione Strutturale (RS)

## Ente e acronimi

- **RS**: Rilevazione Strutturale sul parco immobiliare e sul mercato locativo praticato.
- **UST**: Ufficio federale di statistica (Ufficio federale della statistica), che conduce la RS.

## Cosa misura nel report

La RS fornisce i dati del **mercato locativo praticato**: canoni effettivamente applicati nei contratti esistenti, caratteristiche degli alloggi (superficie netta, numero di locali, persone), tipologia di edificio, epoca di costruzione.

Non va confusa con il **mercato locativo offerto** (annunci Wüest & Partner).

## Copertura temporale


| Concetto                              | Periodo       |
| ------------------------------------- | ------------- |
| **Arco disponibile nella fonte RS**   | 2019–2023     |
| **Ultimo pull dati usato nel report** | **2021–2023** |


- La Rilevazione Strutturale copre annualità dal **2019 al 2023**; nel report i CSV del mercato praticato riflettono l'**ultimo aggiornamento effettuato**, con dati dal **2021 al 2023**.
- Quando si descrive la **natura campionaria**, si può citare l'arco completo 2019–2023.
- Nei **confronti temporali e nelle variazioni**, usare il periodo **2021–2023** (coerente con i CSV correnti), salvo diversa indicazione nel file.



## Come si ottiene / aggiornamento

- Rilevazione **annuale** a livello federale.
- Nel report i dati praticato sono trattati come **campione**: non generalizzare come se rappresentassero l'intera popolazione cantonale.
- Nel testo segnalare sempre il **periodo coperto** (es. «campione 2019–2023», confronti su «2021–2023»).



## CSV del report collegati alla RS


| CSV                 | Contenuto                                                             |
| ------------------- | --------------------------------------------------------------------- |
| `praticato_139.csv` | Canone locativo mediano per tipologia di economia domestica e regione |
| `praticato_60.csv`  | Tipologia di edificio per regione (quota % e valori assoluti)         |
| `praticato_62.csv`  | Distribuzione età degli edifici per regione                           |
| `praticato_146.csv` | Indicatori medi cantonali (prezzo al m², superficie, locali, persone) |




## Regole redazionali

- Citare la fonte come: «Rilevazione Strutturale dell'Ufficio federale di statistica (UST)».
- Usare «mercato locativo praticato» in modo coerente; non alternare con «RS» nel corpo del testo se non serve la sigla.
- Quando si commentano variazioni, ricordare la **natura campionaria** dei dati.

