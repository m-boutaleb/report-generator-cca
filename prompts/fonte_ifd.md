# Fonte dati — Imposta federale diretta (IFD)

## Ente e acronimi
- **IFD**: imposta federale diretta (reddito imponibile / reddito determinante delle economie domestiche).
- **AFC**: Amministrazione federale delle contribuzioni, ente federale che gestisce l’IFD e ne pubblica le statistiche.

## Cosa misura nel report
I dati IFD/AFC alimentano l’analisi del **reddito per economia domestica**:
- reddito medio/mediano equivalente per regione (`reddito_line.csv`);
- distribuzione per **fasce di reddito** (`reddito_75.csv`).

Unità nel report: **kCHF/anno per economia domestica**.

## Come si ottiene / aggiornamento
- Dati derivati dalle **pubblicazioni ufficiali** dell’imposta federale (AFC).
- L’annualità disponibile **non coincide** sempre con quella del mercato locativo o dell’offerta: nel report segnalare esplicitamente l’anno di riferimento (es. annualità 2022).
- Possibile **ritardo di pubblicazione** rispetto ad altre fonti: menzionarlo come limite metodologico quando rilevante (asincronia temporale tra reddito e canoni).

## CSV del report collegati all’IFD
| CSV | Contenuto |
|-----|-----------|
| `reddito_line.csv` | Evoluzione reddito medio equivalente cantonale e regionale |
| `reddito_75.csv` | Distribuzione per fasce di reddito (quota % e valori assoluti) |

## Regole redazionali
- Citare la fonte come: «statistiche dell’imposta federale diretta (IFD), a cura dell’Amministrazione federale delle contribuzioni (AFC)».
- Indicare sempre l’**annualità** dei dati reddito usati nel paragrafo.
- Non confondere reddito IFD con reddito del mercato del lavoro o altre statistiche cantonali.
