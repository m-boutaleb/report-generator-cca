"""In-memory job registry and progress tracking for the report API."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from config import SECTIONS, SECTION_GENERATION_ORDER
from pipeline import DEFAULT_ARTIFACT_DIR, PipelineResult, run_pipeline
from test_google_ai import GEMINI_MODEL

_JOB_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class GenerateOptions(BaseModel):
    skip_fetch: bool = False
    skip_figures: bool = False
    skip_text: bool = False
    inject_only: bool = False
    skip_build: bool = False
    model: str = Field(default_factory=lambda: GEMINI_MODEL)
    sections: list[str] | None = None
    passes: int = Field(2, ge=1, le=5)
    fail_on_bad_refs: bool = True


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    steps: list[str] = []
    error: str | None = None
    ref_check: dict[str, Any] | None = None
    download_url: str | None = None
    tex_url: str | None = None
    pdf_url: str | None = None
    progress_pct: int = 0
    current_step: str | None = None
    current_label: str | None = None
    completed: list[str] = []
    sections_done: int = 0
    sections_total: int = 0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_lock_locked() -> bool:
    return _JOB_LOCK.locked()


def resolve_sections(sections: list[str] | None) -> tuple[str, ...]:
    if not sections:
        return SECTION_GENERATION_ORDER
    unknown = sorted(set(sections) - set(SECTION_GENERATION_ORDER))
    if unknown:
        raise ValueError(
            f"Sezioni sconosciute: {', '.join(unknown)}. "
            f"Consentite: {', '.join(SECTION_GENERATION_ORDER)}"
        )
    return tuple(k for k in SECTION_GENERATION_ORDER if k in sections)


def _section_label(key: str) -> str:
    return SECTIONS[key].title if key in SECTIONS else key.replace("_", " ").title()


def _build_progress_plan(options: GenerateOptions, section_keys: tuple[str, ...]) -> dict[str, float]:
    """Return step_id -> weight (sum ~= 100)."""
    weights: dict[str, float] = {}
    if not options.skip_fetch:
        weights["fetch"] = 10.0
    if not options.skip_figures:
        weights["figures"] = 15.0
    if not options.skip_text:
        share = 55.0 / max(len(section_keys), 1)
        for key in section_keys:
            weights[f"text:{key}"] = share
    if not options.skip_build:
        weights["build"] = 10.0
    weights["ref_check"] = 5.0
    weights["package"] = 5.0
    total = sum(weights.values()) or 100.0
    return {k: v * 100.0 / total for k, v in weights.items()}


def _new_job_dict(job_id: str, *, section_keys: tuple[str, ...], options: GenerateOptions) -> dict[str, Any]:
    return {
        "status": JobStatus.queued,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "steps": [],
        "error": None,
        "ref_check": None,
        "download_url": None,
        "tex_url": None,
        "pdf_url": None,
        "progress_pct": 0,
        "current_step": None,
        "current_label": None,
        "completed": [],
        "sections_done": 0,
        "sections_total": len(section_keys) if not options.skip_text else 0,
        "progress_plan": _build_progress_plan(options, section_keys),
        "options": options,
        "section_keys": section_keys,
    }


def _progress_label(step_id: str) -> str:
    if step_id == "fetch":
        return "Download CSV da Metabase"
    if step_id == "figures":
        return "Aggiornamento grafici e tabelle"
    if step_id == "build":
        return "Compilazione PDF"
    if step_id == "ref_check":
        return "Controllo riferimenti"
    if step_id == "package":
        return "Creazione ZIP"
    if step_id.startswith("text:"):
        return f"Generazione testo: {_section_label(step_id.removeprefix('text:'))}"
    return step_id


def _update_job_progress(job_id: str, *, step_id: str, phase: str) -> None:
    job = _JOBS[job_id]
    plan: dict[str, float] = job["progress_plan"]
    completed: list[str] = job["completed"]

    if phase == "start":
        job["current_step"] = step_id
        job["current_label"] = _progress_label(step_id)
    elif phase == "done":
        if step_id not in completed:
            completed.append(step_id)
        job["completed"] = completed
        job["current_step"] = None
        job["current_label"] = None
        if step_id.startswith("text:"):
            job["sections_done"] = sum(1 for s in completed if s.startswith("text:"))

    done_weight = sum(plan.get(s, 0.0) for s in completed)
    job["progress_pct"] = min(100, int(round(done_weight)))
    job["updated_at"] = now_iso()


def job_status_payload(job_id: str) -> JobStatusResponse:
    job = _JOBS[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        steps=job.get("steps") or [],
        error=job.get("error"),
        ref_check=job.get("ref_check"),
        download_url=job.get("download_url"),
        tex_url=job.get("tex_url"),
        pdf_url=job.get("pdf_url"),
        progress_pct=job.get("progress_pct", 0),
        current_step=job.get("current_step"),
        current_label=job.get("current_label"),
        completed=list(job.get("completed") or []),
        sections_done=job.get("sections_done", 0),
        sections_total=job.get("sections_total", 0),
    )


def _apply_result(job_id: str, result: PipelineResult) -> None:
    job = _JOBS[job_id]
    job["updated_at"] = now_iso()
    job["steps"] = result.steps
    if result.ref_check:
        job["ref_check"] = {
            "ok": result.ref_check.ok,
            "message": result.ref_check.message,
            "missing_labels": result.ref_check.missing_labels,
            "undefined_in_log": result.ref_check.undefined_in_log,
            "broken_in_pdf": result.ref_check.broken_in_pdf,
        }
    if result.ok and result.zip_path and result.zip_path.is_file():
        job["status"] = JobStatus.succeeded
        job["zip_path"] = str(result.zip_path)
        job["tex_path"] = str(result.tex_path)
        job["pdf_path"] = str(result.pdf_path)
        job["download_url"] = f"/report/jobs/{job_id}/download"
        job["tex_url"] = f"/report/jobs/{job_id}/tex"
        job["pdf_url"] = f"/report/jobs/{job_id}/pdf"
        job["error"] = None
        job["progress_pct"] = 100
        job["current_step"] = None
        job["current_label"] = None
    else:
        job["status"] = JobStatus.failed
        job["error"] = result.error or "Pipeline fallita"
        if result.tex_path.is_file():
            job["tex_path"] = str(result.tex_path)
            job["tex_url"] = f"/report/jobs/{job_id}/tex"
        if result.pdf_path.is_file():
            job["pdf_path"] = str(result.pdf_path)
            job["pdf_url"] = f"/report/jobs/{job_id}/pdf"


def _execute_job(job_id: str, options: GenerateOptions) -> None:
    if not _JOB_LOCK.acquire(blocking=False):
        job = _JOBS[job_id]
        job["status"] = JobStatus.failed
        job["updated_at"] = now_iso()
        job["error"] = "Un'altra generazione è già in corso. Riprova più tardi."
        return

    try:
        job = _JOBS[job_id]
        job["status"] = JobStatus.running
        job["updated_at"] = now_iso()
        section_keys = job["section_keys"]

        def on_progress(step_id: str, phase: str) -> None:
            _update_job_progress(job_id, step_id=step_id, phase=phase)

        result = run_pipeline(
            skip_fetch=options.skip_fetch,
            skip_figures=options.skip_figures,
            skip_text=options.skip_text,
            inject_only=options.inject_only,
            skip_build=options.skip_build,
            model=options.model,
            sections=section_keys,
            passes=options.passes,
            fail_on_bad_refs=options.fail_on_bad_refs,
            artifact_dir=DEFAULT_ARTIFACT_DIR,
            on_progress=on_progress,
        )
        _apply_result(job_id, result)
    except Exception as exc:  # noqa: BLE001
        job = _JOBS[job_id]
        job["status"] = JobStatus.failed
        job["updated_at"] = now_iso()
        job["error"] = str(exc)
    finally:
        _JOB_LOCK.release()


def create_job(options: GenerateOptions) -> str:
    section_keys = resolve_sections(options.sections)
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = _new_job_dict(job_id, section_keys=section_keys, options=options)
    return job_id


def get_job(job_id: str) -> dict[str, Any]:
    if job_id not in _JOBS:
        raise KeyError(job_id)
    return _JOBS[job_id]


def execute_job_sync(job_id: str, options: GenerateOptions) -> None:
    _execute_job(job_id, options)
