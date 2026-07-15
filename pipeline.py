#!/usr/bin/env python3
"""End-to-end report pipeline: fetch → figures → prose → PDF → ref check."""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from api_retry import (
    GEMINI_MAX_CALLS_PER_MINUTE,
    GEMINI_MIN_PAUSE_SECONDS,
    GEMINI_RATE_WINDOW_SECONDS,
    RETRY_MAX_ATTEMPTS,
    MinuteRateLimiter,
)
from build_pdf import check_csv_dependencies, pdf_is_locked, pdf_write_error_hint, run_pdflatex
from config import ROOT, SECTION_GENERATION_ORDER, TEX_PATH
from generate_figures import main as generate_figures_main
from inject_offerta_table import main as inject_offerta_table_main
from test_google_ai import GEMINI_MODEL, generate_section

logger = logging.getLogger(__name__)

PDF_PATH = ROOT / "main.pdf"
LOG_PATH = ROOT / "main.log"
AUX_PATH = ROOT / "main.aux"
DEFAULT_ARTIFACT_DIR = ROOT / "output" / "artifacts"

RE_LABEL = re.compile(r"\\label\{([^}]+)\}")
RE_REF = re.compile(r"\\(?:auto)?ref\{([^}]+)\}")
RE_UNDEFINED_REF = re.compile(
    r"LaTeX Warning: Reference `([^']+)' on page .* undefined",
    re.MULTILINE,
)
RE_PDF_BROKEN_REF = re.compile(
    r"(?:Figura|Tabella|Figure|Table)\s*\?\?",
    re.IGNORECASE,
)


@dataclass
class RefCheckResult:
    ok: bool
    missing_labels: list[str] = field(default_factory=list)
    undefined_in_log: list[str] = field(default_factory=list)
    broken_in_pdf: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class PipelineResult:
    ok: bool
    tex_path: Path
    pdf_path: Path
    zip_path: Path | None
    steps: list[str] = field(default_factory=list)
    ref_check: RefCheckResult | None = None
    error: str | None = None


def run_data_fetch() -> None:
    """Run data_fetch.py as a subprocess (module executes on import)."""
    script = ROOT / "data_fetch.py"
    logger.info("Step 1/5 — download CSV from Metabase")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        logger.info(result.stdout.rstrip())
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"data_fetch.py fallito (exit {result.returncode}): {detail}")


def run_figures() -> None:
    logger.info("Step 2/5 — regenerate PGFPlots figures + tables in main.tex")
    generate_figures_main()
    inject_offerta_table_main()


def run_text_generation(
    *,
    model: str = GEMINI_MODEL,
    sections: tuple[str, ...] | list[str] = SECTION_GENERATION_ORDER,
    inject_only: bool = False,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    pause_seconds: float = GEMINI_MIN_PAUSE_SECONDS,
    rate_limit: int = GEMINI_MAX_CALLS_PER_MINUTE,
) -> None:
    """Generate section prose (two-column wrapper applied in postprocess_prose)."""
    logger.info("Step 3/5 — generate prose (2-column text; figures stay full-width)")
    rate_limiter: MinuteRateLimiter | None = None
    if not inject_only:
        rate_limiter = MinuteRateLimiter(
            max_calls=rate_limit,
            window_seconds=max(pause_seconds, GEMINI_RATE_WINDOW_SECONDS),
        )
    for key in sections:
        logger.info("  generating section: %s", key)
        generate_section(
            key,
            model=model,
            output=None,
            dry_run=False,
            inject_only=inject_only,
            prose_source=None,
            rate_limiter=rate_limiter,
            max_attempts=max_attempts,
            pause_seconds=pause_seconds,
        )


def run_build_pdf(*, passes: int = 2) -> Path:
    logger.info("Step 4/5 — compile main.tex → main.pdf (%d passes)", passes)
    check_csv_dependencies(TEX_PATH)
    if pdf_is_locked(PDF_PATH):
        raise RuntimeError(pdf_write_error_hint(PDF_PATH))
    run_pdflatex(TEX_PATH, passes)
    if not PDF_PATH.is_file():
        raise RuntimeError(f"PDF non creato: {PDF_PATH}")
    return PDF_PATH


