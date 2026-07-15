import json
import pandas as pd
import requests
import io
import os

from config import require_secret
from figure_style import format_title_from_disposition

os.makedirs('data', exist_ok=True)
headers = {"X-API-Key": require_secret("METABASE_API_KEY")}
CAPTIONS: dict[str, str] = {}


def get_df(url, caption_key: str | None = None, fallback_title: str = ""):
    r = requests.post(url, headers=headers)
    if caption_key:
        title = format_title_from_disposition(
            r.headers.get("content-disposition", ""),
            fallback_title,
        )
        CAPTIONS[caption_key] = title
    return pd.read_csv(io.StringIO(r.text))


def save_captions() -> None:
    with open("data/captions.json", "w", encoding="utf-8") as f:
        json.dump(CAPTIONS, f, ensure_ascii=False, indent=2)

# 1. Offerta
# Cantonale: 112 -> Data (anno), Media di Prezzo Al M² [chf]
# Regionale: 119 -> Data (anno), Regioni, Media di Prezzo Al M² [chf]
print("Fetching offerta...")
df_off_cant = get_df(
    "https://cc-alloggio.ddns.net/api/card/112/query/csv",
    "offerta_line_cantonale",
    "Canone mediano cantonale per anno (CHF/m²)",
)
df_off_reg = get_df(
    "https://cc-alloggio.ddns.net/api/card/119/query/csv",
    "offerta_line",
    "Canone mediano regionale per anno (CHF/m²)",
)
df_off_tab = get_df(
    "https://cc-alloggio.ddns.net/api/card/145/query/csv",
    "offerta_tabellina",
    "Indicatori medi del mercato locativo offerto a livello cantonale",
)
df_off_cant = df_off_cant.rename(columns={df_off_cant.columns[0]: 'Anno', df_off_cant.columns[1]: 'Cantonale'})
df_off_reg = df_off_reg.rename(columns={df_off_reg.columns[0]: 'Anno', df_off_reg.columns[1]: 'Regione', df_off_reg.columns[2]: 'Prezzo'})
pivot_off_reg = df_off_reg.pivot(index='Anno', columns='Regione', values='Prezzo').reset_index()
off_merged = pd.merge(df_off_cant, pivot_off_reg, on='Anno')
off_merged.to_csv('data/offerta_line.csv', index=False)
df_off_tab.to_csv('data/offerta_tabellina.csv', index=False)



# 2. Praticato
# 139: Grouped bar tipologia vs canone per region
print("Fetching praticato 139...")
df_139 = get_df(
    "https://cc-alloggio.ddns.net/api/card/139/query/csv",
    "praticato_139",
    "Canone locativo mediano per tipologia di economia domestica e regione",
)
# columns: Region, Hh Type Bfs, Canone locativo mediano annuo
df_139.columns = ['Region', 'Tipologia', 'Canone']
# We only want to plot a few labels or rename them because they are very long, but let's keep them and pivot.
# "Coppie conviventi con almeno un/a figlio/a di meno di 25 anni, famiglie non ricomposte" -> too long!
# Let's shorten them using a mapping or truncation for latex labels.
def shorten(x):
    if type(x) is str:
        s = x.split(',')[0]
        if len(s) > 40:
            return s[:37] + "..."
        return s
    return x


def pgf_safe_label(x):
    """Accorcia le etichette tipologia (testo libero, non usato nel CSV pgfplots)."""
    s = shorten(x)
    if isinstance(s, str):
        s = s.replace("<", "sotto ")
    return s


TIPOLOGIA_ORDER = [
    "Convivenze multiple",
    "Coppie con figli 25+",
    "Coppie con figli sotto 25",
    "Coppie senza figli",
    "Genitori soli con figli 25+",
    "Genitori soli con figli sotto 25",
    "Persone sole",
]

df_139['Tipologia'] = df_139['Tipologia'].apply(pgf_safe_label)
pivot_139 = (
    df_139.groupby(['Tipologia', 'Region'])['Canone']
    .mean()
    .reset_index()
    .pivot(index='Tipologia', columns='Region', values='Canone')
    .fillna(0)
    .reset_index()
)
# Ordine stabile per yticklabels in main.tex
pivot_139['Tipologia'] = pd.Categorical(
    pivot_139['Tipologia'], categories=TIPOLOGIA_ORDER, ordered=True
)
pivot_139 = pivot_139.sort_values('Tipologia').reset_index(drop=True)
pivot_139.insert(0, 'id', range(len(pivot_139)))
pivot_139 = pivot_139.drop(columns=['Tipologia'])
pivot_139.to_csv('data/praticato_139.csv', index=False)

