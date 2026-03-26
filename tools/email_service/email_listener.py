# email_service/email_listener.py

import imaplib
import email
from email.header import decode_header
import os

from config import PDF_STORAGE_PATH


EMAIL_ACCOUNT = "webupdateragent@gmail.com"
EMAIL_PASSWORD = "stnz inlj tsjk wmhw"
IMAP_SERVER = "imap.gmail.com"


def fetch_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()

    if not email_ids:
        print("[EMAIL] No new emails")
        return None

    latest_email_id = email_ids[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")

    from_email = msg.get("From")
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()

            if content_type == "text/plain" and not filename:
                body = part.get_payload(decode=True).decode(errors="ignore")

            if filename and filename.lower().endswith(".pdf"):
                os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
                file_path = os.path.join(PDF_STORAGE_PATH, filename)

                with open(file_path, "wb") as f:
                    f.write(part.get_payload(decode=True))

                attachments.append({
                    "filename": filename,
                    "path": file_path
                })

    mail.store(latest_email_id, "+FLAGS", "\\Seen")
    mail.logout()

    print("[EMAIL] New email fetched")

    return {
        "from": from_email,
        "subject": subject or "",
        "body": body or "",
        "attachments": attachments
    }
