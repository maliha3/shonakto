from rest_framework import serializers

from apps.found_persons.models import FoundPerson, LostPerson

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


class LostPersonMatchSerializer(serializers.ModelSerializer):
    """Lost-person counterpart to FoundPersonMatchSerializer — exposes the
    reporter's contact info the same way, for a query photo that matches an
    existing missing-person report instead of a found-person record."""

    uploader_name = serializers.CharField(source="reported_by.name", read_only=True)
    uploader_phone = serializers.CharField(source="reported_by.phone_number", read_only=True)
    uploader_email = serializers.CharField(source="reported_by.email", read_only=True)
    uploader_badge = serializers.ReadOnlyField(source="reporter_badge")

    class Meta:
        model = LostPerson
        fields = [
            "id",
            "photo",
            "full_name",
            "last_seen_location",
            "division",
            "last_seen_timestamp",
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
    lost_person = LostPersonMatchSerializer(read_only=True)
    search_query = SearchQueryMiniSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", read_only=True, default=None)
    uploader_notified = serializers.SerializerMethodField()
    matched_type = serializers.SerializerMethodField()

    class Meta:
        model = MatchResult
        fields = [
            "id",
            "search_query",
            "found_person",
            "lost_person",
            "matched_type",
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

    def get_matched_type(self, obj):
        return "found" if obj.found_person_id else "lost"


class MatchNotificationSerializer(serializers.ModelSerializer):
    """A notification shown to the recipient: someone's search matched their
    found-person report OR their lost-person report, with the searcher's
    contact details attached. matched_person_* fields describe whichever of
    the two records this notification is actually about."""

    searcher_name = serializers.CharField(source="match_result.search_query.requested_by.name", read_only=True)
    searcher_phone = serializers.CharField(
        source="match_result.search_query.requested_by.phone_number", read_only=True
    )
    searcher_email = serializers.CharField(source="match_result.search_query.requested_by.email", read_only=True)
    searcher_address = serializers.CharField(
        source="match_result.search_query.requested_by.address", read_only=True
    )
    query_photo = serializers.ImageField(source="match_result.search_query.photo", read_only=True)
    matched_person_type = serializers.SerializerMethodField()
    matched_person_id = serializers.SerializerMethodField()
    matched_person_photo = serializers.SerializerMethodField()
    matched_person_location = serializers.SerializerMethodField()
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
            "matched_person_type",
            "matched_person_id",
            "matched_person_photo",
            "matched_person_location",
            "match_percentage",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields

    def get_matched_person_type(self, obj):
        return "found" if obj.match_result.found_person_id else "lost"

    def get_matched_person_id(self, obj):
        return str(obj.match_result.found_person_id or obj.match_result.lost_person_id)

    def get_matched_person_photo(self, obj):
        target = obj.match_result.matched_person
        if not target or not target.photo:
            return None
        url = target.photo.url
        request = self.context.get("request")
        if request is not None and url and not url.startswith("http"):
            return request.build_absolute_uri(url)
        return url

    def get_matched_person_location(self, obj):
        found_person = obj.match_result.found_person
        if found_person is not None:
            return found_person.found_location
        lost_person = obj.match_result.lost_person
        return lost_person.last_seen_location if lost_person is not None else None


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