# 60: Stacked bar (Region vs Building Category)
print("Fetching praticato 60...")
df_60 = get_df(
    "https://cc-alloggio.ddns.net/api/card/60/query/csv",
    "praticato_60",
    "Distribuzione delle categorie di edificio per regione (quota % e valori assoluti)",
)
df_60.columns = ['Region', 'Category', 'Conteggio']
totals_60 = df_60.groupby('Region')['Conteggio'].transform('sum')
df_60['Pct'] = (df_60['Conteggio'] / totals_60) * 100
df_60['Pct'] = df_60['Pct'].round(1)
pivot_60_pct = df_60.pivot(index='Region', columns='Category', values='Pct').fillna(0).reset_index()
pivot_60_abs = df_60.pivot(index='Region', columns='Category', values='Conteggio').fillna(0).reset_index()
m_60 = pd.merge(pivot_60_pct, pivot_60_abs, on='Region', suffixes=('_perc', '_abs'))
m_60.to_csv('data/praticato_60.csv', index=False)

# 62: Stacked bar (Anno di costruzione vs Region => X is Region!)
print("Fetching praticato 62...")
df_62 = get_df(
    "https://cc-alloggio.ddns.net/api/card/62/query/csv",
    "praticato_62",
    "Distribuzione del parco immobiliare per epoca di costruzione e regione",
)
df_62.columns = ['AnnoCostruzione', 'Region', 'Conteggio']
totals_62 = df_62.groupby('Region')['Conteggio'].transform('sum')
df_62['Pct'] = (df_62['Conteggio'] / totals_62) * 100
df_62['Pct'] = df_62['Pct'].round(1)
order = ['ante 1961', '1961-1980', '1981-1990', '1991-2000', 'post 2000']
df_62['AnnoCostruzione'] = pd.Categorical(df_62['AnnoCostruzione'], categories=order, ordered=True)
pivot_62_pct = df_62.pivot(index='Region', columns='AnnoCostruzione', values='Pct').fillna(0).reset_index()
pivot_62_abs = df_62.pivot(index='Region', columns='AnnoCostruzione', values='Conteggio').fillna(0).reset_index()
m_62 = pd.merge(pivot_62_pct, pivot_62_abs, on='Region', suffixes=('_perc', '_abs'))
m_62.to_csv('data/praticato_62.csv', index=False)

# Tabella praticato (nr 146)
print("Fetching praticato 146...")
df_146 = get_df(
    "https://cc-alloggio.ddns.net/api/card/146/query/csv",
    "praticato_146",
    "Indicatori medi del mercato locativo praticato a livello cantonale",
)
df_146.to_csv('data/praticato_146.csv', index=False)


# 3. Reddito
# Line merge: 78 (Cantonal) & 77 (Regional)
print("Fetching reddito lines...")
df_78 = get_df(
    "https://cc-alloggio.ddns.net/api/card/78/query/csv",
    "reddito_line_cantonale",
    "Evoluzione reddito medio equivalente",
)
df_84_77 = get_df(
    "https://cc-alloggio.ddns.net/api/card/77/query/csv",
    "reddito_line",
    "Evoluzione reddito medio equivalente per regione",
)
df_78.columns = ['Anno', 'Cantonale']
df_84_77.columns = ['Regione', 'Anno', 'Media']
pivot_84 = df_84_77.pivot(index='Anno', columns='Regione', values='Media').reset_index()
merged_reddito = pd.merge(df_78, pivot_84, on='Anno')
merged_reddito.to_csv('data/reddito_line.csv', index=False)

# Stacked bar fasce reddito: 75
print("Fetching reddito 75...")
df_75 = get_df(
    "https://cc-alloggio.ddns.net/api/card/75/query/csv",
    "reddito_75",
    "Distribuzione fasce di reddito per regione (quota % e valori assoluti)",
)
# columns: Regione, Anno, Somma di 0 30 Occorrenze ... etc
# Assuming year is constant or we just sum over year. Let's filter to latest year or drop Anno and aggregate
df_75 = df_75.drop(columns=['Anno']).groupby('Regione').sum()
# Calculate pct row-wise
totals_75 = df_75.sum(axis=1)
df_75_pct = df_75.div(totals_75, axis=0) * 100
df_75_pct = df_75_pct.round(1)
# Create _perc and _abs columns using merge manually
df_75_pct.columns = [c.replace('Somma di ', '').replace('Occorrenze', '').strip() + '_perc' for c in df_75_pct.columns]
df_75_abs = df_75.copy()
df_75_abs.columns = [c.replace('Somma di ', '').replace('Occorrenze', '').strip() + '_abs' for c in df_75_abs.columns]
merged_75 = pd.concat([df_75_pct, df_75_abs], axis=1).reset_index()
merged_75.to_csv('data/reddito_75.csv', index=False)


