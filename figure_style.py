"""Shared styling helpers for PGFPlots figure generation."""

from __future__ import annotations

import re
from urllib.parse import unquote

# Legend order and colors for regional series (consistent across all charts).
REGION_ORDER = ("Lugano", "Locarno", "Bellinzona", "Mendrisio", "Tre Valli")

REGION_COLORS = {
    "Ticino": "colorTicino",
    "Cantonale": "colorTicino",
    "Lugano": "colorLugano",
    "Locarno": "colorLocarno",
    "Bellinzona": "colorBellinzona",
    "Mendrisio": "colorMendrisio",
    "Tre Valli": "colorTreValli",
}

REGION_LEGEND = ("Ticino", "Lugano", "Locarno", "Bellinzona", "Mendrisio", "Tre Valli")
REGION_XCOORDS = ",".join(REGION_ORDER)

PREAMBLE_COLORS = r"""
\definecolor{colorTicino}{HTML}{9467bd}
\definecolor{colorLugano}{HTML}{d62728}
\definecolor{colorLocarno}{HTML}{1f77b4}
\definecolor{colorBellinzona}{HTML}{e6c619}
\definecolor{colorMendrisio}{HTML}{17becf}
\definecolor{colorTreValli}{HTML}{2ca02c}
\definecolor{color1}{HTML}{1f77b4}
\definecolor{color2}{HTML}{ff7f0e}
\definecolor{color3}{HTML}{2ca02c}
\definecolor{color4}{HTML}{d62728}
\definecolor{color5}{HTML}{9467bd}
"""

# ymax leaves a little headroom above 100: rounded percentages can sum to
# 100.1, and with the default `unbounded coords=discard` PGFPlots would drop
# the top segment's data label when its cumulative coordinate exceeds ymax.
STACKED_BAR_STYLE = (
    "ymin=0, ymax=103, scaled y ticks=false, ytick={0,20,40,60,80,100},"
)

# Stacked bars: label centered inside each segment, drawn once at axis level
# (the addplots must NOT repeat `nodes near coords`, only `point meta=explicit`).
STACKED_LABEL_STYLE = (
    r"nodes near coords={\pgfmathprintnumber{\pgfplotspointmeta}}, "
    r"nodes near coords align={center}, "
    r"every node near coord/.append style={font=\tiny, text=black, fill=white, "
    r"fill opacity=0.9, text opacity=1, inner sep=0.6pt, rounded corners=1pt}, "
    r"clip mode=individual, "
)

# Simple vertical bars (single series): label horizontally centered above the bar.
BAR_LABEL_STYLE = (
    r"nodes near coords, "
    r"every node near coord/.append style={font=\scriptsize, anchor=south, yshift=1pt}, "
    r"clip mode=individual, "
)

# Horizontal bars: label just to the right of each bar tip.
HORIZONTAL_BAR_LABEL_STYLE = (
    r"nodes near coords, "
    r"every node near coord/.append style={font=\scriptsize, anchor=west, xshift=2pt, "
    r"/pgf/number format/fixed, /pgf/number format/precision=1}, "
    r"clip mode=individual, "
)

# Grouped vertical bars (many narrow bars): vertical label centered over each bar,
# reading upward so adjacent labels do not collide.
GROUPED_YBAR_LABEL_STYLE = (
    r"nodes near coords, "
    r"every node near coord/.append style={font=\tiny, rotate=90, anchor=west, "
    r"/pgf/number format/fixed, /pgf/number format/precision=0, "
    r"/pgf/number format/1000 sep={'}}, "
    r"clip mode=individual, "
)

LINE_WIDTH = "very thick"
LEGEND_BELOW = r"legend style={at={(0.5,-0.28)}, anchor=north, font=\footnotesize}"
LEGEND_DEEP = r"legend style={at={(0.5,-0.42)}, anchor=north, font=\footnotesize}"
LEGEND_EXTRA_DEEP = r"legend style={at={(0.5,-0.58)}, anchor=north, font=\footnotesize}"
LEGEND_SCOMPENSO_LINE = r"legend style={at={(0.5,-0.36)}, anchor=north, font=\footnotesize}"
LEGEND_SCOMPENSO_BAR = r"legend style={at={(0.5,-0.34)}, anchor=north, font=\footnotesize}"


