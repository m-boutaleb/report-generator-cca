#!/usr/bin/env python3
"""REST API that runs the full report pipeline and returns main.pdf + main.tex."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from config import ROOT, SECTION_GENERATION_ORDER
from pipeline import DEFAULT_ARTIFACT_DIR, PipelineResult, run_pipeline
from test_google_ai import GEMINI_MODEL

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rapporto CCA — Report Generator API",
    description=(
        "Avvia la pipeline completa del rapporto: download CSV Metabase → "
        "aggiornamento grafici in main.tex → generazione testo (2 colonne) → "
        "compilazione PDF → validazione \\ref → consegna ZIP (pdf+tex)."
    ),
    version="1.0.0",
)

_JOB_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class GenerateRequest(BaseModel):
    skip_fetch: bool = Field(False, description="Salta il download dei CSV")
    skip_figures: bool = Field(False, description="Salta la rigenerazione dei grafici")
    skip_text: bool = Field(False, description="Salta la generazione della prosa")
    inject_only: bool = Field(
        False,
        description="Inietta prosa dai backup locali senza chiamare Gemini",
    )
    skip_build: bool = Field(False, description="Salta la compilazione PDF")
    model: str = Field(GEMINI_MODEL, description="Modello Gemini/Gemma per la prosa")
    sections: list[str] | None = Field(
        None,
        description="Sottoinsieme di sezioni da generare (default: tutte)",
    )
    passes: int = Field(2, ge=1, le=5, description="Passate pdflatex")
    fail_on_bad_refs: bool = Field(
        True,
        description="Fallisci se esistono \\ref non risolti o '??' nel PDF",
    )
    async_mode: bool = Field(
        False,
        description="Se true, avvia in background e restituisce un job_id",
    )


class JobInfo(BaseModel):
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_sections(sections: list[str] | None) -> tuple[str, ...]:
    if not sections:
        return SECTION_GENERATION_ORDER
    unknown = sorted(set(sections) - set(SECTION_GENERATION_ORDER))
    if unknown:
        raise ValueError(
            f"Sezioni sconosciute: {', '.join(unknown)}. "
            f"Consentite: {', '.join(SECTION_GENERATION_ORDER)}"
        )
    # Preserve canonical order
    return tuple(k for k in SECTION_GENERATION_ORDER if k in sections)


def _job_payload(job_id: str) -> JobInfo:
    job = _JOBS[job_id]
    return JobInfo(
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
    )


def _apply_result(job_id: str, result: PipelineResult) -> None:
    job = _JOBS[job_id]
    job["updated_at"] = _now()
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
    else:
        job["status"] = JobStatus.failed
        job["error"] = result.error or "Pipeline fallita"
        if result.tex_path.is_file():
            job["tex_path"] = str(result.tex_path)
            job["tex_url"] = f"/report/jobs/{job_id}/tex"
        if result.pdf_path.is_file():
            job["pdf_path"] = str(result.pdf_path)
            job["pdf_url"] = f"/report/jobs/{job_id}/pdf"


def _execute_job(job_id: str, request: GenerateRequest) -> None:
    if not _JOB_LOCK.acquire(blocking=False):
        job = _JOBS[job_id]
        job["status"] = JobStatus.failed
        job["updated_at"] = _now()
        job["error"] = "Un'altra generazione è già in corso. Riprova più tardi."
        return

    try:
        job = _JOBS[job_id]
        job["status"] = JobStatus.running
        job["updated_at"] = _now()
        sections = _resolve_sections(request.sections)
        result = run_pipeline(
            skip_fetch=request.skip_fetch,
            skip_figures=request.skip_figures,
            skip_text=request.skip_text,
            inject_only=request.inject_only,
            skip_build=request.skip_build,
            model=request.model,
            sections=sections,
            passes=request.passes,
            fail_on_bad_refs=request.fail_on_bad_refs,
            artifact_dir=DEFAULT_ARTIFACT_DIR,
        )
        _apply_result(job_id, result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s fallito", job_id)
        job = _JOBS[job_id]
        job["status"] = JobStatus.failed
        job["updated_at"] = _now()
        job["error"] = str(exc)
    finally:
        _JOB_LOCK.release()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "root": str(ROOT)}


@app.get("/report/sections")
def list_sections() -> dict[str, list[str]]:
    return {"sections": list(SECTION_GENERATION_ORDER)}


@app.post("/report/generate")
def generate_report(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Avvia la pipeline completa.

    - `async_mode=false` (default): esegue in modo sincrono e restituisce lo ZIP
      `main.tex` + `main.pdf` come download.
    - `async_mode=true`: restituisce un `job_id`; lo stato si interroga con
      `GET /report/jobs/{job_id}` e lo ZIP con `GET /report/jobs/{job_id}/download`.
    """
    try:
        _resolve_sections(request.sections)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if _JOB_LOCK.locked() and not request.async_mode:
        raise HTTPException(
            status_code=409,
            detail="Una generazione è già in corso. Usa async_mode=true oppure attendi.",
        )

    job_id = uuid.uuid4().hex
    _JOBS[job_id] = {
        "status": JobStatus.queued,
        "created_at": _now(),
        "updated_at": _now(),
        "steps": [],
        "error": None,
        "ref_check": None,
        "download_url": None,
        "tex_url": None,
        "pdf_url": None,
    }

    if request.async_mode:
        background_tasks.add_task(_execute_job, job_id, request)
        return JSONResponse(
            status_code=202,
            content=_job_payload(job_id).model_dump(),
        )

    _execute_job(job_id, request)
    job = _JOBS[job_id]
    if job["status"] != JobStatus.succeeded:
        raise HTTPException(
            status_code=500,
            detail={
                "job_id": job_id,
                "error": job.get("error"),
                "ref_check": job.get("ref_check"),
                "steps": job.get("steps"),
                "tex_url": job.get("tex_url"),
                "pdf_url": job.get("pdf_url"),
            },
        )

    zip_path = Path(job["zip_path"])
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
        headers={
            "X-Job-Id": job_id,
            "X-Ref-Check": (job.get("ref_check") or {}).get("message", ""),
        },
    )


