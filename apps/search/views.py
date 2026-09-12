from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsLawEnforcement
from apps.found_persons.models import CaseStatus, FoundPerson

from .models import MatchNotification, MatchResult, ReviewStatus, SearchQuery
from .serializers import (
    DashboardStatsSerializer,
    MatchNotificationSerializer,
    MatchResultSerializer,
    MatchReviewActionSerializer,
    SearchQueryCreateSerializer,
    SearchQueryResultSerializer,
)
from .tasks import run_face_matching


class CreateSearchQueryView(APIView):
    """
    POST /api/search/queries/
    Upload the missing person's photo and immediately queue the AI face
    matching pipeline. Poll SearchQueryResultView for results.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SearchQueryCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        query = serializer.save()
        run_face_matching.delay(str(query.id))
        return Response(SearchQueryCreateSerializer(query).data, status=status.HTTP_201_CREATED)


class SearchQueryResultView(APIView):
    """
    GET /api/search/queries/{id}/
    Poll this after creating a query to fetch the match results once
    is_processed=True. Results are filtered server-side to > FACE_MATCH_THRESHOLD
    (default 50%) and include uploader contact details + authority badge.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        query = get_object_or_404(
            SearchQuery.objects.prefetch_related("matches__found_person__uploaded_by"),
            pk=pk,
            requested_by=request.user,
        )
        return Response(SearchQueryResultSerializer(query).data)


class DashboardStatsView(APIView):
    """
    GET /api/search/dashboard/
    Law-enforcement-only summary counts for the Inspector Dashboard.
    """

    permission_classes = [IsLawEnforcement]

    def get(self, request):
        today = timezone.now().date()
        active_qs = FoundPerson.objects.filter(is_active=True)
        data = {
            "active_cases": active_qs.count(),
            "matches_today": MatchResult.objects.filter(created_at__date=today).count(),
            "pending_alerts": MatchResult.objects.filter(status=ReviewStatus.PENDING).count(),
            "critical_count": active_qs.filter(status=CaseStatus.UNIDENTIFIED).count(),
            "medium_count": active_qs.filter(status=CaseStatus.UNDER_CARE).count(),
            "resolved_count": active_qs.filter(status=CaseStatus.REUNITED).count(),
        }
        return Response(DashboardStatsSerializer(data).data)


class PendingMatchesView(APIView):
    """
    GET /api/search/matches/pending/
    Cross-user list of pending AI match alerts for a law-enforcement
    reviewer to triage (unlike SearchQueryResultView, not scoped to the
    requesting user's own queries).
    """

    permission_classes = [IsLawEnforcement]

    def get(self, request):
        matches = (
            MatchResult.objects.filter(status=ReviewStatus.PENDING)
            .select_related("search_query", "found_person", "found_person__uploaded_by")
            .order_by("-match_percentage")
        )
        return Response(MatchResultSerializer(matches, many=True).data)


class MatchReviewView(APIView):
    """
    PATCH /api/search/matches/{id}/review/
    Body: {"action": "approve" | "reject"}. Approving a match also marks the
    matched FoundPerson record as reunited.
    """

    permission_classes = [IsLawEnforcement]

    def patch(self, request, pk):
        match = get_object_or_404(MatchResult, pk=pk)
        serializer = MatchReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        match.status = ReviewStatus.APPROVED if action == "approve" else ReviewStatus.REJECTED
        match.reviewed_by = request.user
        match.reviewed_at = timezone.now()
        match.save(update_fields=["status", "reviewed_by", "reviewed_at"])

        if action == "approve":
            match.found_person.status = CaseStatus.REUNITED
            match.found_person.save(update_fields=["status"])

        return Response(MatchResultSerializer(match).data)


class NotifyUploaderView(APIView):
    """
    POST /api/search/matches/{id}/notify-uploader/
    Lets the searcher who owns this match alert the found-person's uploader,
    with the searcher's contact details attached. Only the searcher who ran
    the query this match belongs to can trigger it, and only once per match.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        match = get_object_or_404(
            MatchResult.objects.select_related("search_query", "found_person__uploaded_by"), pk=pk
        )
        if match.search_query.requested_by_id != request.user.id:
            return Response({"detail": "Not your search result."}, status=403)

        notification, created = MatchNotification.objects.get_or_create(
            match_result=match, defaults={"recipient": match.found_person.uploaded_by}
        )
        return Response(
            {"created": created, "notification": MatchNotificationSerializer(notification).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyNotificationsView(APIView):
    """GET /api/search/notifications/ — the current user's own inbox (as an uploader)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = MatchNotification.objects.filter(recipient=request.user).select_related(
            "match_result__search_query__requested_by", "match_result__found_person"
        )
        return Response(MatchNotificationSerializer(notifications, many=True).data)


class MarkNotificationReadView(APIView):
    """PATCH /api/search/notifications/{id}/read/ — marks one of the current user's own notifications read."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(MatchNotification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(MatchNotificationSerializer(notification).data)


class DismissNotificationView(APIView):
    """DELETE /api/search/notifications/{id}/ — dismisses (deletes) one of the
    current user's own notifications. Does not touch the underlying match or
    found-person record — just clears it from the recipient's Alerts list."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        notification = get_object_or_404(MatchNotification, pk=pk, recipient=request.user)
        notification.delete()
        return Response(status=204)