def format_title_from_disposition(header: str, fallback: str = "") -> str:
    """Build a human-readable Italian title from a Content-Disposition header."""
    match = re.search(r'filename="([^"]+)"', header or "")
    if not match:
        return fallback
    return format_title_from_filename(match.group(1), fallback)


def format_title_from_filename(filename: str, fallback: str = "") -> str:
    name = unquote(filename)
    name = re.sub(r"\.csv$", "", name, flags=re.I)
    name = re.sub(r"[_\s]*\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*$", "", name)
    name = re.sub(r"__+", " — ", name)
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    # Rimuove timestamp ISO in coda (es. 2026-06-12T11:53:16.625431618Z)
    name = re.sub(r"(?:\s*—\s*|\s+)?\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"\s*—\s*$", "", name).strip()

    replacements = (
        (r"\bchf m²a\b", "CHF/m²"),
        (r"\bchf m²\b", "CHF/m²"),
        (r"\bchf m2\b", "CHF/m²"),
        (r"\bchf\b", "CHF"),
        (r"\bm²\b", "m²"),
        (r"\bscenario cd\b", "scenario CD"),
        (r"\bscenario ab\b", "scenario AB"),
        (r"\bscenari ab e cd\b", "scenari AB e CD"),
        (r"\bunita\b", "unità"),
        (r"\beta degli\b", "età degli"),
        (r"\b(\d{4})\s*—", r"(\1) —"),
    )
    for pattern, repl in replacements:
        name = re.sub(pattern, repl, name, flags=re.I)

    name = re.sub(r"\s*\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"\s*—\s*$", "", name).strip()

    if not name:
        return fallback
    return name[0].upper() + name[1:]


def compute_bar_width_pt(
    n_categories: int,
    n_series: int = 1,
    *,
    stacked: bool = False,
    max_width: float = 32.0,
    min_width: float = 6.0,
) -> float:
    """Estimate a readable bar width from category/series counts."""
    n_categories = max(n_categories, 1)
    if stacked:
        width = 240.0 / n_categories
    else:
        width = 200.0 / (n_categories * max(n_series, 1))
    return max(min_width, min(max_width, width))


def bar_width(n_categories: int, n_series: int = 1, *, stacked: bool = False) -> str:
    return f"{compute_bar_width_pt(n_categories, n_series, stacked=stacked):.0f}pt"


def grouped_bar_shifts(n_series: int, bar_width_pt: float, *, gap_pt: float = 1.5) -> list[str]:
    total = n_series * bar_width_pt + (n_series - 1) * gap_pt
    start = -total / 2.0 + bar_width_pt / 2.0
    step = bar_width_pt + gap_pt
    return [f"bar shift={start + i * step:.1f}pt" for i in range(n_series)]


def grouped_vertical_bars(n_categories: int, n_series: int) -> tuple[str, list[str]]:
    """Bar width and shifts for side-by-side vertical grouped bars.

    Bars inside a group touch each other (gap 0) so each group stays compact
    and the white space between groups is maximised.
    """
    bw = max(6.0, min(11.0, 200.0 / (max(n_categories, 1) * max(n_series, 1))))
    shifts = grouped_bar_shifts(n_series, bw, gap_pt=0.0)
    return f"{bw:.1f}pt", shifts


def paired_horizontal_bars(n_categories: int, n_series: int = 2) -> tuple[str, list[str]]:
    """Bar width and shifts for side-by-side horizontal bars without overlap."""
    row_pitch = 180.0 / max(n_categories, 1)
    bw = min(12.0, max(6.0, row_pitch * 0.50 / max(n_series, 1)))
    if n_series <= 1:
        return f"{bw:.1f}pt", ["bar shift=0pt"]
    shifts = grouped_bar_shifts(n_series, bw, gap_pt=1.5)
    return f"{bw:.1f}pt", shifts


def numeric_range(values: list[float], *, padding_ratio: float = 0.08, floor: float | None = None) -> tuple[float, float]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return 0.0, 1.0
    lo = min(clean)
    hi = max(clean)
    span = max(hi - lo, abs(hi) * 0.05, 1.0)
    pad = span * padding_ratio
    ymin = lo - pad if floor is None else max(floor, lo - pad)
    ymax = hi + pad
    return round(ymin, 1), round(ymax, 1)


def latex_escape(text: str) -> str:
    replacements = {
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def braced_column(name: str) -> str:
    if " " in name or any(ch in name for ch in "%&_"):
        return "{" + name + "}"
    return name
