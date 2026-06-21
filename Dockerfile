# ── Base Python ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libzbar0 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js pour Tailwind ─────────────────────────────────────────────────────
FROM base AS node-builder

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY package.json package-lock.json* tailwind.config.js ./
RUN npm ci --only=production

COPY static/ ./static/
COPY templates/ ./templates/

# Compiler Tailwind CSS
RUN npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify

# ── Python Dependencies ───────────────────────────────────────────────────────
FROM base AS python-deps

WORKDIR /install

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ── Production Image ──────────────────────────────────────────────────────────
FROM base AS production

# Utilisateur non-root
RUN groupadd --gid 1001 django \
    && useradd --uid 1001 --gid django --shell /bin/bash --create-home django

WORKDIR /app

# Copier les dépendances Python
COPY --from=python-deps /install /usr/local

# Copier les assets compilés
COPY --from=node-builder /build/static/css/main.css ./static/css/main.css

# Copier le code source
COPY --chown=django:django . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R django:django /app

USER django

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]

# ── Development Image ─────────────────────────────────────────────────────────
FROM base AS development

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

COPY . .

EXPOSE 8000 5555

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
