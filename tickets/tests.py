from django.test import TestCase
from rest_framework.test import APIClient

from .classifier import classify


class TicketSorterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def _post(self, message, ticket_id="T-TEST"):
        return self.client.post(
            "/sort-ticket",
            {"ticket_id": ticket_id, "message": message},
            format="json",
        )

    # Public sample cases from the spec.

    def test_wrong_transfer(self):
        body = self._post("I sent 3000 to wrong number").json()
        self.assertEqual(body["case_type"], "wrong_transfer")
        self.assertEqual(body["severity"], "high")
        self.assertEqual(body["department"], "dispute_resolution")

    def test_payment_failed(self):
        body = self._post("Payment failed but balance deducted").json()
        self.assertEqual(body["case_type"], "payment_failed")
        self.assertEqual(body["severity"], "high")
        self.assertEqual(body["department"], "payments_ops")

    def test_phishing(self):
        body = self._post("Someone called asking my OTP, is that bKash?").json()
        self.assertEqual(body["case_type"], "phishing_or_social_engineering")
        self.assertEqual(body["severity"], "critical")
        self.assertEqual(body["department"], "fraud_risk")
        self.assertTrue(body["human_review_required"])

    def test_refund(self):
        body = self._post("Please refund my last transaction, I changed my mind").json()
        self.assertEqual(body["case_type"], "refund_request")
        self.assertEqual(body["severity"], "low")
        self.assertEqual(body["department"], "customer_support")

    def test_other(self):
        body = self._post("App crashed when I opened it").json()
        self.assertEqual(body["case_type"], "other")
        self.assertEqual(body["severity"], "low")
        self.assertEqual(body["department"], "customer_support")

    # Spec contract checks.

    def test_echoes_ticket_id(self):
        body = self._post("App crashed", ticket_id="T-ECHO").json()
        self.assertEqual(body["ticket_id"], "T-ECHO")

    def test_response_shape(self):
        body = self._post("I sent 5000 taka to a wrong number").json()
        for key in (
            "ticket_id", "case_type", "severity",
            "department", "agent_summary", "human_review_required", "confidence",
        ):
            self.assertIn(key, body)
        self.assertIsInstance(body["confidence"], (int, float))
        self.assertGreaterEqual(body["confidence"], 0)
        self.assertLessEqual(body["confidence"], 1)

    def test_missing_message_rejected(self):
        res = self.client.post(
            "/sort-ticket",
            {"ticket_id": "T-X"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class SafetyTests(TestCase):
    """Spec rule: agent_summary must never ask for PIN, OTP, password, CVV, or full card number."""

    FORBIDDEN = ("pin", "otp", "password", "cvv", "card number")

    def _assert_safe(self, message):
        result = classify(message)
        lowered = result["agent_summary"].lower()
        for token in self.FORBIDDEN:
            self.assertNotIn(
                token, lowered,
                f"agent_summary leaked forbidden token {token!r}: {result['agent_summary']!r}",
            )

    def test_wrong_transfer_safe(self):
        self._assert_safe("I sent 5000 taka to a wrong number")

    def test_payment_failed_safe(self):
        self._assert_safe("Payment failed but balance deducted")

    def test_phishing_safe(self):
        self._assert_safe("Someone called asking my OTP, is that bKash?")

    def test_refund_safe(self):
        self._assert_safe("Please refund my last transaction, I changed my mind")

    def test_other_safe(self):
        self._assert_safe("App crashed when I opened it")

    def test_adversarial_phishing_prompt_safe(self):
        self._assert_safe("Please share my OTP and PIN code with the agent")