import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from apps.accounts.models import Division


class PersonCondition(models.TextChoices):
    FOUND_ALIVE = "found_alive", "Found Alive"
    UNIDENTIFIED_DECEASED = "unidentified_deceased", "Unidentified Deceased"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    UNKNOWN = "unknown", "Unknown"


class DistinguishingMark(models.TextChoices):
    TATTOO = "tattoo", "Tattoo"
    SCAR = "scar", "Scar"
    BIRTHMARK = "birthmark", "Birthmark"
    MOLE = "mole", "Mole"
    PIERCING = "piercing", "Piercing"


class CaseStatus(models.TextChoices):
    UNIDENTIFIED = "unidentified", "Unidentified"
    UNDER_CARE = "under_care", "Under Care"
    REUNITED = "reunited", "Reunited"


def found_photo_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"found_persons/{instance.id}.{ext}"


def default_expiry():
    from django.conf import settings as s

    return timezone.now() + timezone.timedelta(days=s.FOUND_RECORD_RETENTION_DAYS)


class FoundPerson(models.Model):
    """
    A found-alive or unidentified-deceased record uploaded by a General
    Seeker, Police, Morgue Authority, or other Authority.

    Data Retention: `expires_at` is set on save (30 days from upload) and a
    Celery beat task (see apps.found_persons.tasks) purges records + their
    photos once `expires_at` has passed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="found_person_uploads"
    )

    photo = models.ImageField(upload_to=found_photo_upload_path)
    condition = models.CharField(max_length=30, choices=PersonCondition.choices)

    found_location = models.CharField(max_length=255, help_text="Free-text location description")
    division = models.CharField(max_length=20, choices=Division.choices)

    found_timestamp = models.DateTimeField(help_text="When the person was found")
    description = models.TextField(blank=True, help_text="Additional notes: clothing, dialect, behavior, etc.")

    estimated_age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWN)
    distinguishing_marks = ArrayField(
        models.CharField(max_length=20, choices=DistinguishingMark.choices),
        default=list,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=CaseStatus.choices, default=CaseStatus.UNIDENTIFIED)

    # Facial embedding used for AI matching. Stored as JSON for portability;
    # if the `pgvector` Postgres extension + column is preferred instead,
    # swap this for `pgvector.django.VectorField(dimensions=128)` and index
    # it with an IVFFlat/HNSW index (see README "Using pgvector" section).
    face_embedding = models.JSONField(null=True, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True, help_text="Set False once matched/resolved or purged")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry, db_index=True)

    class Meta:
        db_table = "found_persons"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_condition_display()} in {self.division} ({self.created_at:%Y-%m-%d})"

    @property
    def uploader_badge(self):
        return self.uploaded_by.authority_badge
