from django.contrib import admin

from .models import FoundPerson


@admin.register(FoundPerson)
class FoundPersonAdmin(admin.ModelAdmin):
    list_display = ["id", "condition", "status", "gender", "division", "uploaded_by", "is_active", "created_at", "expires_at"]
    list_filter = ["condition", "status", "gender", "division", "is_active"]
    search_fields = ["found_location", "description", "uploaded_by__email"]
    readonly_fields = ["id", "embedding_generated_at", "created_at"]
