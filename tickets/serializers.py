from rest_framework import serializers

CHANNEL_CHOICES = ["app", "sms", "call_center", "merchant_portal"]
LOCALE_CHOICES = ["bn", "en", "mixed"]


class TicketRequestSerializer(serializers.Serializer):
    ticket_id = serializers.CharField(required=True, max_length=64)
    channel = serializers.ChoiceField(choices=CHANNEL_CHOICES, required=False, allow_null=True)
    locale = serializers.ChoiceField(choices=LOCALE_CHOICES, required=False, allow_null=True)
    message = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)