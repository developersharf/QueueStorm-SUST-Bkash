from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .classifier import classify
from .serializers import TicketRequestSerializer


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class SortTicketView(APIView):
    def post(self, request):
        serializer = TicketRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = classify(data["message"])
        payload = {"ticket_id": data["ticket_id"], **result}
        return Response(payload, status=status.HTTP_200_OK)


class DemoView(TemplateView):
    template_name = "tickets/demo.html"