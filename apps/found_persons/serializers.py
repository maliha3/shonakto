from rest_framework import serializers

from .models import FoundPerson


class FoundPersonUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoundPerson
        fields = [
            "id",
            "photo",
            "condition",
            "found_location",
            "division",
            "found_timestamp",
            "description",
            "estimated_age",
            "gender",
            "distinguishing_marks",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        instance = super().create(validated_data)

        # Generate + store the facial embedding right after upload so it's
        # ready to be compared against future search queries.
        from .tasks import generate_embedding_for_found_person

        generate_embedding_for_found_person.delay(str(instance.id))
        return instance


class FoundPersonSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.UUIDField(source="uploaded_by_id", read_only=True)
    uploader_name = serializers.CharField(source="uploaded_by.name", read_only=True)
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
            "description",
            "estimated_age",
            "gender",
            "distinguishing_marks",
            "status",
            "uploaded_by",
            "uploader_name",
            "uploader_badge",
            "is_active",
            "created_at",
            "expires_at",
        ]
        read_only_fields = fields
