#!/usr/bin/env python3
"""Generate PGFPlots figure blocks and inject them into main.tex."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from config import ROOT, TEX_PATH
from figure_style import (
    BAR_LABEL_STYLE,
    GROUPED_YBAR_LABEL_STYLE,
    HORIZONTAL_BAR_LABEL_STYLE,
    LEGEND_BELOW,
    LEGEND_DEEP,
    LEGEND_EXTRA_DEEP,
    LEGEND_SCOMPENSO_BAR,
    LEGEND_SCOMPENSO_LINE,
    LINE_WIDTH,
    REGION_COLORS,
    REGION_LEGEND,
    REGION_ORDER,
    REGION_XCOORDS,
    STACKED_BAR_STYLE,
    STACKED_LABEL_STYLE,
    bar_width,
    braced_column,
    compute_bar_width_pt,
    grouped_vertical_bars,
    grouped_bar_shifts,
    latex_escape,
    numeric_range,
    paired_horizontal_bars,
)

CAPTIONS_PATH = ROOT / "data" / "captions.json"

FIGURE_SECTIONS: dict[str, str] = {
    "offerta_figure": "offerta_figure",
    "praticato_figure": "praticato_figure",
    "reddito_figure": "reddito_figure",
    "tasso_sforzo_figure": "tasso_sforzo_figure",
    "sostenibile_figure": "sostenibile_figure",
    "scompenso_figure": "scompenso_figure",
}


def load_captions() -> dict[str, str]:
    if CAPTIONS_PATH.is_file():
        return json.loads(CAPTIONS_PATH.read_text(encoding="utf-8"))
    return {}


def caption(key: str, fallback: str) -> str:
    return latex_escape(load_captions().get(key, fallback))


def add_csv_labels(content: str) -> str:
    """Add a ``\\label{fig:<csv-stem>}`` to every figure environment.

    The label key is derived from the CSV file the figure is built from, so a
    figure generated from ``data/praticato_60.csv`` becomes referenceable as
    ``\\ref{fig:praticato_60}``. This keeps the reference name identical to the
    source data file the text model receives as input.
    """

    def repl(match: re.Match) -> str:
        block = match.group(0)
        if r"\label{" in block:
            return block
        csv_match = re.search(r"\{(?:data/)?([\w\-]+)\.csv\}", block)
        if not csv_match:
            return block
        stem = csv_match.group(1)
        label = f"    \\label{{fig:{stem}}}\n"
        idx = block.rfind("\\end{figure")
        return block[:idx] + label + block[idx:]

    return re.sub(
        r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}",
        repl,
        content,
        flags=re.DOTALL,
    )


def inject_block(tex: str, marker: str, content: str) -> str:
    start = f"% BEGIN: {marker} (auto-generated)"
    end = f"% END: {marker} (auto-generated)"
    block = f"{start}\n{content}\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if start in tex:
        return pattern.sub(lambda _m: block, tex, count=1)
    raise ValueError(f"Marker non trovato: {marker}")


def update_preamble(tex: str) -> str:
    colors_block = r"""
