#!/usr/bin/env python3
"""Generate prose for report sections via Ollama/Gemma and inject into main.tex."""

import argparse
import re
import sys
from pathlib import Path

import requests

from config import (
    CHAPTER_SECTION_KEYS,
    GLOSSARY_CONTEXT_KEYS,
    OLLAMA_MODEL,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TAGS_URL,
    OLLAMA_TEMPERATURE,
    OLLAMA_URL,
    OUTPUT_DIR,
    PROMPT_PATH,
    SECTION_GENERATION_ORDER,
    SECTIONS,
    SectionConfig,
    TEX_PATH,
)
from figure_style import escape_prose_for_latex


def load_prompt(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_section_prompt(section: SectionConfig) -> str:
    return load_prompt(section.prompt_path or PROMPT_PATH)


def load_csv_bundle(paths: list[Path] | tuple[Path, ...]) -> str:
    if not paths:
        return ""
    blocks = []
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f"CSV not found: {p}. Run data_fetch.py first.")
        blocks.append(f"--- FILE: {p.name} ---\n{p.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(blocks)


def extract_section_prose(tex: str, section: SectionConfig) -> str:
    pattern = re.compile(
        re.escape(section.marker_start) + r"\s*(.*?)\s*" + re.escape(section.marker_end),
        re.DOTALL,
    )
    match = pattern.search(tex)
    if not match:
        return ""
    return match.group(1).strip()


def prose_is_populated(section: SectionConfig, prose: str) -> bool:
    text = prose.strip()
    if not text:
        return False
    remainder = re.sub(re.escape(section.section_latex), "", text, count=1).strip()
    return len(remainder) >= 80


def resolve_section_prose(section: SectionConfig, tex: str) -> str:
    prose = extract_section_prose(tex, section)
    if prose_is_populated(section, prose):
        return prose
    if section.backup_path.is_file():
        backup = section.backup_path.read_text(encoding="utf-8").strip()
        if prose_is_populated(section, backup):
            return backup
    return prose


def load_sections_latex(
    section_keys: tuple[str, ...],
    tex: str | None = None,
    *,
    error_label: str,
) -> str:
    tex_content = tex if tex is not None else ensure_tex_exists()
    blocks: list[str] = []
    missing: list[str] = []
    for key in section_keys:
        section = SECTIONS[key]
        prose = resolve_section_prose(section, tex_content)
        if not prose_is_populated(section, prose):
            missing.append(section.title)
            continue
        blocks.append(f"--- CAPITOLO: {section.title} ---\n\n{prose}")
    if missing:
        raise RuntimeError(
            f"Impossibile generare {error_label}: sezioni non ancora redatte o vuote: "
            + ", ".join(missing)
            + ". Genera prima i capitoli richiesti."
        )
    return "\n\n".join(blocks)


def load_chapters_latex(tex: str | None = None) -> str:
    return load_sections_latex(
        CHAPTER_SECTION_KEYS,
        tex,
        error_label="le conclusioni",
    )


def load_glossary_context_latex(tex: str | None = None) -> str:
    return load_sections_latex(
        GLOSSARY_CONTEXT_KEYS,
        tex,
        error_label="il glossario",
    )


def build_user_message(
    section: SectionConfig,
    csv_text: str,
    *,
    chapters_latex: str = "",
) -> str:
    if section.key == "introduzione":
        return f"""Genera esclusivamente il testo dell'introduzione del report.

Output richiesto (intestazione obbligatoria):
{section.section_latex}

Segui rigorosamente la struttura logica a quattro blocchi e le regole di formato LaTeX definite nel prompt di sistema.
Non includere spiegazioni, note personali o codice al di fuori del corpo del rapporto.
Non includere codice figure o tabelle (\\begin{{figure}}, \\begin{{table}}).
"""

    if section.key == "conclusione":
        return f"""Genera esclusivamente il testo della sezione conclusiva del report.

Output richiesto (intestazione obbligatoria):
{section.section_latex}

Sintetizza esclusivamente i contenuti dei capitoli già redatti riportati di seguito.
Segui rigorosamente la struttura conclusiva e i vincoli metodologici definiti nel prompt di sistema.
Non includere spiegazioni, note personali o codice al di fuori del corpo del rapporto.
Non includere codice figure o tabelle (\\begin{{figure}}, \\begin{{table}}).

Capitoli del report (LaTeX):

{chapters_latex}
"""

    if section.key == "glossario":
        return f"""Genera esclusivamente il capitolo glossario del report.

Output richiesto (intestazione obbligatoria):
{section.section_latex}

Organizza le voci con \\subsection{{...}} per ogni categoria indicata nel prompt di sistema.
Non usare markdown (# o ##): restituisci solo LaTeX pronto per l'inserimento.
Segui rigorosamente elenco termini, formato voci e requisiti stilistici del prompt di sistema.
Non includere codice figure o tabelle (\\begin{{figure}}, \\begin{{table}}).

Testo del report già redatto (LaTeX, per contesto e definizioni coerenti):

{chapters_latex}
"""

    figures_block = ""
    if section.csv_paths:
        # Convention: figure/table labels match the CSV basename
        # (fig:<stem> for figures, tab:<stem> for tables).
        table_stems = {"offerta_tabellina", "praticato_146"}
        lines: list[str] = []
        for path in section.csv_paths:
            stem = path.stem
            kind = "tab" if stem in table_stems else "fig"
            lines.append(f"- {path.name} → {kind}:{stem}  (usa Figura~\\ref{{{kind}:{stem}}} oppure Tabella~\\ref{{{kind}:{stem}}})")
        figures_block = f"""
File CSV di questa sezione e relative etichette LaTeX (obbligatorie nei \\ref{{}}):
{chr(10).join(lines)}
"""

    csv_block = ""
    if csv_text.strip():
        csv_block = f"""
Dati forniti:

{csv_text}
"""

    return f"""Redigi esclusivamente la sezione del rapporto:
{section.section_latex}
{figures_block}- Usa il termine "{section.term}" in modo coerente.
- Il testo del capitolo va in due colonne (il wrapper LaTeX viene applicato automaticamente); non inserire \\begin{{multicols}}.
- Non includere codice figure o tabelle (\\begin{{figure}}, \\begin{{table}}); i grafici sono già nel documento a tutta larghezza.
{csv_block}
"""


def prepare_generation(section: SectionConfig, *, tex: str | None = None) -> tuple[str, str]:
    system_prompt = load_section_prompt(section)
    csv_text = load_csv_bundle(section.csv_paths)
    if section.key == "conclusione":
        chapters_latex = load_chapters_latex(tex)
    elif section.key == "glossario":
        chapters_latex = load_glossary_context_latex(tex)
    else:
        chapters_latex = ""
    user_message = build_user_message(section, csv_text, chapters_latex=chapters_latex)
    return system_prompt, user_message


def build_messages(system_prompt: str, user_message: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


def check_ollama(model: str) -> None:
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=10)
        r.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "Ollama non raggiungibile. Avvia Ollama e verifica che il servizio sia attivo "
            f"({OLLAMA_TAGS_URL})."
        ) from exc

    models = [m.get("name", "") for m in r.json().get("models", [])]
    if not any(model in name or name.startswith(model) for name in models):
        available = ", ".join(models) if models else "(nessun modello)"
        print(
            f"Attenzione: modello '{model}' non trovato tra i modelli locali: {available}",
            file=sys.stderr,
        )
        print(f"Esegui: ollama pull {model}", file=sys.stderr)