# 4. Tasso di sforzo (card 121: barre orizzontali per regione)
print("Fetching tasso di sforzo 121...")
df_121 = get_df(
    "https://cc-alloggio.ddns.net/api/card/121/query/csv",
    "tasso_di_sforzo_121",
    "Tasso di sforzo per regione (mercato praticato e offerto)",
)
df_121.columns = [
    "Regione",
    "RedditoMedio_kCHF",
    "CanoneOffertoMedio",
    "CanonePraticatoMedio",
    "TassoPraticato",
    "TassoOfferto",
]
df_121["TassoPraticato_pct"] = (df_121["TassoPraticato"] * 100).round(1)
df_121["TassoOfferto_pct"] = (df_121["TassoOfferto"] * 100).round(1)
region_order = ["Bellinzona", "Locarno", "Lugano", "Mendrisio", "Tre Valli"]
df_121["Regione"] = pd.Categorical(df_121["Regione"], categories=region_order, ordered=True)
df_121 = df_121.sort_values("Regione").reset_index(drop=True)
df_121.to_csv("data/tasso_di_sforzo_121.csv", index=False)


# 6. Offerta sostenibile
print("Fetching sostenibile 104, 118, 143, 102...")

# Bar chart: numero di locali vs conteggio
print("Fetching sostenibile 104...")
df_104 = get_df(
    "https://cc-alloggio.ddns.net/api/card/104/query/csv",
    "sostenibile_104",
    "Distribuzione dell'offerta per numero di locali",
)
df_104.columns = ["CategoriaLocali", "NrLocali", "Conteggio"]
df_104.to_csv("data/sostenibile_104.csv", index=False)

# Horizontal bar: conteggio per comune (top 15)
print("Fetching sostenibile 118...")
df_118 = get_df(
    "https://cc-alloggio.ddns.net/api/card/118/query/csv",
    "sostenibile_118",
    "Principali comuni per inserzioni a pigione sostenibile",
)
df_118.columns = ["Comune", "Conteggio"]
df_118 = df_118.sort_values("Conteggio", ascending=False).head(15).reset_index(drop=True)
df_118.to_csv("data/sostenibile_118.csv", index=False)

# Distribuzione per regione (torta / quote)
print("Fetching sostenibile 143...")
df_143 = get_df(
    "https://cc-alloggio.ddns.net/api/card/143/query/csv",
    "sostenibile_143",
    "Distribuzione delle inserzioni per regione (quota % e valori assoluti)",
)
df_143.columns = ["Regione", "Conteggio"]
totals_143 = df_143["Conteggio"].sum()
df_143["Conteggio_pct"] = (df_143["Conteggio"] / totals_143 * 100).round(1)
region_order = ["Bellinzona", "Locarno", "Lugano", "Mendrisio", "Tre Valli"]
df_143["Regione"] = pd.Categorical(df_143["Regione"], categories=region_order, ordered=True)
df_143 = df_143.sort_values("Regione").reset_index(drop=True)
df_143.to_csv("data/sostenibile_143.csv", index=False)

# Bar chart: durata d'inserzione vs conteggio
print("Fetching sostenibile 102...")
df_102 = get_df(
    "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/118/card/102/query/csv",
    "sostenibile_102",
    "Distribuzione delle inserzioni per durata d'inserzione",
)
df_102.columns = ["DurataInserzione", "Conteggio"]
df_102.to_csv("data/sostenibile_102.csv", index=False)


# 7. Scompenso
print("Fetching scompenso 87, 136...")

# Line chart: evoluzione scompenso per scenario (AB / CD)
print("Fetching scompenso 87...")
df_87 = get_df(
    "https://cc-alloggio.ddns.net/api/card/87/query/csv",
    "scompenso_87",
    "Evoluzione dello scompenso (scenari AB e CD)",
)
df_87.columns = ["Anno", "Scenario", "Scompenso"]
pivot_87 = df_87.pivot(index="Anno", columns="Scenario", values="Scompenso").reset_index()
pivot_87.to_csv("data/scompenso_87.csv", index=False)

# Barre raggruppate: scompenso per regione e metratura
print("Fetching scompenso 136...")
df_136 = get_df(
    "https://cc-alloggio.ddns.net/api/card/136/query/csv",
    "scompenso_136",
    "Scompenso incrociato per regione e metratura",
)
df_136.columns = ["Superficie", "Regione", "Conteggio"]


def map_surf(x):
    if "2-2.5" in x:
        return "2-2.5 locali (50-70m²)"
    if "3-3.5" in x:
        return "3-3.5 locali (70-90m²)"
    if "4-4.5" in x:
        return "4-4.5 locali (90-110m²)"
    return x


SURFACE_ORDER = [
    "2-2.5 locali (50-70m²)",
    "3-3.5 locali (70-90m²)",
    "4-4.5 locali (90-110m²)",
]

df_136["Superficie"] = df_136["Superficie"].apply(map_surf)
pivot_136 = (
    df_136.pivot(index="Superficie", columns="Regione", values="Conteggio")
    .fillna(0)
    .reset_index()
)
pivot_136["Superficie"] = pd.Categorical(
    pivot_136["Superficie"], categories=SURFACE_ORDER, ordered=True
)
pivot_136 = pivot_136.sort_values("Superficie").reset_index(drop=True)
pivot_136.to_csv("data/scompenso_136.csv", index=False)

print("Done generating all CSVs.")
save_captions()
print("Saved data/captions.json")


