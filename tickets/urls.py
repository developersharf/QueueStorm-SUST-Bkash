from django.urls import path

from .views import DemoView, HealthView, SortTicketView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("sort-ticket", SortTicketView.as_view()),
    path("demo", DemoView.as_view()),
]