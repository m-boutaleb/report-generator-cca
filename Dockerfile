# Rapporto CCA — report generator API (FastAPI + LaTeX)
FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TEXMFHOME=/tmp/texmf-home \
    TEXMFVAR=/tmp/texmf-var \
    TEXMFCONFIG=/tmp/texmf-config

# LaTeX stack needed by main.tex (elsarticle, pgfplots, babel italian, …)
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-fonts-extra \
        texlive-science \
        texlive-lang-italian \
        texlive-bibtex-extra \
        latexmk \
        ghostscript \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source (secrets.json is NOT copied; mount or inject at runtime)
COPY *.py ./
COPY prompts/ ./prompts/
COPY static/ ./static/
COPY secrets.example.json ./
COPY main.tex ./

# Empty data/output dirs; CSVs are fetched / produced at runtime
RUN mkdir -p data output/artifacts \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "api.py"]
