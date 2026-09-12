from django.contrib import admin

from .models import MatchNotification, MatchResult, SearchQuery


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ["id", "requested_by", "is_processed", "created_at"]
    list_filter = ["is_processed"]


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ["id", "search_query", "found_person", "lost_person", "match_percentage", "status", "reviewed_by"]
    list_filter = ["status"]


@admin.register(MatchNotification)
class MatchNotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "match_result", "recipient", "is_read", "created_at"]
    list_filter = ["is_read"]
