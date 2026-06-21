# PerteDocsTG — Installation sur Windows


## 🚀 Installation pas à pas (Windows)

### Prérequis

| Logiciel | Version | Lien |
|----------|---------|------|
| Python | 3.11+ | https://python.org/downloads/ |
| PostgreSQL | 16+ | https://postgresql.org/download/windows/ |
| Node.js | 20+ | https://nodejs.org/ |
| Redis | via WSL2 ou Memurai | Voir ci-dessous |

### 1. Cloner et préparer

```powershell
cd C:\PROJETS
# Le dossier pertedocstg doit déjà exister avec les fichiers du projet

cd pertedocstg

# Créer l'environnement virtuel
py -m venv env
env\Scripts\activate
```

### 2. Installer les dépendances Windows

```powershell
# Mettre à jour pip d'abord
python -m pip install --upgrade pip

# Installer les dépendances adaptées Windows
pip install -r requirements-dev-windows.txt
```

> **Note** : `requirements-dev-windows.txt` remplace :
> - `psycopg[binary]==3.2.1` → `psycopg[binary]>=3.2.2`
> - `python-magic` → `python-magic-bin` (contient la DLL libmagic)
> - `WeasyPrint` → `xhtml2pdf` (pas de dépendance GTK)
> - `gunicorn` → `waitress` (serveur WSGI natif Windows)

### 3. Configurer l'environnement

```powershell
# Copier le .env de développement
copy .env.dev .env

# Ouvrir et éditer .env avec Notepad
notepad .env
```

Variables importantes à vérifier dans `.env` :
```env
DJANGO_SETTINGS_MODULE=config.settings_dev
DB_PASSWORD=votre_mot_de_passe_postgres
```

### 4. Créer la base de données PostgreSQL

```powershell
# Ouvrir psql (installé avec PostgreSQL)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres

# Dans psql :
# CREATE DATABASE pertedocstg_dev;
# \q
```

Ou via **pgAdmin** (interface graphique installée avec PostgreSQL) :
- Clic droit sur "Databases" → "Create" → "Database..."
- Nom : `pertedocstg_dev`

### 5. Appliquer les migrations

```powershell
python manage.py migrate
python manage.py load_togo_geography
python manage.py createsuperuser
```

### 6. Compiler Tailwind CSS

```powershell
npm install
npm run build
```

Pour le mode watch (recompilation automatique) :
```powershell
npm run dev
```

### 7. Lancer le serveur

```powershell
python manage.py runserver
```

Accès : http://localhost:8000

---

## 🔴 Redis sur Windows

Redis ne tourne pas nativement sur Windows. Trois options :

### Option A — WSL2 (recommandée)
```bash
# Dans WSL2 (Ubuntu)
sudo apt install redis-server
sudo service redis-server start
redis-cli ping  # → PONG
```

### Option B — Memurai (Redis natif Windows)
Télécharger : https://www.memurai.com/get-memurai (gratuit pour dev)

```powershell
# Démarrer Memurai (se lance comme un service Windows)
memurai.exe
```

### Option C — Sans Redis (tâches synchrones)
Décommenter dans `config/settings_dev.py` :
```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

---

## ⚙️ Celery sur Windows

Celery nécessite le flag `-P solo` sur Windows (pas de fork) :

```powershell
# Terminal 1 : serveur Django
python manage.py runserver

# Terminal 2 : worker Celery
celery -A config worker -l info -P solo

# Terminal 3 : beat scheduler (optionnel)
celery -A config beat -l info
```

---

## 📄 WeasyPrint (génération PDF)

WeasyPrint nécessite GTK3 sur Windows (complexe à installer). Le projet utilise `xhtml2pdf` en développement Windows.

Pour utiliser WeasyPrint en production (Linux/Docker) : aucune modification nécessaire, le `requirements.txt` principal l'inclut.

---

## 🗄️ SQLite à la place de PostgreSQL (démarrage rapide)

Décommenter dans `config/settings_dev.py` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

> SQLite est suffisant pour le développement mais ne supporte pas toutes les fonctionnalités PostgreSQL utilisées en production.

---

## ✅ Vérification de l'installation

```powershell
# Tester Django
python manage.py check

# Tester la connexion DB
python manage.py dbshell

# Lancer les tests
python manage.py test tests/ -v 2
```

---

## 📋 Résumé des commandes quotidiennes

```powershell
# Activer l'environnement
env\Scripts\activate

# Lancer le serveur
python manage.py runserver

# Appliquer les migrations après un git pull
python manage.py migrate

# Compiler CSS après modification des templates
npm run build

# Créer des migrations après modification des modèles
python manage.py makemigrations
python manage.py migrate
```

---

*PerteDocsTG v1.5 — Support Windows*
