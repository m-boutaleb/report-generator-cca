# Rapporto Osservatorio Alloggio — pipeline dati e LaTeX

## Docker / GitHub Container Registry

Ogni push di un **tag versione** (`1.0.0` o `v1.0.0`) pubblica un’immagine su GHCR:

```text
ghcr.io/<owner>/report-generator-cca:1.0.0
ghcr.io/<owner>/report-generator-cca:latest   # solo per tag X.Y.Z “puri”
```

Workflow: `.github/workflows/docker-publish.yml`.

Esempio pubblicazione e avvio:

```bash
git tag 1.0.0
git push origin 1.0.0

docker pull ghcr.io/<owner>/report-generator-cca:1.0.0
docker run --rm -p 8000:8000 \
  -v ${PWD}/secrets.json:/app/secrets.json:ro \
  ghcr.io/<owner>/report-generator-cca:1.0.0
```

`secrets.json` non è incluso nell’immagine: montalo a runtime (o usa variabili d’ambiente).

## REST API (pipeline completa)

Un’unica chiamata avvia: download CSV → aggiornamento grafici → generazione testo (2 colonne) → compilazione PDF → check `\ref` → ZIP (`main.pdf` + `main.tex`).

```bash
pip install -r requirements.txt
copy secrets.example.json secrets.json   # poi compila le chiavi (GEMINI_API_KEY, …)
python api.py                            # http://127.0.0.1:8000
```

Le credenziali stanno in `secrets.json` (ignorato da git). Priorità: variabile d’ambiente → `secrets.json` → default.

Documentazione interattiva: `http://127.0.0.1:8000/docs`

| Endpoint | Descrizione |
|----------|-------------|
| `POST /report/generate` | Pipeline completa; restituisce ZIP (sync) o `job_id` (`async_mode=true`) |
| `GET /report/jobs/{id}` | Stato job async |
| `GET /report/jobs/{id}/download` | ZIP `main.tex` + `main.pdf` |
| `GET /report/jobs/{id}/tex` | Solo `.tex` |
| `GET /report/jobs/{id}/pdf` | Solo `.pdf` |
| `GET /report/latest/download?kind=zip\|tex\|pdf` | Ultimo artifact / file corrente |
| `GET /health` | Healthcheck |

Esempio sync:

```bash
curl -X POST http://127.0.0.1:8000/report/generate -H "Content-Type: application/json" -d "{}" -o rapporto.zip
```

Esempio async:

```bash
curl -X POST http://127.0.0.1:8000/report/generate -H "Content-Type: application/json" -d "{\"async_mode\": true}"
# poi: GET /report/jobs/<job_id>  →  GET /report/jobs/<job_id>/download
```

Opzioni body utili: `skip_fetch`, `skip_figures`, `skip_text`, `inject_only` (usa backup prosa locali), `fail_on_bad_refs`.

In alternativa, dalla CLI:

```bash
python pipeline.py                 # pipeline completa → output/artifacts/rapporto_*.zip
python pipeline.py --inject-only   # prosa dai backup, senza Gemini
python pipeline.py --skip-text     # solo dati + grafici + PDF
```

Layout: la prosa è wrappata in `\begin{multicols}{2}` (testo a due colonne); le figure restano a tutta larghezza fuori dalle colonne. I `\ref{}` usano `fig:<nome_csv>` / `tab:<nome_csv>`.

## Ordine di esecuzione (workflow B, step singoli)

Eseguire dalla root del progetto, con ambiente Python attivo:

```bash
python data_fetch.py      # scarica tutti i CSV in data/ (+ data/captions.json)
python generate_figures.py  # rigenera i grafici PGFPlots in main.tex
python apply_tikz2.py     # alias di generate_figures.py
python inject_offerta_table.py  # tabella riepilogo da offerta_tabellina.csv
python generate_offerta_text.py
python build_pdf.py       # richiede tutti i CSV referenziati in main.tex
```

Se `build_pdf.py` segnala CSV mancanti, eseguire prima `data_fetch.py`.

1. **data_fetch.py** — scarica i CSV da Metabase in `data/` (offerta, praticato, ecc.).
2. **apply_tikz2.py** — inietta i grafici PGFPlots in `main.tex` (richiede `main.tex` con le sezioni corrispondenti).
3. **generate_offerta_text.py** — genera la prosa del capitolo *Mercato locativo offerto* con Gemma via Ollama e la inietta in `main.tex`.

## Prerequisiti Ollama

```bash
ollama serve          # se non già in esecuzione
ollama pull gemma3:4b # o altro modello Gemma
```

Variabili d'ambiente opzionali:

| Variabile | Default |
|-----------|---------|
| `OLLAMA_MODEL` | `gemma3:4b` |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` |
| `OLLAMA_TEMPERATURE` | `0.3` |
| `OLLAMA_NUM_PREDICT` | `2048` |

## generate_offerta_text.py

```bash
python generate_offerta_text.py              # genera e inietta in main.tex
python generate_offerta_text.py --dry-run    # mostra prompt senza chiamare Ollama
python generate_offerta_text.py --model gemma2:9b
```

Output:

- Backup: `output/offerta_prosa_last.tex`
- Iniezione idempotente in `main.tex` tra `% BEGIN: offerta_prosa` e `% END: offerta_prosa`

Dati usati: `data/offerta_line.csv`, `data/offerta_tabellina.csv`, istruzioni in `prompts/prompt_EA.txt`.

## test_google_ai.py (Gemini — provider cloud per la prosa)

Usato dalla pipeline API (`python api.py` / `pipeline.py`). Stesse istruzioni e CSV di `generate_offerta_text.py`:

```bash
pip install google-genai
# Imposta GEMINI_API_KEY in secrets.json
python test_google_ai.py --dry-run
python test_google_ai.py --section all
```

Output: `output/*_prosa_gemma.tex`

## build_pdf.py

Compila `main.tex` in `main.pdf` (richiede **MiKTeX** o **TeX Live** con `pdflatex` nel PATH).

```bash
python build_pdf.py                 # 2 passate pdflatex (indice, pgfplots)
python build_pdf.py --latexmk       # alternativa con latexmk
python build_pdf.py --clean         # pulisce .aux/.log prima di compilare
python build_pdf.py --clean-only    # solo pulizia
python build_pdf.py --passes 3
```

Prerequisito LaTeX su Windows: installa [MiKTeX](https://miktex.org/download) e riapri il terminale, oppure aggiungi `pdflatex` al PATH.
