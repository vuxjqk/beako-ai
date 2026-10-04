FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# The embedding model (~130 MB), baked into the image so a host without a persistent disk does
# not download it again on every start. Outside /app, so docker-compose's code mount leaves it
# alone; hosts use it by setting EMBED_CACHE_DIR=/opt/models (local runs keep data/models)
COPY src/ingest/settings.py /tmp/settings.py
RUN python -c "import importlib.util as u; s = u.spec_from_file_location('s', '/tmp/settings.py'); m = u.module_from_spec(s); s.loader.exec_module(m); from fastembed import TextEmbedding; TextEmbedding(m.MODEL_NAME, cache_dir='/opt/models')" \
    && rm /tmp/settings.py

COPY . .

EXPOSE 8000

# Production start: apply migrations, then serve on $PORT (set by hosts such as Render) behind
# their proxy. docker-compose replaces this with a --reload command for development
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