@app.get("/report/jobs/{job_id}", response_model=JobInfo)
def get_job(job_id: str) -> JobInfo:
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job non trovato")
    return _job_payload(job_id)


@app.get("/report/jobs/{job_id}/download")
def download_zip(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job non trovato")
    job = _JOBS[job_id]
    zip_path = job.get("zip_path")
    if not zip_path or not Path(zip_path).is_file():
        raise HTTPException(status_code=404, detail="ZIP non disponibile per questo job")
    path = Path(zip_path)
    return FileResponse(path=path, media_type="application/zip", filename=path.name)


@app.get("/report/jobs/{job_id}/tex")
def download_tex(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job non trovato")
    tex_path = _JOBS[job_id].get("tex_path")
    if not tex_path or not Path(tex_path).is_file():
        raise HTTPException(status_code=404, detail="TEX non disponibile")
    path = Path(tex_path)
    return FileResponse(path=path, media_type="application/x-tex", filename=path.name)


@app.get("/report/jobs/{job_id}/pdf")
def download_pdf(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job non trovato")
    pdf_path = _JOBS[job_id].get("pdf_path")
    if not pdf_path or not Path(pdf_path).is_file():
        raise HTTPException(status_code=404, detail="PDF non disponibile")
    path = Path(pdf_path)
    return FileResponse(path=path, media_type="application/pdf", filename=path.name)


@app.get("/report/latest/download")
def download_latest(
    kind: str = Query("zip", pattern="^(zip|tex|pdf)$"),
):
    """Scarica l'ultimo artifact prodotto in output/artifacts (o main.* corrente)."""
    if kind == "tex":
        path = ROOT / "main.tex"
        media = "application/x-tex"
    elif kind == "pdf":
        path = ROOT / "main.pdf"
        media = "application/pdf"
    else:
        artifacts = sorted(DEFAULT_ARTIFACT_DIR.glob("rapporto_*.zip"))
        if not artifacts:
            raise HTTPException(status_code=404, detail="Nessun ZIP trovato")
        path = artifacts[-1]
        media = "application/zip"

    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File non trovato: {path.name}")
    return FileResponse(path=path, media_type=media, filename=path.name)


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
