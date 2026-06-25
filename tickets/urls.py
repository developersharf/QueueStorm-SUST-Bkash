from django.urls import path

from .views import DemoView, HealthView, SortTicketView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("sort-ticket", SortTicketView.as_view()),
    # Root URL serves the test/demo page. Routed at "" (not "/") because the
    # include() in ticketsort/urls.py strips the leading slash.
    path("", DemoView.as_view(), name="demo"),
    path("demo", DemoView.as_view(), name="demo-alt"),
]