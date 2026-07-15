#!/usr/bin/env python3
"""Genera testo sezioni rapporto con Gemma (Gemini API cloud) e inietta in main.tex."""

import argparse
import sys
from pathlib import Path

from google import genai
from google.genai import types

from api_retry import (
    GEMINI_MAX_CALLS_PER_MINUTE,
    GEMINI_MIN_PAUSE_SECONDS,
    GEMINI_RATE_WINDOW_SECONDS,
    RETRY_MAX_ATTEMPTS,
    MinuteRateLimiter,
    call_with_retry,
)
from config import (
    GEMINI_MODEL,
    OUTPUT_DIR,
    PROMPT_PATH,
    SECTION_GENERATION_ORDER,
    SECTIONS,
    TEX_PATH,
    get_secret,
)
from generate_offerta_text import (
    ensure_tex_exists,
    inject_prose,
    postprocess_prose,
    prepare_generation,
    save_backup,
    verify_injection,
)

OUTPUT_PATHS = {
    "introduzione": OUTPUT_DIR / "introduzione_prosa_gemma.tex",
    "offerta": OUTPUT_DIR / "offerta_prosa_gemma.tex",
    "praticato": OUTPUT_DIR / "praticato_prosa_gemma.tex",
    "reddito": OUTPUT_DIR / "reddito_prosa_gemma.tex",
    "tasso_sforzo": OUTPUT_DIR / "tasso_sforzo_prosa_gemma.tex",
    "sostenibile": OUTPUT_DIR / "sostenibile_prosa_gemma.tex",
    "scompenso": OUTPUT_DIR / "scompenso_prosa_gemma.tex",
    "conclusione": OUTPUT_DIR / "conclusione_prosa_gemma.tex",
    "glossario": OUTPUT_DIR / "glossario_prosa_gemma.tex",
}


def get_client() -> genai.Client:
    api_key = get_secret("GEMINI_API_KEY") or get_secret("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Imposta GEMINI_API_KEY (o GOOGLE_API_KEY) in secrets.json "
            "oppure come variabile d'ambiente."
        )
    return genai.Client(api_key=api_key)


def extract_response_text(response) -> str:
    text = response.text
    if text and text.strip():
        return text.strip()

    parts: list[str] = []
    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in content.parts or []:
            if getattr(part, "thought", False):
                continue
            part_text = getattr(part, "text", None)
            if part_text:
                parts.append(part_text)
    return "\n".join(parts).strip()


def call_gemini(
    client: genai.Client,
    system_prompt: str,
    user_message: str,
    model: str = GEMINI_MODEL,
    *,
    rate_limiter: MinuteRateLimiter | None = None,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    pause_seconds: float = GEMINI_MIN_PAUSE_SECONDS,
) -> str:
    def _request() -> str:
        if rate_limiter is not None:
            rate_limiter.acquire()
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        text = extract_response_text(response)
        if not text:
            raise RuntimeError("Risposta vuota da Gemini/Gemma.")
        return text

    return call_with_retry(
        _request,
        label=f"Gemma/{model}",
        max_attempts=max_attempts,
        fixed_delay=pause_seconds,
    )


def resolve_prose_source(section_key: str, source: Path | None) -> Path:
    if source is not None:
        if not source.is_file():
            raise FileNotFoundError(f"File prosa non trovato: {source}")
        return source

    section = SECTIONS[section_key]
    legacy_gemini = OUTPUT_DIR / f"{section_key}_prosa_gemini.tex"
    for path in (OUTPUT_PATHS[section_key], legacy_gemini, section.backup_path):
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Nessun backup prosa per '{section_key}'. "
        f"Genera prima con Gemma oppure passa --from path/to/prosa.tex"
    )


def apply_prose(
    section_key: str,
    raw: str,
    *,
    output: Path | None,
) -> None:
    section = SECTIONS[section_key]
    prose = postprocess_prose(raw, section)

    tex = ensure_tex_exists()
    updated = inject_prose(tex, section, prose)
    verify_injection(updated, section, prose)
    TEX_PATH.write_text(updated, encoding="utf-8")

    save_backup(prose, section)
    backup_path = output or OUTPUT_PATHS[section_key]
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(prose, encoding="utf-8")

    print(f"Prosa '{section_key}' iniettata in: {TEX_PATH}")
    print(f"Backup salvato in: {backup_path}")
    print("\n--- ANTEPRIMA ---\n")
    print(prose[:1500] + ("..." if len(prose) > 1500 else ""))


