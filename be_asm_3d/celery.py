import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'be_asm_3d.settings')

app = Celery('be_asm_3d')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
