"""
PerteDocsTG — Settings de DÉVELOPPEMENT LOCAL
Surcharge config/settings.py pour le dev (SQLite, cache mémoire, email console)

Usage : dans .env → DJANGO_SETTINGS_MODULE=config.settings_dev
"""

# ── Créer les dossiers requis AVANT l'import de settings ─────────────────────
# (évite FileNotFoundError sur le handler logging 'file')
from pathlib import Path as _Path
_BASE = _Path(__file__).resolve().parent.parent
for _d in ['logs', 'media', 'staticfiles', 'static/css', 'static/js']:
    (_BASE / _d).mkdir(parents=True, exist_ok=True)

from .settings import *  # noqa

# ── Mode debug ────────────────────────────────────────────────────────────────
DEBUG = True
ALLOWED_HOSTS = ['*']

# ── Base de données ───────────────────────────────────────────────────────────
# Par défaut : SQLite (aucune installation requise, parfait pour démarrer)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Option PostgreSQL : décommentez quand vous voulez basculer
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': env('DB_NAME', default='pertedocstg_dev'),
#         'USER': env('DB_USER', default='postgres'),
#         'PASSWORD': env('DB_PASSWORD', default='postgres'),
#         'HOST': env('DB_HOST', default='localhost'),
#         'PORT': env('DB_PORT', default='5432'),
#     }
# }

# ── Cache ─────────────────────────────────────────────────────────────────────
# Par défaut : cache mémoire (aucune installation requise)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Option Redis : décommentez si vous avez Redis (WSL2 ou Memurai)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
#     }
# }

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
# Par défaut : tâches synchrones (pas besoin de Redis ni de worker)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# Désactivez les deux lignes ci-dessus si vous avez Redis

# ── Email ─────────────────────────────────────────────────────────────────────
# Affiche les emails dans la console au lieu de les envoyer
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Sécurité (désactivée en dev) ──────────────────────────────────────────────
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ── Logging console uniquement (pas de fichier en dev) ────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'dev': {
            'format': '[{levelname}] {asctime} {module} — {message}',
            'style': '{',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'dev',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            # Passez à 'DEBUG' pour voir toutes les requêtes SQL
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ── Debug Toolbar (optionnel — pip install django-debug-toolbar) ──────────────
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1', '::1']
    DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda r: False}  # Désactivée
except ImportError:
    pass

# ── Media files ───────────────────────────────────────────────────────────────
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# ── Stockage des fichiers statiques ──────────────────────────────────────────
# On surcharge WhiteNoise pour utiliser le système de fichiers local simple en dev
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ── PDF : xhtml2pdf disponible sur Windows (WeasyPrint nécessite GTK) ─────────
import sys
USE_WEASYPRINT = sys.platform != 'win32'

# ── Tailwind CDN (évite Node.js en développement) ────────────────────────────
USE_TAILWIND_CDN = True
