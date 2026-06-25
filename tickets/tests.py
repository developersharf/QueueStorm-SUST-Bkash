from django.test import TestCase
from rest_framework.test import APIClient


class TicketSorterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def _post(self, message):
        return self.client.post("/sort-ticket", {"ticket_id": "T-TEST", "message": message}, format="json")

    def test_wrong_transfer(self):
        body = self._post("I sent 3000 to wrong number").json()
        self.assertEqual(body["case_type"], "wrong_transfer")
        self.assertEqual(body["severity"], "high")

    def test_payment_failed(self):
        body = self._post("Payment failed but balance deducted").json()
        self.assertEqual(body["case_type"], "payment_failed")
        self.assertEqual(body["severity"], "high")

    def test_phishing(self):
        body = self._post("Someone called asking my OTP, is that bKash?").json()
        self.assertEqual(body["case_type"], "phishing_or_social_engineering")
        self.assertEqual(body["severity"], "critical")
        self.assertTrue(body["human_review_required"])

    def test_refund(self):
        body = self._post("Please refund my last transaction, I changed my mind").json()
        self.assertEqual(body["case_type"], "refund_request")
        self.assertEqual(body["severity"], "low")

    def test_other(self):
        body = self._post("App crashed when I opened it").json()
        self.assertEqual(body["case_type"], "other")
        self.assertEqual(body["severity"], "low")