# PerteDocsTG — Guide de Déploiement Complet
## Ubuntu 24.04 LTS · Docker · Nginx · SSL Let's Encrypt

---

## 1. Prérequis serveur

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Paquets essentiels
sudo apt install -y \
  curl wget git unzip \
  ufw fail2ban \
  htop net-tools

# Docker Engine
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose v2
sudo apt install -y docker-compose-plugin

# Vérification
docker --version
docker compose version
```

---

## 2. Configuration du pare-feu (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

---

## 3. Configuration Fail2ban

```bash
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
# Modifier : bantime = 3600 / maxretry = 5
sudo systemctl enable --now fail2ban
```

---

## 4. Cloner le projet

```bash
sudo mkdir -p /opt/pertedocstg
sudo chown $USER:$USER /opt/pertedocstg
cd /opt/pertedocstg
git clone https://github.com/votre-org/pertedocstg.git .
```

---

## 5. Configuration de l'environnement

```bash
cp .env.example .env
nano .env

# Remplir obligatoirement :
# SECRET_KEY = (générer avec : python3 -c "import secrets; print(secrets.token_urlsafe(50))")
# DB_PASSWORD = mot de passe fort
# REDIS_PASSWORD = mot de passe fort
# EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
# AFRICAS_TALKING_API_KEY (si SMS activé)
```

---

## 6. Créer les répertoires

```bash
mkdir -p logs nginx/conf.d
chmod 755 logs
```

---

## 7. Démarrage initial (sans SSL)

```bash
# Démarrer seulement db et redis d'abord
docker compose up -d db redis
sleep 10

# Démarrer l'application
docker compose up -d web celery_worker celery_beat

# Vérifier les logs
docker compose logs -f web
```

---

## 8. Initialisation de la base de données

```bash
# Migrations
docker compose exec web python manage.py migrate

# Charger les données géographiques du Togo
docker compose exec web python manage.py load_togo_geography

# Créer un superadmin
docker compose exec web python manage.py createsuperuser \
  --email admin@pertedocs.tg

# Collecter les statiques
docker compose exec web python manage.py collectstatic --noinput
```

---

## 9. Configuration SSL avec Let's Encrypt

```bash
# Démarrer Nginx en HTTP d'abord (pour la validation ACME)
# Modifier temporairement nginx/conf.d/pertedocstg.conf pour désactiver HTTPS

docker compose up -d nginx

# Obtenir le certificat SSL
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@pertedocs.tg \
  --agree-tos \
  --no-eff-email \
  -d pertedocs.tg \
  -d www.pertedocs.tg

# Réactiver HTTPS dans la config Nginx
# Redémarrer Nginx
docker compose restart nginx
```

---

## 10. Déploiement complet

```bash
docker compose up -d

# Vérifier l'état de tous les services
docker compose ps

# Vérifier la santé de l'app
curl -f https://pertedocs.tg/health/
```

---

## 11. Service Systemd (démarrage automatique)

```bash
sudo nano /etc/systemd/system/pertedocstg.service
```

```ini
[Unit]
Description=PerteDocsTG Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/pertedocstg
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pertedocstg
sudo systemctl start pertedocstg
```

---

## 12. Sauvegardes automatiques

```bash
nano /opt/pertedocstg/scripts/backup.sh
```

```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/pertedocstg"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "$(date) — Démarrage sauvegarde PerteDocsTG"

# Backup PostgreSQL
docker compose -f /opt/pertedocstg/docker-compose.yml exec -T db \
  pg_dump -U pertedocstg_user pertedocstg | \
  gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup media
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" \
  -C /opt/pertedocstg media/

# Supprimer les anciennes sauvegardes
find "$BACKUP_DIR" -name "*.gz" -mtime +$KEEP_DAYS -delete

echo "$(date) — Sauvegarde terminée : $BACKUP_DIR"
```

```bash
chmod +x /opt/pertedocstg/scripts/backup.sh

# Cron quotidien à 2h
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/pertedocstg/scripts/backup.sh >> /var/log/pertedocstg-backup.log 2>&1") | crontab -

# Renouvellement SSL automatique
(crontab -l 2>/dev/null; echo "0 3 1 * * cd /opt/pertedocstg && docker compose run --rm certbot renew && docker compose restart nginx") | crontab -
```

---

## 13. Mise à jour de l'application

```bash
#!/bin/bash
# scripts/update.sh
set -e

cd /opt/pertedocstg

echo "Pulling dernières modifications..."
git pull origin main

echo "Reconstruction de l'image..."
docker compose build --no-cache web

echo "Migrations..."
docker compose run --rm web python manage.py migrate

echo "Fichiers statiques..."
docker compose run --rm web python manage.py collectstatic --noinput

echo "Redémarrage des services..."
docker compose up -d --no-deps web celery_worker celery_beat

echo "✅ Mise à jour terminée"
docker compose ps
```

---

## 14. Monitoring et logs

```bash
# Logs en temps réel
docker compose logs -f web
docker compose logs -f celery_worker
docker compose logs -f nginx

# Statistiques ressources
docker stats

# Santé de l'application
watch -n 5 'curl -s https://pertedocs.tg/health/ | python3 -m json.tool'
```

---

## 15. Checklist de production

- [ ] `DEBUG=False` dans `.env`
- [ ] `SECRET_KEY` fort et unique
- [ ] Mots de passe DB et Redis forts
- [ ] SSL Let's Encrypt actif
- [ ] Sauvegardes automatiques configurées
- [ ] Fail2ban actif
- [ ] UFW configuré
- [ ] Email SMTP fonctionnel (tester)
- [ ] SMS Africa's Talking configuré
- [ ] Superadmin créé
- [ ] Données géographiques chargées
- [ ] Monitoring configuré (optionnel : Sentry)
- [ ] `ALLOWED_HOSTS` correctement défini
- [ ] HTTPS forcé dans Nginx
- [ ] En-têtes de sécurité Nginx actifs

---

*PerteDocsTG v1.0 — République Togolaise*
