from django.urls import path

from .views import (
    CreateSearchQueryView,
    DashboardStatsView,
    DismissNotificationView,
    MarkNotificationReadView,
    MatchReviewView,
    MyNotificationsView,
    NotifyUploaderView,
    PendingMatchesView,
    SearchQueryResultView,
)

urlpatterns = [
    path("queries/", CreateSearchQueryView.as_view(), name="search-create"),
    path("queries/<uuid:pk>/", SearchQueryResultView.as_view(), name="search-result"),
    path("dashboard/", DashboardStatsView.as_view(), name="search-dashboard"),
    path("matches/pending/", PendingMatchesView.as_view(), name="search-matches-pending"),
    path("matches/<uuid:pk>/review/", MatchReviewView.as_view(), name="search-match-review"),
    path("matches/<uuid:pk>/notify-uploader/", NotifyUploaderView.as_view(), name="search-match-notify-uploader"),
    path("notifications/", MyNotificationsView.as_view(), name="search-notifications"),
    path("notifications/<uuid:pk>/read/", MarkNotificationReadView.as_view(), name="search-notification-read"),
    path("notifications/<uuid:pk>/", DismissNotificationView.as_view(), name="search-notification-dismiss"),
]
