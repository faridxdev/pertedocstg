"""
PerteDocsTG — Configuration Celery
"""

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pertedocstg')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Tâches périodiques
app.conf.beat_schedule = {
    'cleanup-draft-declarations-daily': {
        'task': 'notifications.tasks.cleanup_draft_declarations',
        'schedule': 86400.0,  # Chaque 24h
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
