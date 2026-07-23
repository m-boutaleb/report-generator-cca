import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SECRETS_PATH = ROOT / "secrets.json"
SECRETS_EXAMPLE_PATH = ROOT / "secrets.example.json"


@lru_cache(maxsize=1)
def load_secrets() -> dict[str, str]:
    """Load local credentials from secrets.json (if present)."""
    if not SECRETS_PATH.is_file():
        return {}
    try:
        data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Impossibile leggere {SECRETS_PATH.name}: {exc}. "
            f"Copia {SECRETS_EXAMPLE_PATH.name} in {SECRETS_PATH.name} e compilalo."
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{SECRETS_PATH.name} deve contenere un oggetto JSON.")
    return {str(k): "" if v is None else str(v) for k, v in data.items()}


def get_secret(name: str, default: str = "") -> str:
    """Resolve a setting: environment variable first, then secrets.json, then default."""
    env_val = os.environ.get(name)
    if env_val is not None and str(env_val).strip() != "":
        return str(env_val)
    file_val = load_secrets().get(name, "")
    if file_val is not None and str(file_val).strip() != "":
        return str(file_val)
    return default


def require_secret(name: str, *, hint: str = "") -> str:
    value = get_secret(name)
    if value:
        return value
    tip = hint or (
        f"Imposta `{name}` in {SECRETS_PATH.name} "
        f"(parti da {SECRETS_EXAMPLE_PATH.name}) oppure come variabile d'ambiente."
    )
    raise RuntimeError(f"Chiave mancante: {name}. {tip}")


