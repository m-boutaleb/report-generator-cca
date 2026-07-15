import re

import os

if not os.path.exists("main.tex"):
    with open("main.tex", "w", encoding="utf-8") as f:
        f.write("")  # crea un file vuoto se non esiste

with open("main.tex", "r", encoding="utf-8") as f:
    text = f.read()

# 1. off_regioni
p1 = r"\\begin\{figure\*\}\[\]\s*\\centering\s*\\includegraphics\[(.*?)\]\{off_regioni\.png\}\s*\\caption\{(.*?)\}\s*\\label\{off1\}\s*\\end\{figure\*\}"
r1 = r"""\begin{figure*}[htbp]
    \centering
    \begin{tikzpicture}
    \begin{axis}[
        width=10cm,
        height=6cm,
        xlabel={Anno},
        ylabel={Prezzo [CHF/m$^2$]},
        xtick=data,
        nodes near coords,
        ymin=200, ymax=235,
        grid=major,
        bar width=20pt,
        ybar
    ]
    \addplot[fill=color1] table [x=Anno, y=Prezzo, col sep=comma] {csv_data/off_cantonale.csv};
    \end{axis}
    \end{tikzpicture}
    \caption{Evoluzione del canone mediano offerto cantonale [CHF/$mˆ2$ annui] per anno di riferimento}
    \label{off1}
\end{figure*}"""
text = re.sub(p1, lambda m: r1, text, flags=re.DOTALL)

# 2. RS_ANNO (replaces RS1)
p2 = r"\\begin\{figure\*\}\[htbp\]\s*\\centering\s*\\includegraphics\[(.*?)\]\{RS_ANNO\.png\}\s*\\caption\{(.*?)\}\s*\\label\{RS1\}\s*\\end\{figure\*\}"
r2 = r"""\begin{figure*}[htbp]
    \centering
    \begin{tikzpicture}
    \begin{axis}[
        width=\textwidth,
        height=7cm,
        ybar,
        bar width=5pt,
        enlarge x limits=0.15,
        ylabel={Conteggio},
        symbolic x coords={ante 1961,1961-1980,1981-1990,1991-2000,post 2000},
        xtick=data,
        legend style={at={(0.5,-0.15)}, anchor=north, legend columns=-1},
    ]
    \addplot[fill=color1] table [x={Anno di costruzione}, y=Bellinzona, col sep=comma] {csv_data/rs_anno.csv};
    \addplot[fill=color2] table [x={Anno di costruzione}, y=Locarno, col sep=comma] {csv_data/rs_anno.csv};
    \addplot[fill=color3] table [x={Anno di costruzione}, y=Lugano, col sep=comma] {csv_data/rs_anno.csv};
    \addplot[fill=color4] table [x={Anno di costruzione}, y=Mendrisio, col sep=comma] {csv_data/rs_anno.csv};
    \addplot[fill=color5] table [x={Anno di costruzione}, y={Tre Valli}, col sep=comma] {csv_data/rs_anno.csv};
    \legend{Bellinzona,Locarno,Lugano,Mendrisio,Tre Valli}
    \end{axis}
    \end{tikzpicture}
    \caption{Anno di costruzione per regione e relativo conteggio delle osservazioni}
    \label{RS1}
\end{figure*}"""
text = re.sub(p2, lambda m: r2, text, flags=re.DOTALL)

# 3. RS_ED (replaces RS2)
p3 = r"\\begin\{figure\*\}\[htbp\]\s*\\centering\s*\\includegraphics\[(.*?)\]\{RS_ED\.png\}\s*\\caption\{(.*?)\}\s*\\label\{RS2\}\s*\\end\{figure\*\}"
r3 = r"""\begin{figure*}[htbp]
    \centering
    \begin{tikzpicture}
    \begin{axis}[
        width=14cm,
        height=7cm,
        ybar,
        bar width=8pt,
        enlarge x limits=0.15,
        ylabel={Percentuale (\%)},
        symbolic x coords={Bellinzona,Locarno,Lugano,Mendrisio,Tre Valli},
        xtick=data,
        legend style={at={(0.5,-0.15)}, anchor=north, legend columns=2},
        every node near coord/.append style={font=\tiny, rotate=90, anchor=west},
        nodes near coords align={vertical}
    ]
    \addplot[fill=color1, point meta=explicit, nodes near coords] table [x=Region, y={Case plurifamiliari_perc}, meta={Case plurifamiliari_abs}, col sep=comma] {csv_data/rs_ed.csv};
    \addplot[fill=color2, point meta=explicit, nodes near coords] table [x=Region, y={Case unifamiliari_perc}, meta={Case unifamiliari_abs}, col sep=comma] {csv_data/rs_ed.csv};
    \addplot[fill=color3, point meta=explicit, nodes near coords] table [x=Region, y={Edifici ad uso parzialmente abitativo_perc}, meta={Edifici ad uso parzialmente abitativo_abs}, col sep=comma] {csv_data/rs_ed.csv};
    \addplot[fill=color4, point meta=explicit, nodes near coords] table [x=Region, y={Edifici con utilizzazione accessoria_perc}, meta={Edifici con utilizzazione accessoria_abs}, col sep=comma] {csv_data/rs_ed.csv};
    \legend{Case plurifamiliari,Case unifamiliari,Edifici parzialmente abitativo,Utilizzazione accessoria}
    \end{axis}
    \end{tikzpicture}
    \caption{Tipologia di edificio per regione (\% ed etichette con osservazioni assolute)}
    \label{RS2}
\end{figure*}"""
text = re.sub(p3, lambda m: r3, text, flags=re.DOTALL)

