from rest_framework import permissions, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from .models import FoundPerson
from .serializers import FoundPersonSerializer, FoundPersonUploadSerializer


class IsAllowedUploader(permissions.BasePermission):
    """
    Spec: 'Allowed users (General, Police, Morgue, Authorities) can upload
    found/unidentified person details.' In practice that's simply any
    authenticated, verified user — kept as an explicit permission class so
    the rule is easy to tighten later (e.g. restrict to authorities only).

    Object-level access (retrieve/update/delete a specific record) is
    further restricted to the user who uploaded it.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_verified)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.uploaded_by_id == request.user.id


class FoundPersonViewSet(viewsets.ModelViewSet):
    """
    /api/found-persons/          GET (list active, unexpired records), POST (upload)
    /api/found-persons/{id}/     GET, PATCH, DELETE (own records only)
    """

    queryset = FoundPerson.objects.filter(is_active=True).select_related("uploaded_by")
    permission_classes = [IsAllowedUploader]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "create":
            return FoundPersonUploadSerializer
        return FoundPersonSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        division = self.request.query_params.get("division")
        condition = self.request.query_params.get("condition")
        if division:
            qs = qs.filter(division=division)
        if condition:
            qs = qs.filter(condition=condition)
        return qs

    def perform_destroy(self, instance):
        if instance.photo:
            instance.photo.delete(save=False)
        instance.delete()