OLLAMA_BASE_URL = get_secret("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_MODEL = get_secret("OLLAMA_MODEL", "gemma4")
OLLAMA_TEMPERATURE = float(get_secret("OLLAMA_TEMPERATURE", "0.3"))
OLLAMA_NUM_PREDICT = int(get_secret("OLLAMA_NUM_PREDICT", "2048"))

GEMINI_API_KEY = get_secret("GEMINI_API_KEY") or get_secret("GOOGLE_API_KEY")
METABASE_API_KEY = get_secret("METABASE_API_KEY")

GEMINI_MODEL = get_secret("GEMINI_MODEL", "gemma-4-31b-it")

PROMPT_PATH = ROOT / "prompts" / "prompt_EA.md"
FONTE_RS_PATH = ROOT / "prompts" / "fonte_rs.md"
FONTE_IFD_PATH = ROOT / "prompts" / "fonte_ifd.md"
INTRODUZIONE_PROMPT_PATH = ROOT / "prompts" / "prompt_introduzione_v1.md"
CONCLUSIONE_PROMPT_PATH = ROOT / "prompts" / "prompt_conclusione_v3.md"
GLOSSARIO_PROMPT_PATH = ROOT / "prompts" / "glossario.md"
TEX_PATH = ROOT / "main.tex"
OUTPUT_DIR = ROOT / "output"


@dataclass(frozen=True)
class SectionConfig:
    key: str
    title: str
    csv_paths: tuple[Path, ...]
    marker_start: str
    marker_end: str
    figure_captions: tuple[str, ...]
    term: str
    backup_path: Path
    fallback_before: str
    prompt_path: Path | None = None

    @property
    def section_latex(self) -> str:
        return rf"\section{{{self.title}}}"

    @property
    def uses_csv(self) -> bool:
        return bool(self.csv_paths)


SECTIONS: dict[str, SectionConfig] = {
    "introduzione": SectionConfig(
        key="introduzione",
        title="Introduzione",
        csv_paths=(),
        marker_start="% BEGIN: introduzione_prosa (auto-generated)",
        marker_end="% END: introduzione_prosa (auto-generated)",
        figure_captions=(),
        term="scompenso di pigione sostenibile",
        backup_path=OUTPUT_DIR / "introduzione_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: offerta_prosa|\n\\begin\{figure)",
        prompt_path=INTRODUZIONE_PROMPT_PATH,
    ),
    "offerta": SectionConfig(
        key="offerta",
        title="Mercato locativo offerto",
        csv_paths=(
            ROOT / "data" / "offerta_line.csv",
            ROOT / "data" / "offerta_tabellina.csv",
        ),
        marker_start="% BEGIN: offerta_prosa (auto-generated)",
        marker_end="% END: offerta_prosa (auto-generated)",
        figure_captions=(
            "Evoluzione del canone mediano offerto (Cantonale vs Regionale)",
            "Indicatori medi del mercato locativo offerto a livello cantonale",
        ),
        term="mercato locativo offerto",
        backup_path=OUTPUT_DIR / "offerta_prosa_last.tex",
        fallback_before=r"(?=\n\\begin\{figure|\n% BEGIN: offerta_tabellina)",
    ),
    "praticato": SectionConfig(
        key="praticato",
        title="Mercato locativo praticato",
        csv_paths=(
            ROOT / "data" / "praticato_139.csv",
            ROOT / "data" / "praticato_60.csv",
            ROOT / "data" / "praticato_62.csv",
            ROOT / "data" / "praticato_146.csv",
        ),
        marker_start="% BEGIN: praticato_prosa (auto-generated)",
        marker_end="% END: praticato_prosa (auto-generated)",
        figure_captions=(
            "Canone locativo mediano per tipologia di economia domestica e regione",
            "Distribuzione delle categorie di edificio per regione (quota % e valori assoluti)",
            "Distribuzione del parco immobiliare per epoca di costruzione e regione",
            "Indicatori medi del mercato locativo praticato a livello cantonale",
        ),
        term="mercato locativo praticato",
        backup_path=OUTPUT_DIR / "praticato_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: praticato_figure|\n\\begin\{figure)",
    ),
    "reddito": SectionConfig(
        key="reddito",
        title="Reddito",
        csv_paths=(
            ROOT / "data" / "reddito_line.csv",
            ROOT / "data" / "reddito_75.csv",
        ),
        marker_start="% BEGIN: reddito_prosa (auto-generated)",
        marker_end="% END: reddito_prosa (auto-generated)",
        figure_captions=(
            "Evoluzione reddito medio equivalente",
            "Distribuzione fasce di reddito (percentuale e valori assoluti)",
        ),
        term="reddito",
        backup_path=OUTPUT_DIR / "reddito_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: reddito_figure|\n\\begin\{figure)",
    ),
    "tasso_sforzo": SectionConfig(
        key="tasso_sforzo",
        title="Tasso di sforzo",
        csv_paths=(ROOT / "data" / "tasso_di_sforzo_121.csv",),
        marker_start="% BEGIN: tasso_sforzo_prosa (auto-generated)",
        marker_end="% END: tasso_sforzo_prosa (auto-generated)",
        figure_captions=(
            "Tasso di sforzo per regione (mercato praticato e offerto)",
        ),
        term="tasso di sforzo",
        backup_path=OUTPUT_DIR / "tasso_sforzo_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: tasso_sforzo_figure|\n\\begin\{figure)",
    ),
    "sostenibile": SectionConfig(
        key="sostenibile",
        title="Offerta a pigione sostenibile",
        csv_paths=(
            ROOT / "data" / "sostenibile_104.csv",
            ROOT / "data" / "sostenibile_118.csv",
            ROOT / "data" / "sostenibile_143.csv",
            ROOT / "data" / "sostenibile_102.csv",
        ),
        marker_start="% BEGIN: sostenibile_prosa (auto-generated)",
        marker_end="% END: sostenibile_prosa (auto-generated)",
        figure_captions=(
            "Distribuzione dell'offerta per numero di locali",
            "Principali comuni per inserzioni a pigione sostenibile",
            "Distribuzione delle inserzioni per regione (quota % e valori assoluti)",
            "Distribuzione delle inserzioni per durata d'inserzione",
        ),
        term="offerta a pigione sostenibile",
        backup_path=OUTPUT_DIR / "sostenibile_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: sostenibile_figure|\n\\begin\{figure)",
    ),
    "scompenso": SectionConfig(
        key="scompenso",
        title="Scompenso di pigione sostenibile",
        csv_paths=(
            ROOT / "data" / "scompenso_87.csv",
            ROOT / "data" / "scompenso_136.csv",
        ),
        marker_start="% BEGIN: scompenso_prosa (auto-generated)",
        marker_end="% END: scompenso_prosa (auto-generated)",
        figure_captions=(
            "Evoluzione dello scompenso (scenari AB e CD)",
            "Scompenso incrociato per regione e metratura",
        ),
        term="scompenso di pigione sostenibile",
        backup_path=OUTPUT_DIR / "scompenso_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: scompenso_figure|\n\\begin\{table|\n\\begin\{figure)",
    ),
    "conclusione": SectionConfig(
        key="conclusione",
        title="Conclusioni",
        csv_paths=(),
        marker_start="% BEGIN: conclusione_prosa (auto-generated)",
        marker_end="% END: conclusione_prosa (auto-generated)",
        figure_captions=(),
        term="scompenso di pigione sostenibile",
        backup_path=OUTPUT_DIR / "conclusione_prosa_last.tex",
        fallback_before=r"(?=\n% BEGIN: glossario_prosa|\n\\end\{document\})",
        prompt_path=CONCLUSIONE_PROMPT_PATH,
    ),
    "glossario": SectionConfig(
        key="glossario",
        title="Glossario",
        csv_paths=(),
        marker_start="% BEGIN: glossario_prosa (auto-generated)",
        marker_end="% END: glossario_prosa (auto-generated)",
        figure_captions=(),
        term="scompenso di pigione sostenibile",
        backup_path=OUTPUT_DIR / "glossario_prosa_last.tex",
        fallback_before=r"(?=\n\\end\{document\})",
        prompt_path=GLOSSARIO_PROMPT_PATH,
    ),
}

CHAPTER_SECTION_KEYS: tuple[str, ...] = (
    "introduzione",
    "offerta",
    "praticato",
    "reddito",
    "tasso_sforzo",
    "sostenibile",
    "scompenso",
)

GLOSSARY_CONTEXT_KEYS: tuple[str, ...] = (*CHAPTER_SECTION_KEYS, "conclusione")

SECTION_GENERATION_ORDER: tuple[str, ...] = (*GLOSSARY_CONTEXT_KEYS, "glossario")

# Alias retrocompatibilità (offerta)
_offerta = SECTIONS["offerta"]
CSV_PATHS = list(_offerta.csv_paths)
SECTION_TITLE = _offerta.title
SECTION_LATEX = _offerta.section_latex
MARKER_START = _offerta.marker_start
MARKER_END = _offerta.marker_end
FIGURE_CAPTION = _offerta.figure_captions[0]
PROSA_BACKUP_PATH = _offerta.backup_path
