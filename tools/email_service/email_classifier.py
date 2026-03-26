def classify_email(email):
    """
    Classifies email into:
    - office_order
    - timetable
    - unknown
    """

    text = (email.get("subject", "") + " " + email.get("body", "")).lower()

    # Timetable detection
    if any(k in text for k in [
        "timetable",
        "time table",
        "tt",
        "exam schedule",
        "schedule"
    ]):
        return "timetable"

    # Office order detection
    if any(k in text for k in [
        "office order",
        "order",
        "notification",
        "memorandum"
    ]):
        return "office_order"

    return "unknown"