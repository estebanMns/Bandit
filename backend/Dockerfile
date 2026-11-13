FROM python:3.12-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Versiones exactas con su huella (requirements.txt). Todo llega ya compilado salvo los dos
# paquetes de notificaciones push, que solo se publican como código fuente.
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes --only-binary :all:     --no-binary pywebpush --no-binary http-ece -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/app/src

COPY alembic.ini ./
COPY migrations ./migrations

RUN useradd --create-home --uid 10001 bandit \
  && mkdir -p /app/var/media \
  && chown -R bandit /app/var
USER bandit

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory bandit.main:create_app --host 0.0.0.0 --port 8000"]