# 4. Scompenso1 and side by side (replaces SCO1)
p4 = r"\\begin\{figure\*\}\[htbp\]\s*\\centering\s*\\includegraphics\[(.*?)\]\{scompenso1\.png\}\s*\\caption\{(.*?)\}\s*\\label\{SCO1\}\s*\\end\{figure\*\}"
r4 = r"""\begin{figure*}[htbp]
    \centering
    \begin{minipage}{0.48\textwidth}
        \centering
        \begin{tikzpicture}
        \begin{axis}[
            width=\textwidth,
            height=6cm,
            xlabel={Anno},
            ylabel={Somma di scompenso},
            xtick=data,
            yticklabel style={/pgf/number format/fixed},
            legend style={at={(0.5,-0.2)}, anchor=north, legend columns=-1},
            grid=major
        ]
        \addplot[color=color1, mark=*, thick] table [x=anno, y=AB, col sep=comma] {csv_data/scompenso1.csv};
        \addplot[color=color2, mark=square*, thick] table [x=anno, y=CD, col sep=comma] {csv_data/scompenso1.csv};
        \legend{Scenario AB, Scenario CD}
        \end{axis}
        \end{tikzpicture}
        \caption{Evoluzione scompenso (scenari)}
        \label{SCO1}
    \end{minipage}\hfill
    \begin{minipage}{0.48\textwidth}
        \centering
        \begin{tikzpicture}
        \begin{axis}[
            width=\textwidth,
            height=6cm,
            xbar,
            bar width=3pt,
            enlarge y limits=0.2,
            xlabel={Somma Scompenso},
            symbolic y coords={4-4.5 locali,3-3.5 locali,2-2.5 locali},
            ytick=data,
            legend style={at={(0.5,-0.2)}, anchor=north, legend columns=2, font=\tiny, draw=none, fill=none},
            yticklabel style={font=\scriptsize}
        ]
        \addplot[fill=color1] table [y=Superficie, x=Bellinzona, col sep=comma] {csv_data/scompenso_side.csv};
        \addplot[fill=color2] table [y=Superficie, x=Locarno, col sep=comma] {csv_data/scompenso_side.csv};
        \addplot[fill=color3] table [y=Superficie, x=Lugano, col sep=comma] {csv_data/scompenso_side.csv};
        \addplot[fill=color4] table [y=Superficie, x=Mendrisio, col sep=comma] {csv_data/scompenso_side.csv};
        \addplot[fill=color5] table [y=Superficie, x={Tre Valli}, col sep=comma] {csv_data/scompenso_side.csv};
        \legend{Bellinzona,Locarno,Lugano,Mendrisio,Tre Valli}
        \end{axis}
        \end{tikzpicture}
        \caption{Scompenso per superficie e regione}
        \label{SCO1_side}
    \end{minipage}
\end{figure*}"""
text = re.sub(p4, lambda m: r4, text, flags=re.DOTALL)

# 5. Remove scompenso3 (replaces SCO3)
p5 = r"\\begin\{figure\*\}\[htbp\]\s*\\centering\s*\\includegraphics\[(.*?)\]\{scompenso3\.png\}\s*\\caption\{(.*?)\}\s*\\label\{SCO3\}\s*\\end\{figure\*\}"
text = re.sub(p5, "", text, flags=re.DOTALL)

with open("main.tex", "w", encoding="utf-8") as f:
    f.write(text)

print("Applied tikz injections.")