\definecolor{colorTicino}{HTML}{9467bd}
\definecolor{colorLugano}{HTML}{d62728}
\definecolor{colorLocarno}{HTML}{1f77b4}
\definecolor{colorBellinzona}{HTML}{e6c619}
\definecolor{colorMendrisio}{HTML}{17becf}
\definecolor{colorTreValli}{HTML}{2ca02c}
"""
    if "colorTicino" not in tex:
        tex = tex.replace(
            r"\definecolor{color1}{HTML}{1f77b4}",
            colors_block + r"\definecolor{color1}{HTML}{1f77b4}",
            1,
        )

    pgfplotsset = r"""\pgfplotsset{
    compat=1.18,
    every axis/.append style={
        grid=major,
        major grid style={gray!30, line width=0.35pt},
    },
    /pgf/number format/.cd,
    1000 sep={'},
    dec sep={.},
}"""
    old = r"""\pgfplotsset{
    compat=1.18,
    every axis/.append style={
        grid=major,
        major grid style={gray!30, line width=0.35pt},
    },
}"""
    if old in tex:
        tex = tex.replace(old, pgfplotsset, 1)
    return tex


def regional_line_plots(csv_rel: str) -> tuple[str, str]:
    csv_ref = csv_rel.replace("\\", "/")
    plots = [
        rf"\addplot[color=colorTicino, dashed, ultra thick] table [x=Anno, y=Cantonale, col sep=comma] {{{csv_ref}}};"
    ]
    for region in REGION_ORDER:
        col = braced_column(region)
        color = REGION_COLORS[region]
        plots.append(
            rf"\addplot[color={color}, {LINE_WIDTH}] table [x=Anno, y={col}, col sep=comma] {{{csv_ref}}};"
        )
    legend = ", ".join(REGION_LEGEND)
    return "\n    ".join(plots), legend


def build_offerta_figure() -> str:
    csv = "data/offerta_line.csv"
    plots, legend = regional_line_plots("data/offerta_line.csv")
    title = caption(
        "offerta_line",
        "Canone mediano cantonale e regionale per anno (CHF/m²)",
    )
    return rf"""\begin{{figure*}}[htbp]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        width=\textwidth,
        height=7cm,
        xlabel={{Anno}},
        ylabel={{Prezzo [CHF/m$^2$]}},
        legend columns=3,
        {LEGEND_BELOW},
        xtick=data,
        xticklabel style={{/pgf/number format/1000 sep=}}
    ]
    {plots}
    \legend{{{legend}}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{title}}}
\end{{figure*}}"""


def build_praticato_figures() -> str:
    df139 = pd.read_csv(ROOT / "data/praticato_139.csv")
    numeric_cols = [c for c in df139.columns if c != "id"]
    values = df139[numeric_cols].to_numpy().flatten().tolist()
    ymin, ymax = numeric_range(values, floor=None)
    bw, shifts = grouped_vertical_bars(len(df139), len(REGION_ORDER))

    plots139 = []
    for region, shift in zip(REGION_ORDER, shifts):
        plots139.append(
            rf"\addplot[fill={REGION_COLORS[region]}, {shift}] "
            rf"table [x=id, y={braced_column(region)}, col sep=comma] {{data/praticato_139.csv}};"
        )
    cap139 = caption(
        "praticato_139",
        "Canone locativo annuo mediano per tipologia di economia domestica (2021-2023) (CHF/m² anno)",
    )

    fig139 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar,
        width=\textwidth,
        height=9cm,
        bar width={bw},
        enlarge x limits=0.12,
        ymin={ymin},
        ymax={ymax},
        ylabel={{Canone locativo mediano [CHF]}},
        xtick={{0,1,2,3,4,5,6}},
        xticklabels={{
            {{Convivenze multiple}},
            {{Coppie con figli 25+}},
            {{Coppie con figli sotto 25}},
            {{Coppie senza figli}},
            {{Genitori soli con figli 25+}},
            {{Genitori soli con figli sotto 25}},
            {{Persone sole}}
        }},
        xticklabel style={{font=\scriptsize, rotate=45, anchor=east}},
        legend columns=5,
        {LEGEND_EXTRA_DEEP},
    ]
    {" ".join(plots139)}
    \legend{{Lugano, Locarno, Bellinzona, Mendrisio, Tre Valli}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap139}}}
\end{{figure}}"""

    bw60 = bar_width(5, stacked=True)
    cap60 = caption(
        "praticato_60",
        "Tipologia di edificio per regione",
    )
    fig60 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar stacked,
        width=\textwidth,
        height=7cm,
        bar width={bw60},
        ylabel={{Quota (\%)}},
        symbolic x coords={{{REGION_XCOORDS}}},
        xtick=data,
        legend columns=3,
        {LEGEND_BELOW},
        {STACKED_BAR_STYLE}
        {STACKED_LABEL_STYLE}
    ]
    \addplot[fill=color1, point meta=explicit] table [x=Region, y={{Case plurifamiliari_perc}}, meta={{Case plurifamiliari_abs}}, col sep=comma] {{data/praticato_60.csv}};
    \addplot[fill=color2, point meta=explicit] table [x=Region, y={{Case unifamiliari_perc}}, meta={{Case unifamiliari_abs}}, col sep=comma] {{data/praticato_60.csv}};
    \addplot[fill=color3, point meta=explicit] table [x=Region, y={{Edifici a uso misto o accessorio_perc}}, meta={{Edifici a uso misto o accessorio_abs}}, col sep=comma] {{data/praticato_60.csv}};
    \legend{{Case plurifamiliari, Case unifamiliari, Edifici a uso misto o accessorio}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap60}}}
