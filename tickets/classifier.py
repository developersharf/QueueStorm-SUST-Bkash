import re

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

_FORBIDDEN_TOKENS = ("pin", "otp", "password", "cvv", "card number")
_AMOUNT_RE = re.compile(
    r"\b(\d{1,9}(?:[.,]\d{1,2})?)\s*(bdt|taka|tk|৳|usd|\$)?\b",
    re.IGNORECASE,
)


def _matches(text, keywords):
    return [k for k in keywords if k in text]


def _extract_amount(message: str) -> str | None:
    match = _AMOUNT_RE.search(message)
    if not match:
        return None
    amount = match.group(1).replace(",", "")
    currency = match.group(2)
    if currency:
        currency_norm = {"taka": "BDT", "tk": "BDT", "৳": "BDT", "$": "USD"}
        currency = currency_norm.get(currency.lower(), currency.upper())
    else:
        currency = "BDT"
    return f"{amount} {currency}"


def _safe_summary(template: str, message: str, fallback: str) -> str:
    amount = _extract_amount(message)
    rendered = template.format(amount=amount) if amount else fallback
    lowered = rendered.lower()
    if any(token in lowered for token in _FORBIDDEN_TOKENS):
        return fallback
    return rendered


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
            "agent_summary": "Customer describes a contact requesting sensitive account details, indicating a likely phishing or social engineering attempt.",
        }

    wrong_hits = _matches(text, WRONG_TRANSFER_KEYWORDS)
    if wrong_hits:
        summary = _safe_summary(
            "Customer reports sending {amount} to a wrong recipient and requests recovery.",
            message,
            "Customer reports sending money to a wrong recipient and requests recovery.",
        )
        return {
            "case_type": "wrong_transfer",
            "severity": "high",
            "department": "dispute_resolution",
            "human_review_required": False,
            "confidence": 0.9 if len(wrong_hits) > 1 else 0.8,
            "agent_summary": summary,
        }

    payment_hits = _matches(text, PAYMENT_FAILED_KEYWORDS)
    deduction_hits = _matches(text, DEDUCTION_KEYWORDS)
    if payment_hits or deduction_hits:
        severity = "high" if deduction_hits else "medium"
        if deduction_hits:
            amount = _extract_amount(message)
            if amount:
                summary = f"Customer reports a failed transaction of {amount} with the balance already deducted."
            else:
                summary = "Customer reports a failed transaction with the balance already deducted."
        else:
            amount = _extract_amount(message)
            if amount:
                summary = f"Customer reports a failed transaction of {amount} that did not complete."
            else:
                summary = "Customer reports a failed transaction that did not complete."
        lowered = summary.lower()
        if any(token in lowered for token in _FORBIDDEN_TOKENS):
            summary = "Customer reports a failed transaction."
        return {
            "case_type": "payment_failed",
            "severity": severity,
            "department": "payments_ops",
            "human_review_required": False,
            "confidence": 0.85 if deduction_hits else 0.75,
            "agent_summary": summary,
        }

    refund_hits = _matches(text, REFUND_KEYWORDS)
    if refund_hits:
        dispute_hits = _matches(text, DISPUTE_REFUND_KEYWORDS)
        severity = "high" if dispute_hits else "low"
        department = "dispute_resolution" if dispute_hits else "customer_support"
        if dispute_hits:
            summary = "Customer reports an unauthorized charge and requests a refund for the disputed transaction."
        else:
            amount = _extract_amount(message)
            if amount:
                summary = f"Customer requests a refund of {amount} for a recent transaction."
            else:
                summary = "Customer requests a refund for a recent transaction."
        lowered = summary.lower()
        if any(token in lowered for token in _FORBIDDEN_TOKENS):
            summary = "Customer requests a refund for a recent transaction."
        return {
            "case_type": "refund_request",
            "severity": severity,
            "department": department,
            "human_review_required": False,
            "confidence": 0.85 if dispute_hits else 0.75,
            "agent_summary": summary,
        }

    return {
        "case_type": "other",
        "severity": "low",
        "department": "customer_support",
        "human_review_required": False,
        "confidence": 0.5,
        "agent_summary": "Customer reports a general issue that does not map to a specific transaction case.",
    }