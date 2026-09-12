import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("missing_persons")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule: run the found-record purge every day at 03:00 server time.
app.conf.beat_schedule = {
    "purge-expired-found-records-daily": {
        "task": "apps.found_persons.tasks.purge_expired_found_records",
        "schedule": crontab(hour=3, minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
