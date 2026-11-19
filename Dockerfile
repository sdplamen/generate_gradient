FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Pass with --build-arg VERSION=1.2 --build-arg REVISION=$(git rev-parse --short HEAD)
ARG VERSION=dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="generate-gradient" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.source="https://github.com/sdplamen/generate_gradient"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect static files and run the tests at build time; a throwaway key is enough for these steps.
RUN SECRET_KEY=build-only-key python manage.py collectstatic --noinput \
    && SECRET_KEY=build-only-key python manage.py test generate

# Run as an unprivileged user; /app/data holds the SQLite database (mount a volume there to keep it).
RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && if [ -f gradient_generator_db ]; then cp gradient_generator_db /app/data/; fi \
    && chown -R appuser:appuser /app
USER appuser

ENV DB_PATH=/app/data/gradient_generator_db \
    PORT=8000 \
    WEB_CONCURRENCY=3

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn generate_gradient.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --access-logfile -"]
