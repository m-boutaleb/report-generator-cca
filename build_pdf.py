#!/usr/bin/env python3
"""Compile main.tex to PDF using pdflatex or latexmk."""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from config import ROOT, TEX_PATH

RE_CSV = re.compile(r"\{data/([^}]+\.csv)\}")

PDF_PATH = ROOT / "main.pdf"
AUX_EXTENSIONS = (".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz")


def pdf_is_locked(pdf_path: Path) -> bool:
    if not pdf_path.is_file():
        return False
    try:
        with pdf_path.open("r+b"):
            return False
    except OSError:
        return True


def pdf_write_error_hint(pdf_path: Path) -> str:
    if pdf_is_locked(pdf_path):
        return (
            f"Impossibile scrivere {pdf_path.name}: il file è probabilmente aperto "
            f"in un lettore PDF. Chiudi {pdf_path.name} e riprova."
        )
    return f"Impossibile scrivere {pdf_path.name}. Verifica permessi o spazio su disco."


def find_command(name: str) -> str | None:
    return shutil.which(name)


def run_pdflatex(tex_path: Path, passes: int, *, jobname: str | None = None) -> None:
    engine = find_command("pdflatex")
    if not engine:
        raise RuntimeError(
            "pdflatex non trovato nel PATH. Installa MiKTeX o TeX Live "
            "e assicurati che pdflatex sia disponibile."
        )

    stem = tex_path.stem
    args = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
    ]
    if jobname:
        args.append(f"-jobname={jobname}")
    args.append(str(tex_path.name))

    for i in range(1, passes + 1):
        print(f"--- pdflatex pass {i}/{passes} ---")
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            log = ROOT / f"{jobname or stem}.log"
            hint = f" Vedi {log}" if log.is_file() else ""
            log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            if "I can't write on file" in log_text and jobname is None:
                raise RuntimeError(pdf_write_error_hint(tex_path.with_suffix(".pdf")))
            raise RuntimeError(f"pdflatex fallito (exit {result.returncode}).{hint}")


def run_latexmk(tex_path: Path) -> None:
    engine = find_command("latexmk")
    if not engine:
        raise RuntimeError("latexmk non trovato nel PATH.")

    print("--- latexmk -pdf ---")
    result = subprocess.run(
        [
            engine,
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            str(tex_path.name),
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"latexmk fallito (exit {result.returncode}).")


def required_csvs(tex_path: Path) -> list[Path]:
    text = tex_path.read_text(encoding="utf-8")
    names = sorted(set(RE_CSV.findall(text)))
    return [ROOT / "data" / name for name in names]


def check_csv_dependencies(tex_path: Path) -> list[Path]:
    missing = [p for p in required_csvs(tex_path) if not p.is_file()]
    if missing:
        lines = "\n".join(f"  - {p.relative_to(ROOT)}" for p in missing)
        raise RuntimeError(
            "CSV mancanti referenziati in main.tex:\n"
            f"{lines}\n"
            "Esegui prima: python data_fetch.py"
        )
    return missing


def clean_aux(tex_path: Path) -> None:
    stem = tex_path.stem
    removed = []
    for ext in AUX_EXTENSIONS:
        p = ROOT / f"{stem}{ext}"
        if p.is_file():
            p.unlink()
            removed.append(p.name)
    if removed:
        print("Rimossi:", ", ".join(removed))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila main.tex in PDF")
    parser.add_argument(
        "--tex",
        type=Path,
        default=TEX_PATH,
        help=f"File LaTeX da compilare (default: {TEX_PATH.name})",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=2,
        help="Passate pdflatex (default: 2, per indice e riferimenti)",
    )
    parser.add_argument(
        "--latexmk",
        action="store_true",
        help="Usa latexmk invece di pdflatex ripetuto",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Rimuove file ausiliari (.aux, .log, ...) prima della compilazione",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Solo pulizia file ausiliari, senza compilare",
    )
    parser.add_argument(
        "--skip-csv-check",
        action="store_true",
        help="Non verificare la presenza dei CSV prima di compilare",
    )
    args = parser.parse_args()

    tex_path = args.tex if args.tex.is_absolute() else ROOT / args.tex
    if not tex_path.is_file():
        print(f"Errore: file non trovato: {tex_path}", file=sys.stderr)
        return 1

    if args.clean or args.clean_only:
        clean_aux(tex_path)
        if args.clean_only:
            return 0

    if not args.skip_csv_check:
        try:
            check_csv_dependencies(tex_path)
        except RuntimeError as exc:
            print(f"Errore: {exc}", file=sys.stderr)
            return 1

    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_is_locked(pdf_path):
        print(f"Attenzione: {pdf_write_error_hint(pdf_path)}", file=sys.stderr)
        return 1

    try:
        if args.latexmk:
            run_latexmk(tex_path)
        else:
            run_pdflatex(tex_path, args.passes)
    except RuntimeError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    pdf = tex_path.with_suffix(".pdf")
    if pdf.is_file():
        print(f"PDF generato: {pdf}")
        return 0

    print(f"Errore: PDF non creato ({pdf})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
