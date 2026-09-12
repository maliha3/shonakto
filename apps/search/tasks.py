import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def run_face_matching(search_query_id):
    """
    Triggered right after a search query is uploaded. Generates an embedding
    for the uploaded missing-person photo, then compares it against both the
    active FoundPerson AND active LostPerson embeddings via cosine
    similarity, storing any hit above settings.FACE_MATCH_THRESHOLD (default
    50%) as a MatchResult — a query photo might match someone who's already
    been found, or it might match another family's existing missing-person
    report (i.e. two people searching for the same person).
    """
    from apps.found_persons.models import FoundPerson, LostPerson
    from apps.search.face_utils import find_matches, generate_face_embedding

    from .models import MatchResult, SearchQuery

    try:
        query = SearchQuery.objects.get(id=search_query_id)
    except SearchQuery.DoesNotExist:
        logger.warning("SearchQuery %s no longer exists.", search_query_id)
        return

    embedding = query.query_embedding
    if embedding is None:
        embedding = generate_face_embedding(query.photo)
        if embedding is None:
            logger.warning("No face detected in query photo for SearchQuery %s.", search_query_id)
            query.is_processed = True
            query.save(update_fields=["is_processed"])
            return
        query.query_embedding = embedding
        query.save(update_fields=["query_embedding"])

    found_candidates = list(
        FoundPerson.objects.filter(is_active=True, face_embedding__isnull=False).values_list(
            "id", "face_embedding"
        )
    )
    lost_candidates = list(
        LostPerson.objects.filter(is_active=True, face_embedding__isnull=False).values_list(
            "id", "face_embedding"
        )
    )

    found_matches = find_matches(embedding, found_candidates, threshold=settings.FACE_MATCH_THRESHOLD)
    lost_matches = find_matches(embedding, lost_candidates, threshold=settings.FACE_MATCH_THRESHOLD)

    MatchResult.objects.filter(search_query=query).delete()
    MatchResult.objects.bulk_create(
        [
            MatchResult(search_query=query, found_person_id=found_id, match_percentage=percentage)
            for found_id, percentage in found_matches
        ]
        + [
            MatchResult(search_query=query, lost_person_id=lost_id, match_percentage=percentage)
            for lost_id, percentage in lost_matches
        ]
    )

    query.is_processed = True
    query.save(update_fields=["is_processed"])
    total_matches = len(found_matches) + len(lost_matches)
    logger.info("Search query %s processed with %s match(es).", search_query_id, total_matches)
    return total_matches
