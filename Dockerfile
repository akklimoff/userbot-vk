FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY userbot ./userbot

RUN useradd --create-home --uid 1000 appuser && mkdir -p /app/state && chown appuser /app/state
USER appuser

CMD ["python", "-m", "userbot.main"]
