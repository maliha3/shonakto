import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def generate_embedding_for_found_person(found_person_id):
    """Runs the AI face-embedding pipeline on a newly uploaded found-person photo."""
    from apps.search.face_utils import generate_face_embedding

    from .models import FoundPerson

    try:
        found_person = FoundPerson.objects.get(id=found_person_id)
    except FoundPerson.DoesNotExist:
        logger.warning("FoundPerson %s no longer exists; skipping embedding.", found_person_id)
        return

    embedding = generate_face_embedding(found_person.photo)
    if embedding is None:
        logger.warning("No face detected in found_person=%s; leaving embedding empty.", found_person_id)
        return

    found_person.face_embedding = embedding
    found_person.embedding_generated_at = timezone.now()
    found_person.save(update_fields=["face_embedding", "embedding_generated_at"])
    logger.info("Embedding generated for found_person=%s", found_person_id)


@shared_task
def purge_expired_found_records():
    """
    Data Retention Rule: delete found records (and their images) older than
    FOUND_RECORD_RETENTION_DAYS (default 30 days). Scheduled via Celery beat
    (see config/celery.py beat_schedule) to run daily.
    """
    from .models import FoundPerson

    expired = FoundPerson.objects.filter(expires_at__lte=timezone.now())
    count = expired.count()

    for record in expired.iterator():
        if record.photo:
            record.photo.delete(save=False)
        record.delete()

    logger.info("Purged %s expired found-person record(s).", count)
    return count
