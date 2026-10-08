FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /opt/quant-engine

COPY pyproject.toml ./
COPY app ./app
COPY dashboard ./dashboard
COPY scripts ./scripts
COPY alembic.ini ./
COPY migrations ./migrations

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && groupadd --gid 10001 quant \
    && useradd --uid 10001 --gid quant --create-home --shell /usr/sbin/nologin quant \
    && mkdir -p data reports \
    && chown -R quant:quant /opt/quant-engine

USER quant

EXPOSE 8000 8501

CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]