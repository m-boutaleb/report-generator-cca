import re

with open("main.tex", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Pgfplots and colors
preamble_addition = r"""\usepackage{float}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{pgfplotstable}
\definecolor{color1}{HTML}{1f77b4}
\definecolor{color2}{HTML}{ff7f0e}
\definecolor{color3}{HTML}{2ca02c}
\definecolor{color4}{HTML}{d62728}
\definecolor{color5}{HTML}{9467bd}
"""
content = content.replace(r"\usepackage{float}", preamble_addition, 1)

# 2. Add Reddito section and rename Aggiornamento scompenso
content = content.replace(r"\section{Aggiornamento scompenso 2024}", r"""\section{Reddito}

\section{Aggiornamento scompenso}""")

# 3. Replace Piattaforma di monitoraggio with Offerta a pigione sostenibile
# We find the string from "\section{Piattaforma di monitoraggio}" up to just before "\section{Conclusioni}"
pattern = r"\\section\{Piattaforma di monitoraggio\}.*?%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
replacement = r"""\section{Offerta a pigione sostenibile}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"""
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("main.tex", "w", encoding="utf-8") as f:
    f.write(content)

print("Applied structural changes.")
