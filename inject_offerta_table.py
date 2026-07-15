#!/usr/bin/env python3
"""Inject LaTeX table from data/offerta_tabellina.csv into main.tex."""

import re
from pathlib import Path

import pandas as pd

from figure_style import latex_escape

ROOT = Path(__file__).resolve().parent
CAPTIONS_PATH = ROOT / "data" / "captions.json"


def load_captions() -> dict[str, str]:
    if CAPTIONS_PATH.is_file():
        import json

        return json.loads(CAPTIONS_PATH.read_text(encoding="utf-8"))
    return {}
CSV_PATH = ROOT / "data" / "offerta_tabellina.csv"
TEX_PATH = ROOT / "main.tex"
SECTION = "Mercato locativo offerto"
MARKER_START = "% BEGIN: offerta_tabellina (auto-generated)"
MARKER_END = "% END: offerta_tabellina (auto-generated)"


def fmt_decimal(value: float, decimals: int = 1) -> str:
    # Decimal separator: point. Thousands separator: apostrophe.
    return f"{value:,.{decimals}f}".replace(",", "'")


def fmt_integer(value: float) -> str:
    # Thousands separator: apostrophe.
    return f"{int(round(value)):,}".replace(",", "'")


def build_table_latex(df: pd.DataFrame) -> str:
    rows = []
    for _, row in df.iterrows():
        anno = int(row.iloc[0])
        prezzo = fmt_decimal(float(row.iloc[1]), 1)
        superficie = fmt_decimal(float(row.iloc[2]), 1)
        locali = fmt_decimal(float(row.iloc[3]), 2)
        osservazioni = fmt_integer(float(row.iloc[4]))
        durata = fmt_decimal(float(row.iloc[5]), 1)
        rows.append(
            f"    {anno} & {prezzo} & {superficie} & {locali} & {osservazioni} & {durata} \\\\"
        )

    body = "\n".join(rows)
    header = r"""\begin{table*}[ht]
    \centering
    \footnotesize
    \label{tab:offerta_tabellina}
    \begin{tabular}{lrrrrr}
        \toprule
        Anno &
        \makecell[r]{Prezzo medio al m\textsuperscript{2} \\ {[}CHF{]}} &
        \makecell[r]{Superficie media \\ {[}m\textsuperscript{2}{]}} &
        \makecell[r]{Nr locali \\ medi} &
        \makecell[r]{Osservazioni} &
        \makecell[r]{Durata media \\ d'inserzione {[}gg{]}} \\
        \midrule
"""
    footer = rf"""        \bottomrule
    \end{{tabular}}
    \caption{{{latex_escape(load_captions().get("offerta_tabellina", "Indicatori medi del mercato locativo offerto a livello cantonale"))}}}
\end{{table*}}
"""
    return f"{MARKER_START}\n{header}{body}\n{footer}{MARKER_END}"


def ensure_preamble_packages(tex: str) -> str:
    packages = []
    if r"\usepackage{booktabs}" not in tex:
        packages.append(r"\usepackage{booktabs}")
    if r"\usepackage{makecell}" not in tex:
        packages.append(r"\usepackage{makecell}")
    if not packages:
        return tex
    block = "\n".join(packages) + "\n"
    return tex.replace(r"\usepackage{hyperref}", block + r"\usepackage{hyperref}", 1)


def inject_table(tex: str, table_block: str) -> str:
    marker_pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\s*",
        re.DOTALL,
    )
    if MARKER_START in tex:
        return marker_pattern.sub(lambda _m: table_block + "\n\n", tex, count=1)

    section_pattern = rf"(\\section\{{{re.escape(SECTION)}\}})"
    if not re.search(section_pattern, tex):
        raise ValueError(f"Sezione non trovata: {SECTION}")

    # Inserisce dopo la prima figure* della sezione Offerta (grafico evoluzione)
    fig_end = r"\end{figure*}"
    section_match = re.search(section_pattern + r".*", tex, re.DOTALL)
    if not section_match:
        raise ValueError("Impossibile individuare il corpo della sezione Offerta.")

    start = section_match.start()
    section_text = tex[start:]
    fig_pos = section_text.find(fig_end)
    if fig_pos == -1:
        return re.sub(
            section_pattern + r"\s*",
            lambda m: m.group(1) + "\n\n" + table_block + "\n\n",
            tex,
            count=1,
        )

    insert_at = start + fig_pos + len(fig_end)
    return tex[:insert_at] + "\n\n" + table_block + "\n\n" + tex[insert_at:]


def main() -> None:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"CSV non trovato: {CSV_PATH}. Esegui data_fetch.py.")

    df = pd.read_csv(CSV_PATH)
    if len(df.columns) < 6:
        raise ValueError(f"CSV inatteso: colonne={list(df.columns)}")

    table_block = build_table_latex(df)
    tex = TEX_PATH.read_text(encoding="utf-8")
    tex = ensure_preamble_packages(tex)
    tex = inject_table(tex, table_block)
    TEX_PATH.write_text(tex, encoding="utf-8")
    print(f"Tabella iniettata in {TEX_PATH}")


if __name__ == "__main__":
    main()
