# Dockerfile multi-stage pour CSBOT
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Installation de Poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Installation des dépendances Python
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-interaction --no-ansi

# Copie du code source
COPY . .

# Création des dossiers nécessaires
RUN mkdir -p logs data/documents

EXPOSE 8088

CMD ["python", "main.py"]

