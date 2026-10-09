FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home cine && mkdir -p /app/data /app/models && chown -R cine:cine /app
USER cine
EXPOSE 8501

FROM base AS test
RUN pip install --user --no-cache-dir -r requirements-dev.txt
CMD ["python", "-m", "pytest", "-q"]

FROM base AS runtime
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
