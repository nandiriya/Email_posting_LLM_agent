# email_service/office_order_detector.py

KEYWORDS = [
    "office order",
    "notification",
    "circular",
    "memorandum",
    "order"
]


def is_office_order(email: dict) -> bool:
    """
    Rule-based office order detection
    """

    text = f"{email.get('subject', '')} {email.get('body', '')}".lower()

    for keyword in KEYWORDS:
        if keyword in text:
            return True

    # If PDF attachment exists → assume office order
    for attachment in email.get("attachments", []):
        if attachment["filename"].lower().endswith(".pdf"):
            return True

    return False
