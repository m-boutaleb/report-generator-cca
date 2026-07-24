#!/usr/bin/env python3
"""REST API that runs the full report pipeline and returns main.pdf + main.tex."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from config import ROOT, SECTION_GENERATION_ORDER
from report_jobs import (
    GenerateOptions,
    JobStatus,
    JobStatusResponse,
    create_job,
    execute_job_sync,
    get_job,
    job_lock_locked,
    job_status_payload,
    resolve_sections,
)
from test_google_ai import GEMINI_MODEL

logger = logging.getLogger(__name__)

STATIC_DIR = ROOT / "static"
JOB_HTML_PATH = STATIC_DIR / "report_job.html"

app = FastAPI(
    title="Rapporto CCA — Report Generator API",
    description=(
        "Avvia la pipeline completa del rapporto: download CSV Metabase → "
        "aggiornamento grafici in main.tex → generazione testo (2 colonne) → "
        "compilazione PDF → validazione \\ref → consegna ZIP (pdf+tex)."
    ),
    version="1.1.0",
)


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


def _options_from_request(request: GenerateRequest) -> GenerateOptions:
    return GenerateOptions(
        skip_fetch=request.skip_fetch,
        skip_figures=request.skip_figures,
        skip_text=request.skip_text,
        inject_only=request.inject_only,
        skip_build=request.skip_build,
        model=request.model,
        sections=request.sections,
        passes=request.passes,
        fail_on_bad_refs=request.fail_on_bad_refs,
    )


def _options_from_query(
    *,
    skip_fetch: bool = False,
    skip_figures: bool = False,
    skip_text: bool = False,
    inject_only: bool = False,
    skip_build: bool = False,
    model: str = GEMINI_MODEL,
    passes: int = 2,
    fail_on_bad_refs: bool = True,
) -> GenerateOptions:
    return GenerateOptions(
        skip_fetch=skip_fetch,
        skip_figures=skip_figures,
        skip_text=skip_text,
        inject_only=inject_only,
        skip_build=skip_build,
        model=model,
        passes=passes,
        fail_on_bad_refs=fail_on_bad_refs,
    )


def _enqueue_job(
    options: GenerateOptions,
    background_tasks: BackgroundTasks,
) -> tuple[str, bool]:
    """Create job and schedule background execution. Returns (job_id, started)."""
    try:
        resolve_sections(options.sections)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if job_lock_locked():
        raise HTTPException(
            status_code=409,
            detail="Una generazione è già in corso. Attendi il completamento e riprova.",
        )

    job_id = create_job(options)
    background_tasks.add_task(execute_job_sync, job_id, options)
    return job_id, True


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "root": str(ROOT)}


@app.get("/report/sections")
def list_sections() -> dict[str, list[str]]:
    return {"sections": list(SECTION_GENERATION_ORDER)}


@app.get("/report/generate")
def generate_report_get(
    background_tasks: BackgroundTasks,
    skip_fetch: bool = Query(False),
    skip_figures: bool = Query(False),
    skip_text: bool = Query(False),
    inject_only: bool = Query(False),
    skip_build: bool = Query(False),
    model: str = Query(GEMINI_MODEL),
    passes: int = Query(2, ge=1, le=5),
    fail_on_bad_refs: bool = Query(True),
):
    """
    Avvia la pipeline in background e reindirizza alla pagina di monitoraggio.

    Esempio: apri nel browser `http://host:8000/report/generate`
    """
    options = _options_from_query(
        skip_fetch=skip_fetch,
        skip_figures=skip_figures,
        skip_text=skip_text,
        inject_only=inject_only,
        skip_build=skip_build,
        model=model,
        passes=passes,
        fail_on_bad_refs=fail_on_bad_refs,
    )
    job_id, _ = _enqueue_job(options, background_tasks)
    return RedirectResponse(url=f"/report/jobs/{job_id}", status_code=303)


@app.post("/report/generate")
def generate_report_post(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Avvia la pipeline completa.

    - `async_mode=false` (default): esegue in modo sincrono e restituisce lo ZIP.
    - `async_mode=true`: restituisce JSON con `job_id`; monitora con
      `GET /report/jobs/{job_id}/status` o la pagina `GET /report/jobs/{job_id}`.
    """
    options = _options_from_request(request)

    if request.async_mode:
        job_id, _ = _enqueue_job(options, background_tasks)
        return JSONResponse(
            status_code=202,
            content=job_status_payload(job_id).model_dump(),
        )

    if job_lock_locked():
        raise HTTPException(
            status_code=409,
            detail="Una generazione è già in corso. Usa async_mode=true oppure attendi.",
        )

    job_id = create_job(options)
    execute_job_sync(job_id, options)
    job = get_job(job_id)
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
                "status_url": f"/report/jobs/{job_id}/status",
                "page_url": f"/report/jobs/{job_id}",
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


@app.get("/report/jobs/{job_id}", response_class=HTMLResponse)
def job_status_page(job_id: str) -> HTMLResponse:
    """Pagina HTML con polling ogni 2 s su /report/jobs/{job_id}/status."""
    try:
        get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job non trovato") from exc
    if not JOB_HTML_PATH.is_file():
        raise HTTPException(status_code=500, detail="Template HTML mancante")
    return HTMLResponse(JOB_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/report/jobs/{job_id}/status", response_model=JobStatusResponse)
def job_status_json(job_id: str) -> JobStatusResponse:
    """Stato JSON per polling (aggiornamento progresso per sezione)."""
    try:
        get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job non trovato") from exc
    return job_status_payload(job_id)


@app.get("/report/jobs/{job_id}/download")
def download_zip(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job non trovato") from exc
    zip_path = job.get("zip_path")
    if not zip_path or not Path(zip_path).is_file():
        raise HTTPException(status_code=404, detail="ZIP non disponibile per questo job")
    path = Path(zip_path)
    return FileResponse(path=path, media_type="application/zip", filename=path.name)


@app.get("/report/jobs/{job_id}/tex")
def download_tex(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job non trovato") from exc
    tex_path = job.get("tex_path")
    if not tex_path or not Path(tex_path).is_file():
        raise HTTPException(status_code=404, detail="TEX non disponibile")
    path = Path(tex_path)
    return FileResponse(path=path, media_type="application/x-tex", filename=path.name)


@app.get("/report/jobs/{job_id}/pdf")
def download_pdf(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job non trovato") from exc
    pdf_path = job.get("pdf_path")
    if not pdf_path or not Path(pdf_path).is_file():
        raise HTTPException(status_code=404, detail="PDF non disponibile")
    path = Path(pdf_path)
    return FileResponse(path=path, media_type="application/pdf", filename=path.name)


@app.get("/report/latest/download")
def download_latest(
    kind: str = Query("zip", pattern="^(zip|tex|pdf)$"),
):
    """Scarica l'ultimo artifact prodotto in output/artifacts (o main.* corrente)."""
    from pipeline import DEFAULT_ARTIFACT_DIR

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
