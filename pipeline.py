# pipeline.py

import requests  # type: ignore
import os
from datetime import datetime

from tools.email_service.email_listener import fetch_email
from tools.email_service.email_classifier import classify_email
from tools.pdf_service.pdf_parser import extract_pdf
from tools.rag.retriever import SimpleRAG
from agents.document_agent import analyze_document

from config import (
    WEBSITE_BASE_URL,
    CREATE_ORDER_ENDPOINT,
    DEBUG_MODE
)


def log(message: str):
    if DEBUG_MODE:
        print(f"[PIPELINE] {message}")


# API CALLS 

def create_office_order(payload: dict):
    url = WEBSITE_BASE_URL + CREATE_ORDER_ENDPOINT
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def create_timetable(payload: dict):
    url = WEBSITE_BASE_URL + "/api/timetable"
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


# ---------------- MAIN PIPELINE ----------------

def run_pipeline():
    log("Pipeline started")

    email = fetch_email()
    if email is None:
        log("No new email")
        return

    log("Email fetched")

    attachments = email.get("attachments", [])
    if not attachments:
        log("No attachment found")
        return

    for attachment in attachments:

        pdf_path = attachment["path"]

        if not os.path.exists(pdf_path):
            log(f"PDF not found: {pdf_path}")
            continue

        log(f"Processing PDF: {pdf_path}")

        # Convert to web path
        filename = os.path.basename(pdf_path)
        web_pdf_path = f"/static/pdfs/{filename}"

        # PDF TEXT
        raw_pdf_text = extract_pdf(pdf_path)
        cleaned_pdf_text = raw_pdf_text.get("text", "")
        # RAG BUILD
        rag = SimpleRAG()
        rag.build_index(cleaned_pdf_text)

        # FIRST PASS (TYPE DETECTION) 
        context = rag.retrieve("Identify whether this is a timetable or an office order")
        doc_data = analyze_document(context)

        email_type = doc_data.get("document_type", "unknown")

        if email_type == "unknown":
            email_type = classify_email(email)
            log("Fallback to email classification")

        log(f"Final detected type: {email_type}")

        # OFFICE ORDER
        if email_type == "office_order":

            log("Processing office order")

            context = rag.retrieve("Extract subject, category, subcategory, and release date")

            doc_data = analyze_document(context)

            subject = doc_data.get("subject", "")
            category = doc_data.get("category", "")
            subcategory = doc_data.get("subcategory", "")
            release_date = doc_data.get("release_date", "")

            payload = {
                "subject": subject,
                "category": category,
                "subcategory": subcategory,
                "content": cleaned_pdf_text,
                "release_date": release_date,
                "effective_from": "",
                "effective_to": "",
                "pdf_path": web_pdf_path
            }

            log(f"Office order payload: {payload}")

            try:
                response = create_office_order(payload)
                log(f"Office order created ID: {response.get('id')}")
            except Exception as e:
                log(f"Office order API failed: {e}")
                continue

        # TIMETABLE 
        elif email_type == "timetable":

            log("Processing timetable")

            context = rag.retrieve(
                "Find the main title of the timetable, semester, academic year, and official heading"
)
            

            doc_data = analyze_document(context)

            subject = doc_data.get("subject", "").strip()

            # fallback
            if not subject:
                subject = "Timetable"

            # normalize (IMPORTANT for versioning)
            subject = subject.replace("Course Schedule", "Course Timetable").strip()

            formatted_date = doc_data.get("release_date")

            if not formatted_date:
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            payload = {
                "subject": subject,
                "date": formatted_date,
                "file": web_pdf_path
            }

            log(f"Timetable payload: {payload}")

            try:
                res = create_timetable(payload)
                log(f"Timetable added successfully (v{res.get('version')})")
            except Exception as e:
                log(f"Timetable API failed: {e}")
                continue

        else:
            log("Unknown document type → skipped")

    log("Pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()