\end{{figure}}"""

    bw62 = bar_width(5, stacked=True)
    cap62 = caption("praticato_62", "Distribuzione del parco immobiliare per epoca di costruzione e regione")
    fig62 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar stacked,
        width=\textwidth,
        height=7cm,
        bar width={bw62},
        ylabel={{Quota (\%)}},
        symbolic x coords={{{REGION_XCOORDS}}},
        xtick=data,
        legend columns=5,
        {LEGEND_BELOW},
        {STACKED_BAR_STYLE}
        {STACKED_LABEL_STYLE}
    ]
    \addplot[fill=color1, point meta=explicit] table [x=Region, y={{ante 1961_perc}}, meta={{ante 1961_abs}}, col sep=comma] {{data/praticato_62.csv}};
    \addplot[fill=color2, point meta=explicit] table [x=Region, y={{1961-1980_perc}}, meta={{1961-1980_abs}}, col sep=comma] {{data/praticato_62.csv}};
    \addplot[fill=color3, point meta=explicit] table [x=Region, y={{1981-1990_perc}}, meta={{1981-1990_abs}}, col sep=comma] {{data/praticato_62.csv}};
    \addplot[fill=color4, point meta=explicit] table [x=Region, y={{1991-2000_perc}}, meta={{1991-2000_abs}}, col sep=comma] {{data/praticato_62.csv}};
    \addplot[fill=color5, point meta=explicit] table [x=Region, y={{post 2000_perc}}, meta={{post 2000_abs}}, col sep=comma] {{data/praticato_62.csv}};
    \legend{{ante 1961, 1961-1980, 1981-1990, 1991-2000, post 2000}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap62}}}
\end{{figure}}"""

    cap146 = caption(
        "praticato_146",
        "Indicatori medi del mercato locativo praticato a livello cantonale",
    )
    table146 = rf"""\begin{{table}}[H]
    \centering
    \footnotesize
    \label{{tab:praticato_146}}
    \pgfplotstabletypeset[
        col sep=comma,
        every head row/.style={{before row=\toprule, after row=\midrule}},
        every last row/.style={{after row=\bottomrule}},
        columns={{Year Data,Media di Prezzo Mq,Media di Net Surface,Media di Number Of Rooms,Media di Number Of People}},
        columns/{{Year Data}}/.style={{string type, column name=Anno}},
        columns/{{Media di Prezzo Mq}}/.style={{fixed, fixed zerofill, precision=1, column name={{\makecell[r]{{Prezzo medio al m\textsuperscript{{2}} \\ {{[}}CHF{{]}}}}}}}},
        columns/{{Media di Net Surface}}/.style={{fixed, fixed zerofill, precision=1, column name={{\makecell[r]{{Superficie media \\ {{[}}m\textsuperscript{{2}}{{]}}}}}}}},
        columns/{{Media di Number Of Rooms}}/.style={{fixed, fixed zerofill, precision=2, column name={{\makecell[r]{{Nr locali \\ medi}}}}}},
        columns/{{Media di Number Of People}}/.style={{fixed, fixed zerofill, precision=2, column name={{\makecell[r]{{Nr persone \\ medie}}}}}}
    ]{{data/praticato_146.csv}}
    \caption{{{cap146}}}
\end{{table}}"""

    return "\n\n".join([fig139, fig60, fig62, table146])


