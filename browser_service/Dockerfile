FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CAD_PROFILE=free CAD_DATA_DIR=/tmp/engcad/jobs
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglu1-mesa libglib2.0-0 libgomp1 gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 cad && useradd --uid 10001 --gid cad --create-home cad
WORKDIR /app
COPY pyproject.toml README.md LICENSE /app/core/
COPY skills/engineering-cad-converter/scripts /app/core/skills/engineering-cad-converter/scripts
COPY requirements-tested.txt /app/core-constraints.txt
COPY browser_service/requirements-tested.txt /app/web-constraints.txt
COPY browser_service/pyproject.toml browser_service/README.md browser_service/LICENSE browser_service/THIRD_PARTY_NOTICES.md /app/service/
COPY browser_service/engcad_web /app/service/engcad_web
RUN pip install --no-cache-dir -c /app/core-constraints.txt -c /app/web-constraints.txt "/app/core[step]" /app/service
COPY browser_service/deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod 755 /app/entrypoint.sh
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health',timeout=4)"
ENTRYPOINT ["/app/entrypoint.sh"]