def call_ollama(model: str, messages: list[dict]) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": OLLAMA_TEMPERATURE,
                "num_predict": OLLAMA_NUM_PREDICT,
            },
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def wrap_prose_twocolumn(prose: str) -> str:
    """Titolo di sezione a tutta pagina; corpo del testo su due colonne."""
    text = prose.strip()
    if not text or r"\begin{multicols}" in text:
        return text

    match = re.match(r"(\\section\{[^}]+\}\s*\n)([\s\S]*)", text)
    if match:
        header, body = match.group(1), match.group(2).strip()
        if not body:
            return header.rstrip()
        return f"{header}\\begin{{multicols}}{{2}}\n{body}\n\\end{{multicols}}"

    return f"\\begin{{multicols}}{{2}}\n{text}\n\\end{{multicols}}"


def postprocess_prose(raw: str, section: SectionConfig) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:latex)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    if not text.startswith(r"\section{"):
        text = f"{section.section_latex}\n\n{text}"

    if section.marker_start in text or section.marker_end in text:
        raise ValueError("La risposta del modello contiene marker di iniezione; rigenerare.")

    return wrap_prose_twocolumn(escape_prose_for_latex(text))


def inject_prose(text: str, section: SectionConfig, prose: str) -> str:
    block = f"{section.marker_start}\n{prose.strip()}\n{section.marker_end}\n\n"
    marker_pattern = re.compile(
        re.escape(section.marker_start) + r".*?" + re.escape(section.marker_end) + r"\s*",
        re.DOTALL,
    )

    if section.marker_start in text:
        _repl = lambda _: block
        updated, count = marker_pattern.subn(_repl, text, count=1)
        if count > 0:
            return updated

        fallback = re.compile(
            re.escape(section.marker_start) + r"\s*(?:.*?\n)*?" + section.fallback_before,
            re.DOTALL,
        )
        updated, count = fallback.subn(_repl, text, count=1)
        if count > 0:
            return updated

        begin_line = re.compile(re.escape(section.marker_start) + r"\s*\n")
        updated, count = begin_line.subn(_repl, text, count=1)
        if count > 0:
            return updated

        raise ValueError(
            f"Marker {section.marker_start!r} presente in {TEX_PATH.name} "
            "ma iniezione non riuscita. Verifica la struttura del file."
        )

    section_pattern = rf"(\\section\{{{re.escape(section.title)}\}})"
    if not re.search(section_pattern, text):
        raise ValueError(
            f"Sezione non trovata in {TEX_PATH.name}: \\section{{{section.title}}}."
        )

    return re.sub(
        section_pattern + r"\s*",
        lambda m: m.group(1) + "\n\n" + block,
        text,
        count=1,
    )


