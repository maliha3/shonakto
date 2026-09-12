from rest_framework import serializers

from apps.found_persons.models import FoundPerson

from .models import MatchNotification, MatchResult, SearchQuery


class SearchQueryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ["id", "photo"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["requested_by"] = self.context["request"].user
        return super().create(validated_data)


class SearchQueryMiniSerializer(serializers.ModelSerializer):
    """Minimal SearchQuery info embedded in a MatchResult — just enough to
    render the "Query Photo" side of a match card without a second request."""

    class Meta:
        model = SearchQuery
        fields = ["id", "photo"]
        read_only_fields = fields


class FoundPersonMatchSerializer(serializers.ModelSerializer):
    """Used inside a MatchResult response — exposes the uploader's contact info
    per spec ('uploader contact details: Name, Phone, Email') plus the
    authority badge when applicable."""

    uploader_name = serializers.CharField(source="uploaded_by.name", read_only=True)
    uploader_phone = serializers.CharField(source="uploaded_by.phone_number", read_only=True)
    uploader_email = serializers.CharField(source="uploaded_by.email", read_only=True)
    uploader_badge = serializers.ReadOnlyField()

    class Meta:
        model = FoundPerson
        fields = [
            "id",
            "photo",
            "condition",
            "found_location",
            "division",
            "found_timestamp",
            "estimated_age",
            "gender",
            "distinguishing_marks",
            "uploader_name",
            "uploader_phone",
            "uploader_email",
            "uploader_badge",
        ]
        read_only_fields = fields


class MatchResultSerializer(serializers.ModelSerializer):
    found_person = FoundPersonMatchSerializer(read_only=True)
    search_query = SearchQueryMiniSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", read_only=True, default=None)
    uploader_notified = serializers.SerializerMethodField()

    class Meta:
        model = MatchResult
        fields = [
            "id",
            "search_query",
            "found_person",
            "match_percentage",
            "status",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "uploader_notified",
        ]
        read_only_fields = fields

    def get_uploader_notified(self, obj):
        return hasattr(obj, "notification")


class MatchNotificationSerializer(serializers.ModelSerializer):
    """A notification shown to the uploader: someone's search matched their
    found-person report, with the searcher's contact details attached."""

    searcher_name = serializers.CharField(source="match_result.search_query.requested_by.name", read_only=True)
    searcher_phone = serializers.CharField(
        source="match_result.search_query.requested_by.phone_number", read_only=True
    )
    searcher_email = serializers.CharField(source="match_result.search_query.requested_by.email", read_only=True)
    searcher_address = serializers.CharField(
        source="match_result.search_query.requested_by.address", read_only=True
    )
    query_photo = serializers.ImageField(source="match_result.search_query.photo", read_only=True)
    found_person_id = serializers.UUIDField(source="match_result.found_person_id", read_only=True)
    found_person_photo = serializers.ImageField(source="match_result.found_person.photo", read_only=True)
    found_person_location = serializers.CharField(source="match_result.found_person.found_location", read_only=True)
    match_percentage = serializers.FloatField(source="match_result.match_percentage", read_only=True)

    class Meta:
        model = MatchNotification
        fields = [
            "id",
            "searcher_name",
            "searcher_phone",
            "searcher_email",
            "searcher_address",
            "query_photo",
            "found_person_id",
            "found_person_photo",
            "found_person_location",
            "match_percentage",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


class SearchQueryResultSerializer(serializers.ModelSerializer):
    matches = MatchResultSerializer(many=True, read_only=True)

    class Meta:
        model = SearchQuery
        fields = ["id", "photo", "is_processed", "created_at", "matches"]
        read_only_fields = fields


class DashboardStatsSerializer(serializers.Serializer):
    active_cases = serializers.IntegerField()
    matches_today = serializers.IntegerField()
    pending_alerts = serializers.IntegerField()
    critical_count = serializers.IntegerField()
    medium_count = serializers.IntegerField()
    resolved_count = serializers.IntegerField()


class MatchReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