def build_reddito_figures() -> str:
    plots, legend = regional_line_plots("data/reddito_line.csv")
    cap_line = caption("reddito_line", "Evoluzione reddito medio equivalente")
    fig_line = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        width=\textwidth,
        height=7cm,
        xlabel={{Anno}},
        ylabel={{Media reddito [kCHF]}},
        legend columns=3,
        {LEGEND_BELOW},
        xtick=data,
        xticklabel style={{/pgf/number format/1000 sep=}}
    ]
    {plots}
    \legend{{{legend}}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap_line}}}
\end{{figure}}"""

    bw = bar_width(5, stacked=True)
    cap75 = caption(
        "reddito_75",
        "Distribuzione fasce di reddito per regione (quota % e valori assoluti)",
    )
    fig75 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar stacked,
        width=\textwidth,
        height=7cm,
        bar width={bw},
        ylabel={{Quota (\%)}},
        symbolic x coords={{{REGION_XCOORDS}}},
        xtick=data,
        legend columns=3,
        {LEGEND_BELOW},
        {STACKED_BAR_STYLE}
        {STACKED_LABEL_STYLE}
    ]
    \addplot[fill=color1, point meta=explicit] table [x=Regione, y={{0 30_perc}}, meta={{0 30_abs}}, col sep=comma] {{data/reddito_75.csv}};
    \addplot[fill=color2, point meta=explicit] table [x=Regione, y={{30 40_perc}}, meta={{30 40_abs}}, col sep=comma] {{data/reddito_75.csv}};
    \addplot[fill=color3, point meta=explicit] table [x=Regione, y={{40 50_perc}}, meta={{40 50_abs}}, col sep=comma] {{data/reddito_75.csv}};
    \addplot[fill=color4, point meta=explicit] table [x=Regione, y={{50 75_perc}}, meta={{50 75_abs}}, col sep=comma] {{data/reddito_75.csv}};
    \addplot[fill=color5, point meta=explicit] table [x=Regione, y={{75+_perc}}, meta={{75+_abs}}, col sep=comma] {{data/reddito_75.csv}};
    \legend{{0--30k, 30--40k, 40--50k, 50--75k, 75k+}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap75}}}
\end{{figure}}"""
    return f"{fig_line}\n\n{fig75}"


def build_tasso_figure() -> str:
    df = pd.read_csv(ROOT / "data/tasso_di_sforzo_121.csv")
    df["sort_key"] = df[["TassoPraticato_pct", "TassoOfferto_pct"]].max(axis=1)
    df = df.sort_values("sort_key", ascending=True).reset_index(drop=True)
    y_coords = ",".join(df["Regione"].tolist())

    values = df["TassoPraticato_pct"].tolist() + df["TassoOfferto_pct"].tolist()
    xmin, xmax = numeric_range(values, floor=None)

    bw, shifts = paired_horizontal_bars(len(df), 2)
    cap = caption(
        "tasso_di_sforzo_121",
        "Tasso di sforzo praticato e offerto per regione",
    )
    return rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        width=\textwidth,
        height=7.5cm,
        xbar,
        bar width={bw},
        enlarge y limits=0.18,
        xlabel={{Tasso di sforzo (\%)}},
        xmin={xmin},
        xmax={xmax},
        symbolic y coords={{{y_coords}}},
        ytick=data,
        legend columns=2,
        {LEGEND_BELOW},
        yticklabel style={{font=\footnotesize}},
        {HORIZONTAL_BAR_LABEL_STYLE}
    ]
    \addplot[fill=color1, {shifts[0]}] table [y=Regione, x=TassoPraticato_pct, col sep=comma] {{data/tasso_di_sforzo_121.csv}};
    \addplot[fill=color2, {shifts[1]}] table [y=Regione, x=TassoOfferto_pct, col sep=comma] {{data/tasso_di_sforzo_121.csv}};
    \legend{{Mercato praticato, Mercato offerto}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap}}}
