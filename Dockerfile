FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates ./templates
COPY static ./static

RUN mkdir -p /app/database

ENV PORT=5000
ENV EVENT_DB=/app/database/events.db
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
