FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock* /app/
RUN if [ -f /app/requirements.lock ]; then \
      pip install --no-cache-dir -r /app/requirements.lock; \
    else \
      pip install --no-cache-dir -r /app/requirements.txt; \
    fi

COPY . /app
RUN mkdir -p /app/media

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
