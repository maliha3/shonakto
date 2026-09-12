import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def run_face_matching(search_query_id):
    """
    Triggered right after a search query is uploaded. Generates an embedding
    for the uploaded missing-person photo, compares it against every active
    FoundPerson record's embedding via cosine similarity, and stores any hit
    above settings.FACE_MATCH_THRESHOLD (default 50%) as a MatchResult.
    """
    from apps.found_persons.models import FoundPerson
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

    candidates = (
        FoundPerson.objects.filter(is_active=True, face_embedding__isnull=False)
        .select_related("uploaded_by")
        .values_list("id", "face_embedding")
    )
    candidate_pairs = [(found_id, emb) for found_id, emb in candidates]

    matches = find_matches(embedding, candidate_pairs, threshold=settings.FACE_MATCH_THRESHOLD)

    MatchResult.objects.filter(search_query=query).delete()
    MatchResult.objects.bulk_create(
        [
            MatchResult(search_query=query, found_person_id=found_id, match_percentage=percentage)
            for found_id, percentage in matches
        ]
    )

    query.is_processed = True
    query.save(update_fields=["is_processed"])
    logger.info("Search query %s processed with %s match(es).", search_query_id, len(matches))
    return len(matches)