\end{{figure}}"""


def build_sostenibile_figures() -> str:
    df104 = pd.read_csv(ROOT / "data/sostenibile_104.csv")
    n104 = len(df104)
    bw104 = bar_width(n104)
    xtick_vals = ",".join(str(v) for v in df104["NrLocali"].tolist())
    xtick_labels = ",\n            ".join(
        "{" + latex_escape(str(v)) + "}" for v in df104["CategoriaLocali"].tolist()
    )
    cap104 = caption(
        "sostenibile_104",
        "Alloggi in offerta a pigione sostenibile per nr locali — 2024",
    )
    fig104 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar,
        width=\textwidth,
        height=7.5cm,
        bar width={bw104},
        ylabel={{Conteggio}},
        xlabel={{Numero di locali}},
        xtick={{{xtick_vals}}},
        xticklabels={{
            {xtick_labels}
        }},
        xticklabel style={{font=\scriptsize, rotate=35, anchor=east}},
        {BAR_LABEL_STYLE}
    ]
    \addplot[fill=color1] table [x=NrLocali, y=Conteggio, col sep=comma] {{data/sostenibile_104.csv}};
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap104}}}
\end{{figure}}"""

    df118 = pd.read_csv(ROOT / "data/sostenibile_118.csv")
    values118 = df118["Conteggio"].tolist()
    xmin118, _ = numeric_range(values118, floor=0)
    bw118, _ = paired_horizontal_bars(len(df118), 1)
    cap118 = caption(
        "sostenibile_118",
        "Alloggi in offerta a pigione sostenibile — 2024",
    )
    fig118 = rf"""\begin{{figure}}[H]
    \centering
    \pgfplotstableread[col sep=comma]{{data/sostenibile_118.csv}}\sostenibilecomuni
    \begin{{tikzpicture}}
    \begin{{axis}}[
        xbar,
        width=\textwidth,
        height=8.5cm,
        bar width={bw118},
        enlarge y limits=0.18,
        xlabel={{Conteggio}},
        xmin={xmin118},
        ytick=data,
        yticklabels from table={{\sostenibilecomuni}}{{Comune}},
        y dir=reverse,
        yticklabel style={{font=\footnotesize}},
        {HORIZONTAL_BAR_LABEL_STYLE}
    ]
    \addplot[fill=color2] table [x=Conteggio, y expr=\coordindex] {{\sostenibilecomuni}};
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap118}}}
\end{{figure}}"""

    cap143 = caption(
        "sostenibile_143",
        "Distribuzione delle inserzioni per regione (quota % e valori assoluti)",
    )
    fig143 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar,
        width=\textwidth,
        height=7.5cm,
        bar width={bar_width(5)},
        ylabel={{Conteggio}},
        symbolic x coords={{{REGION_XCOORDS}}},
        xtick=data,
        {BAR_LABEL_STYLE}
    ]
    \addplot[fill=color3] table [x=Regione, y=Conteggio, col sep=comma] {{data/sostenibile_143.csv}};
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap143}}}
\end{{figure}}"""

    cap102 = caption(
        "sostenibile_102",
        "Distribuzione delle inserzioni per durata d'inserzione",
    )
    fig102 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar,
        width=\textwidth,
        height=7.5cm,
        bar width={bar_width(9)},
        ylabel={{Conteggio}},
        xlabel={{Durata d'inserzione}},
        xtick=data,
        {BAR_LABEL_STYLE}
    ]
    \addplot[fill=color4] table [x=DurataInserzione, y=Conteggio, col sep=comma] {{data/sostenibile_102.csv}};
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap102}}}
\end{{figure}}"""

    return "\n\n".join([fig104, fig118, fig143, fig102])


def build_scompenso_figures() -> str:
    cap87 = caption("scompenso_87", "Evoluzione dello scompenso (scenari AB e CD)")
    fig87 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        width=\textwidth,
        height=7.5cm,
        enlarge y limits={{0.14}},
        xlabel={{Anno}},
        ylabel={{Scompenso [CHF]}},
        xtick=data,
        yticklabel style={{/pgf/number format/fixed, /pgf/number format/1000 sep={{\,}}}},
        legend columns=2,
        {LEGEND_SCOMPENSO_LINE},
        xticklabel style={{/pgf/number format/1000 sep=}},
        clip mode=individual,
        nodes near coords,
        every node near coord/.append style={{font=\scriptsize, anchor=south, yshift=4pt, /pgf/number format/fixed, /pgf/number format/precision=0, /pgf/number format/1000 sep={{\,}}}},
    ]
    \addplot[color=color1, mark=*, {LINE_WIDTH}] table [x=Anno, y=AB, col sep=comma] {{data/scompenso_87.csv}};
    \addplot[color=color2, mark=square*, {LINE_WIDTH}] table [x=Anno, y=CD, col sep=comma] {{data/scompenso_87.csv}};
    \legend{{Scenario AB, Scenario CD}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap87}}}
