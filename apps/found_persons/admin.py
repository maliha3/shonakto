from django.contrib import admin

from .models import FoundPerson, LostPerson


@admin.register(FoundPerson)
class FoundPersonAdmin(admin.ModelAdmin):
    list_display = ["id", "condition", "status", "gender", "division", "uploaded_by", "is_active", "created_at", "expires_at"]
    list_filter = ["condition", "status", "gender", "division", "is_active"]
    search_fields = ["found_location", "description", "uploaded_by__email"]
    readonly_fields = ["id", "embedding_generated_at", "created_at"]


@admin.register(LostPerson)
class LostPersonAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "status", "gender", "division", "reported_by", "is_active", "created_at"]
    list_filter = ["status", "gender", "division", "is_active"]
    search_fields = ["full_name", "last_seen_location", "description", "reported_by__email"]
    readonly_fields = ["id", "embedding_generated_at", "created_at"]