def ensure_tex_exists() -> str:
    if not TEX_PATH.is_file():
        raise FileNotFoundError(f"{TEX_PATH.name} non trovato.")
    return TEX_PATH.read_text(encoding="utf-8")


def save_backup(prose: str, section: SectionConfig) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    section.backup_path.write_text(prose, encoding="utf-8")


def verify_injection(updated: str, section: SectionConfig, prose: str) -> None:
    if section.marker_end not in updated or prose.strip() not in updated:
        raise RuntimeError(
            f"Iniezione in {TEX_PATH.name} fallita per '{section.key}'. "
            f"Verifica i marker {section.marker_start!r} / {section.marker_end!r}."
        )


def generate_section(section: SectionConfig, model: str, *, dry_run: bool = False) -> int:
    system_prompt, user_message = prepare_generation(section)
    messages = build_messages(system_prompt, user_message)

    if dry_run:
        prompt_path = section.prompt_path or PROMPT_PATH
        print(f"=== SEZIONE: {section.key} ===")
        print(f"=== PROMPT: {prompt_path.name} ===")
        preview = system_prompt[:500] + ("..." if len(system_prompt) > 500 else "")
        print(preview)
        print("\n=== USER ===")
        print(user_message)
        return 0

    tex = ensure_tex_exists()
    check_ollama(model)

    print(f"Chiamata Ollama ({model}) per '{section.key}'...")
    raw = call_ollama(model, messages)
    prose = postprocess_prose(raw, section)

    save_backup(prose, section)
    print(f"Backup salvato: {section.backup_path}")

    updated = inject_prose(tex, section, prose)
    verify_injection(updated, section, prose)
    TEX_PATH.write_text(updated, encoding="utf-8")
    print(f"Prosa '{section.key}' iniettata in {TEX_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera testo sezioni rapporto con Gemma/Ollama e inietta in main.tex"
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
        help="Mostra il prompt utente senza chiamare Ollama né modificare main.tex",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Modello Ollama (default: {OLLAMA_MODEL})",
    )
    args = parser.parse_args()

    keys = SECTION_GENERATION_ORDER if args.section == "all" else [args.section]
    for key in keys:
        rc = generate_section(SECTIONS[key], args.model, dry_run=args.dry_run)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, requests.RequestException) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
