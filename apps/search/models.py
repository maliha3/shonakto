import uuid

from django.conf import settings
from django.db import models


def search_photo_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"search_queries/{instance.id}.{ext}"


class SearchQuery(models.Model):
    """A single 'find my missing person' AI search request — just a photo upload."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_queries"
    )
    photo = models.ImageField(upload_to=search_photo_upload_path)

    query_embedding = models.JSONField(null=True, blank=True)

    is_processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_queries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SearchQuery {self.id} by {self.requested_by}"


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class MatchResult(models.Model):
    """
    A single face-match hit for a SearchQuery, cached after the AI pipeline
    runs. The query photo is compared against both the found-person and the
    lost-person databases, so exactly one of found_person/lost_person is set
    per row — never both, never neither.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name="matches")
    found_person = models.ForeignKey(
        "found_persons.FoundPerson",
        on_delete=models.CASCADE,
        related_name="match_results",
        null=True,
        blank=True,
    )
    lost_person = models.ForeignKey(
        "found_persons.LostPerson",
        on_delete=models.CASCADE,
        related_name="match_results",
        null=True,
        blank=True,
    )
    match_percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_matches"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "match_results"
        ordering = ["-match_percentage"]
        unique_together = (("search_query", "found_person"), ("search_query", "lost_person"))
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(found_person__isnull=False, lost_person__isnull=True)
                    | models.Q(found_person__isnull=True, lost_person__isnull=False)
                ),
                name="match_result_exactly_one_target",
            ),
        ]

    def __str__(self):
        return f"{self.match_percentage:.2f}% match for query {self.search_query_id}"

    @property
    def matched_person(self):
        return self.found_person or self.lost_person


class MatchNotification(models.Model):
    """
    Sent by a searcher to the uploader of a matched FoundPerson record, e.g.
    "someone thinks they found a match for the person you reported" — shows
    up in the uploader's Alerts tab with the searcher's contact details so
    they can follow up.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match_result = models.OneToOneField(MatchResult, on_delete=models.CASCADE, related_name="notification")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_notifications"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "match_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.recipient} for match {self.match_result_id}"
