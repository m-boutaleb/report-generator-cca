import pandas as pd
import requests
import io
import os

os.makedirs('csv_data', exist_ok=True)

# 1. off_regioni (Cantonale) -> 112
print("Downloading 112...")
req1 = requests.post("https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/207/card/112/csv")
df1 = pd.read_csv(io.StringIO(req1.text))
df1 = df1.sort_values(by=df1.columns[0]).reset_index(drop=True)
df1.to_csv("csv_data/off_cantonale.csv", index=False)

# 2. RS_ED -> 60 (Bar chart % with absolute values)
print("Downloading 60...")
req2 = requests.post("https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/60/card/60/csv")
df2 = pd.read_csv(io.StringIO(req2.text))
# columns: Region, Building Category Sea, Conteggio
# Calcolo per regione dei count totali
totals = df2.groupby('Region')['Conteggio'].transform('sum')
df2['Percentuale'] = (df2['Conteggio'] / totals) * 100
df2['Percentuale'] = df2['Percentuale'].round(1)

# we want to pivot so Region is row, columns are Categories, and each category has perc and conteggio
# Pgfplots can easily read it if each category has a % column and an abs column.
pivot_perc = df2.pivot(index='Region', columns='Building Category Sea', values='Percentuale').fillna(0).reset_index()
pivot_abs = df2.pivot(index='Region', columns='Building Category Sea', values='Conteggio').fillna(0).reset_index()

# Merge them
merged2 = pd.merge(pivot_perc, pivot_abs, on='Region', suffixes=('_perc', '_abs'))
merged2.to_csv("csv_data/rs_ed.csv", index=False)

# 3. RS_ANNO -> 62 (Anno di costruzione, Region, Conteggio)
print("Downloading 62...")
req3 = requests.post("https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/62/card/62/csv")
df3 = pd.read_csv(io.StringIO(req3.text))
pivot3 = df3.pivot(index='Anno di costruzione', columns='Region', values='Conteggio').fillna(0).reset_index()
# Sort by Anno di costruzione: ante 1961, 1961-1980, 1981-1990, 1991-2000, post 2000
order = ['ante 1961', '1961-1980', '1981-1990', '1991-2000', 'post 2000']
pivot3['Anno di costruzione'] = pd.Categorical(pivot3['Anno di costruzione'], categories=order, ordered=True)
pivot3 = pivot3.sort_values('Anno di costruzione').reset_index(drop=True)
pivot3.to_csv("csv_data/rs_anno.csv", index=False)


# 4. Scompenso1 -> 87 (anno, scenario, Somma di scompenso)
print("Downloading 87...")
req4 = requests.post("https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/97/card/87/csv")
df4 = pd.read_csv(io.StringIO(req4.text))
pivot4 = df4.pivot(index='anno', columns='scenario', values='Somma di scompenso').reset_index()
pivot4.to_csv("csv_data/scompenso1.csv", index=False)

# 5. Scompenso affiancato -> 136 (Superficie mq + nr locali, Regione, Somma di Scompenso)
print("Downloading 136...")
req5 = requests.post("https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/161/card/136/csv")
df5 = pd.read_csv(io.StringIO(req5.text))
pivot5 = df5.pivot(index='Superficie mq + nr locali', columns='Regione', values='Somma di Scompenso').fillna(0).reset_index()
# Sort categories
s_order = ['2-2.5 locali  (50-70m²)', '3-3.5 locali (70-90m²)', '4-4.5 locali (90-110m²)']
pivot5['Superficie mq + nr locali'] = pd.Categorical(pivot5['Superficie mq + nr locali'], categories=s_order, ordered=True)
pivot5 = pivot5.sort_values('Superficie mq + nr locali').reset_index(drop=True)
pivot5.to_csv("csv_data/scompenso_side.csv", index=False)

print("Done generating CSVs.")