\end{{figure}}"""

    df136 = pd.read_csv(ROOT / "data/scompenso_136.csv")
    bw136, shifts = grouped_vertical_bars(len(df136), len(REGION_ORDER))
    plots136 = []
    for region, shift in zip(REGION_ORDER, shifts):
        plots136.append(
            rf"\addplot[fill={REGION_COLORS[region]}, {shift}] "
            rf"table [x=Superficie, y={braced_column(region)}, col sep=comma] {{data/scompenso_136.csv}};"
        )

    cap136 = caption(
        "scompenso_136",
        "Scompenso annuo di pigione sostenibile regionali per dimensione dell'unità — 2024 — scenario CD",
    )
    fig136 = rf"""\begin{{figure}}[H]
    \centering
    \begin{{tikzpicture}}
    \begin{{axis}}[
        ybar,
        width=\textwidth,
        height=8cm,
        bar width={bw136},
        enlarge x limits=0.25,
        ylabel={{Scompenso [CHF]}},
        symbolic x coords={{2-2.5 locali (50-70m²),3-3.5 locali (70-90m²),4-4.5 locali (90-110m²)}},
        xtick=data,
        xticklabels={{
            {{2-2.5 locali\\(50-70m²)}},
            {{3-3.5 locali\\(70-90m²)}},
            {{4-4.5 locali\\(90-110m²)}}
        }},
        xticklabel style={{font=\scriptsize, align=center}},
        legend columns=3,
        {LEGEND_SCOMPENSO_BAR},
        {GROUPED_YBAR_LABEL_STYLE}
    ]
    {" ".join(plots136)}
    \legend{{Lugano, Locarno, Bellinzona, Mendrisio, Tre Valli}}
    \end{{axis}}
    \end{{tikzpicture}}
    \caption{{{cap136}}}
\end{{figure}}"""

    return f"{fig87}\n\n{fig136}"


def ensure_offerta_marker(tex: str) -> str:
    start = "% BEGIN: offerta_figure (auto-generated)"
    if start in tex:
        return tex
    pattern = r"(% END: offerta_prosa \(auto-generated\)\s*\n)(\s*\\begin\{figure\*\})"
    replacement = r"\1\n" + start + r"\n\2"
    return re.sub(pattern, replacement, tex, count=1)


def ensure_offerta_marker_end(tex: str) -> str:
    end = "% END: offerta_figure (auto-generated)"
    if end in tex:
        return tex
    pattern = r"(\\end\{figure\*\}\s*\n)(% BEGIN: offerta_tabellina)"
    replacement = r"\1" + end + r"\n\n\2"
    return re.sub(pattern, replacement, tex, count=1)


def main() -> None:
    tex = TEX_PATH.read_text(encoding="utf-8")
    tex = update_preamble(tex)
    tex = ensure_offerta_marker(tex)
    tex = ensure_offerta_marker_end(tex)

    tex = inject_block(tex, "offerta_figure", add_csv_labels(build_offerta_figure()))
    tex = inject_block(tex, "praticato_figure", add_csv_labels(build_praticato_figures()))
    tex = inject_block(tex, "reddito_figure", add_csv_labels(build_reddito_figures()))
    tex = inject_block(tex, "tasso_sforzo_figure", add_csv_labels(build_tasso_figure()))
    tex = inject_block(tex, "sostenibile_figure", add_csv_labels(build_sostenibile_figures()))
    tex = inject_block(tex, "scompenso_figure", add_csv_labels(build_scompenso_figures()))

    TEX_PATH.write_text(tex, encoding="utf-8")
    print(f"Figure PGFPlots rigenerate in {TEX_PATH}")


if __name__ == "__main__":
    main()