def generate_section(
    section_key: str,
    *,
    model: str,
    output: Path | None,
    dry_run: bool,
    inject_only: bool,
    prose_source: Path | None,
    rate_limiter: MinuteRateLimiter | None,
    max_attempts: int,
    pause_seconds: float,
) -> None:
    section = SECTIONS[section_key]
    system_prompt, user_message = prepare_generation(section)
    prompt_path = section.prompt_path or PROMPT_PATH

    if dry_run:
        print(f"=== SEZIONE: {section_key} ===")
        print(f"=== MODELLO: {model} (Gemini API cloud) ===")
        print(f"=== PROMPT: {prompt_path.name} ===")
        preview = system_prompt[:600] + ("..." if len(system_prompt) > 600 else "")
        print(preview)
        print("\n=== RICHIESTA SEZIONE ===")
        print(user_message[:4000] + ("..." if len(user_message) > 4000 else ""))
        return

    if inject_only:
        source = resolve_prose_source(section_key, prose_source)
        print(f"Iniezione locale per '{section_key}' da: {source}")
        raw = source.read_text(encoding="utf-8")
        apply_prose(section_key, raw, output=output)
        return

    print(f"Chiamata Gemma ({model}) per '{section_key}'...")
    client = get_client()
    raw = call_gemini(
        client,
        system_prompt,
        user_message,
        model=model,
        rate_limiter=rate_limiter,
        max_attempts=max_attempts,
        pause_seconds=pause_seconds,
    )
    apply_prose(section_key, raw, output=output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera testo sezioni rapporto con Gemma (Gemini API) + prompt_EA + CSV"
    )
    parser.add_argument(
        "--section",
        choices=[*SECTIONS.keys(), "all"],
        default="offerta",
        help="Sezione da generare (default: offerta)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra prompt senza chiamare l'API",
    )
    parser.add_argument(
        "--inject-only",
        action="store_true",
        help="Salta l'API: inietta in main.tex da un backup esistente",
    )
    parser.add_argument(
        "--from",
        dest="prose_source",
        type=Path,
        default=None,
        help="File prosa da usare con --inject-only",
    )
    parser.add_argument(
        "--model",
        default=GEMINI_MODEL,
        help=f"Modello Gemini API (default: {GEMINI_MODEL})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="File di backup aggiuntivo (solo con una singola sezione)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=RETRY_MAX_ATTEMPTS,
        help=f"Tentativi massimi per chiamata API (default: {RETRY_MAX_ATTEMPTS})",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=GEMINI_MIN_PAUSE_SECONDS,
        help=(
            f"Pausa fissa in secondi tra chiamate (rate limit) e su retry 503/429 "
            f"(default: {GEMINI_MIN_PAUSE_SECONDS})"
        ),
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=GEMINI_MAX_CALLS_PER_MINUTE,
        help=f"Chiamate API Gemini max per minuto (default: {GEMINI_MAX_CALLS_PER_MINUTE})",
    )
    parser.add_argument(
        "--rate-window",
        type=float,
        default=GEMINI_RATE_WINDOW_SECONDS,
        help=f"Pausa al raggiungimento del limite chiamate (default: {GEMINI_RATE_WINDOW_SECONDS})",
    )
    args = parser.parse_args()

    if args.output and args.section == "all":
        raise RuntimeError("--output non è supportato con --section all")
    if args.dry_run and args.inject_only:
        raise RuntimeError("--dry-run e --inject-only sono mutuamente esclusivi")
    if args.max_retries < 1:
        raise RuntimeError("--max-retries deve essere >= 1")
    if args.rate_limit < 1:
        raise RuntimeError("--rate-limit deve essere >= 1")
    if args.rate_window <= 0:
        raise RuntimeError("--rate-window deve essere > 0")
    if args.pause <= 0:
        raise RuntimeError("--pause deve essere > 0")

    pause_seconds = max(args.pause, args.rate_window)

    rate_limiter: MinuteRateLimiter | None = None
    if not args.dry_run and not args.inject_only:
        rate_limiter = MinuteRateLimiter(
            max_calls=args.rate_limit,
            window_seconds=pause_seconds,
        )
        print(
            f"Gemini: max {args.rate_limit} chiamate/min, "
            f"pausa fissa {pause_seconds:.0f}s (rate limit e retry).",
            file=sys.stderr,
        )

    keys = SECTION_GENERATION_ORDER if args.section == "all" else [args.section]
    for key in keys:
        generate_section(
            key,
            model=args.model,
            output=args.output,
            dry_run=args.dry_run,
            inject_only=args.inject_only,
            prose_source=args.prose_source,
            rate_limiter=rate_limiter,
            max_attempts=args.max_retries,
            pause_seconds=pause_seconds,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
