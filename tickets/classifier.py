PHISHING_KEYWORDS = [
    "otp", "pin code", "pin number", "my pin", "password", "cvv",
    "card number", "asking for my", "share my code", "verify your account",
    "called asking", "texted asking", "is that bkash", "is this bkash",
    "claiming to be bkash", "fake call", "scam call",
]

WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "sent to wrong", "wrong account", "wrong recipient",
    "transferred to wrong", "sent money to wrong", "wrong person",
]

DEDUCTION_KEYWORDS = ["deducted", "money gone", "balance gone", "charged twice"]

PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "transaction failed", "failed but", "not completed",
    "stuck on", "pending forever", "transaction error",
]

REFUND_KEYWORDS = [
    "refund", "changed my mind", "money back", "return my payment", "cancel and refund",
]

DISPUTE_REFUND_KEYWORDS = ["unauthorized", "did not authorize", "i did not make this", "fraudulent charge"]


def _matches(text, keywords):
    return [k for k in keywords if k in text]


def classify(message: str) -> dict:
    text = message.lower()

    phishing_hits = _matches(text, PHISHING_KEYWORDS)
    if phishing_hits:
        return {
            "case_type": "phishing_or_social_engineering",
            "severity": "critical",
            "department": "fraud_risk",
            "human_review_required": True,
            "confidence": 0.9 if len(phishing_hits) > 1 else 0.8,
            "agent_summary": "Customer describes contact requesting sensitive account details, a likely phishing attempt.",
        }

    wrong_hits = _matches(text, WRONG_TRANSFER_KEYWORDS)
    if wrong_hits:
        return {
            "case_type": "wrong_transfer",
            "severity": "high",
            "department": "dispute_resolution",
            "human_review_required": False,
            "confidence": 0.9 if len(wrong_hits) > 1 else 0.8,
            "agent_summary": "Customer reports sending money to the wrong recipient and wants the funds recovered.",
        }

    payment_hits = _matches(text, PAYMENT_FAILED_KEYWORDS)
    deduction_hits = _matches(text, DEDUCTION_KEYWORDS)
    if payment_hits or deduction_hits:
        severity = "high" if deduction_hits else "medium"
        summary_tail = " with balance deducted." if deduction_hits else "."
        return {
            "case_type": "payment_failed",
            "severity": severity,
            "department": "payments_ops",
            "human_review_required": False,
            "confidence": 0.85 if deduction_hits else 0.75,
            "agent_summary": "Customer reports a failed transaction" + summary_tail,
        }

    refund_hits = _matches(text, REFUND_KEYWORDS)
    if refund_hits:
        dispute_hits = _matches(text, DISPUTE_REFUND_KEYWORDS)
        severity = "high" if dispute_hits else "low"
        department = "dispute_resolution" if dispute_hits else "customer_support"
        return {
            "case_type": "refund_request",
            "severity": severity,
            "department": department,
            "human_review_required": False,
            "confidence": 0.85 if dispute_hits else 0.75,
            "agent_summary": "Customer requests a refund for a recent transaction.",
        }

    return {
        "case_type": "other",
        "severity": "low",
        "department": "customer_support",
        "human_review_required": False,
        "confidence": 0.5,
        "agent_summary": "Customer reports a general issue not tied to a specific transaction.",
    }