def check_references(tex_path: Path = TEX_PATH, pdf_path: Path = PDF_PATH) -> RefCheckResult:
    """Verify every \\ref has a \\label and that the PDF has no 'Figura ??' leftovers."""
    logger.info("Step 5/5 — validate \\ref / \\label")
    tex = tex_path.read_text(encoding="utf-8")
    labels = set(RE_LABEL.findall(tex))
    refs = set(RE_REF.findall(tex))
    missing = sorted(refs - labels)

    undefined_log: list[str] = []
    log_path = tex_path.with_suffix(".log")
    if log_path.is_file():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        undefined_log = sorted(set(RE_UNDEFINED_REF.findall(log_text)))

    broken_pdf: list[str] = []
    if pdf_path.is_file():
        try:
            import fitz  # pymupdf

            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                for match in RE_PDF_BROKEN_REF.finditer(text):
                    snippet = text[max(0, match.start() - 20) : match.end() + 20]
                    broken_pdf.append(f"p.{i}: {snippet!r}")
        except ImportError:
            # Fallback: binary search for the literal "??" near figure captions is weak;
            # rely on .log undefined warnings instead.
            logger.warning("pymupdf non disponibile: controllo PDF limitato al log LaTeX")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lettura PDF per check ref fallita: %s", exc)

    ok = not missing and not undefined_log and not broken_pdf
    parts: list[str] = []
    if missing:
        parts.append(f"\\ref senza \\label: {', '.join(missing)}")
    if undefined_log:
        parts.append(f"undefined nel log: {', '.join(undefined_log)}")
    if broken_pdf:
        parts.append(f"?? nel PDF: {'; '.join(broken_pdf[:5])}")
    message = "Riferimenti OK" if ok else "; ".join(parts)
    return RefCheckResult(
        ok=ok,
        missing_labels=missing,
        undefined_in_log=undefined_log,
        broken_in_pdf=broken_pdf,
        message=message,
    )


def package_artifacts(
    tex_path: Path,
    pdf_path: Path,
    *,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = artifact_dir / f"rapporto_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(tex_path, arcname=tex_path.name)
        zf.write(pdf_path, arcname=pdf_path.name)
    logger.info("Artifact ZIP: %s", zip_path)
    return zip_path


def run_pipeline(
    *,
    skip_fetch: bool = False,
    skip_figures: bool = False,
    skip_text: bool = False,
    inject_only: bool = False,
    skip_build: bool = False,
    model: str = GEMINI_MODEL,
    sections: tuple[str, ...] | list[str] | None = None,
    passes: int = 2,
    fail_on_bad_refs: bool = True,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> PipelineResult:
    """Run the full report pipeline and return paths + ref-check status."""
    steps: list[str] = []
    section_keys = tuple(sections) if sections else SECTION_GENERATION_ORDER

    try:
        if not skip_fetch:
            run_data_fetch()
            steps.append("fetch")
        else:
            steps.append("fetch:skipped")

        if not skip_figures:
            run_figures()
            steps.append("figures")
        else:
            steps.append("figures:skipped")

        if not skip_text:
            run_text_generation(
                model=model,
                sections=section_keys,
                inject_only=inject_only,
            )
            steps.append("text" if not inject_only else "text:inject_only")
        else:
            steps.append("text:skipped")

        if not skip_build:
            run_build_pdf(passes=passes)
            steps.append("build")
        else:
            steps.append("build:skipped")

        ref_check = check_references(TEX_PATH, PDF_PATH)
        steps.append("ref_check")

        if fail_on_bad_refs and not ref_check.ok:
            return PipelineResult(
                ok=False,
                tex_path=TEX_PATH,
                pdf_path=PDF_PATH,
                zip_path=None,
                steps=steps,
                ref_check=ref_check,
                error=f"Riferimenti non validi: {ref_check.message}",
            )

        zip_path = None
        if PDF_PATH.is_file() and TEX_PATH.is_file():
            zip_path = package_artifacts(TEX_PATH, PDF_PATH, artifact_dir=artifact_dir)
            steps.append("package")

        return PipelineResult(
            ok=True,
            tex_path=TEX_PATH,
            pdf_path=PDF_PATH,
            zip_path=zip_path,
            steps=steps,
            ref_check=ref_check,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline fallita")
        return PipelineResult(
            ok=False,
            tex_path=TEX_PATH,
            pdf_path=PDF_PATH,
            zip_path=None,
            steps=steps,
            error=str(exc),
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    parser = argparse.ArgumentParser(description="Pipeline completa rapporto → ZIP (tex+pdf)")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-figures", action="store_true")
    parser.add_argument("--skip-text", action="store_true")
    parser.add_argument(
        "--inject-only",
        action="store_true",
        help="Inietta prosa dai backup locali senza chiamare Gemini",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--model", default=GEMINI_MODEL)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument(
        "--allow-bad-refs",
        action="store_true",
        help="Non fallire se ci sono riferimenti ?? / undefined",
    )
    args = parser.parse_args()

    result = run_pipeline(
        skip_fetch=args.skip_fetch,
        skip_figures=args.skip_figures,
        skip_text=args.skip_text,
        inject_only=args.inject_only,
        skip_build=args.skip_build,
        model=args.model,
        passes=args.passes,
        fail_on_bad_refs=not args.allow_bad_refs,
    )
    if result.ref_check:
        print(f"Ref check: {result.ref_check.message}")
    if result.ok:
        print(f"OK — steps: {', '.join(result.steps)}")
        if result.zip_path:
            print(f"ZIP: {result.zip_path}")
        print(f"TEX: {result.tex_path}")
        print(f"PDF: {result.pdf_path}")
        return 0
    print(f"ERRORE: {result.error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
