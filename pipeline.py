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


# API CALLS #

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


def get_timetables_by_subject(subject: str):
    try:
        url = WEBSITE_BASE_URL + f"/api/timetable?subject={subject}"
        response = requests.get(url)
        return response.json()
    except:
        return []


# MAIN PIPELINE #

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

        #  PATH FIX 
        filename = os.path.basename(pdf_path)
        web_pdf_path = f"/static/pdfs/{filename}"

        # PDF TEXT EXTRACTION
        raw_pdf_text = extract_pdf(pdf_path)

        if isinstance(raw_pdf_text, dict):
            cleaned_pdf_text = raw_pdf_text.get("text", "")
        else:
            cleaned_pdf_text = str(raw_pdf_text)

        cleaned_pdf_text = cleaned_pdf_text.strip()

        log(f"Extracted text length: {len(cleaned_pdf_text)}")

        if not cleaned_pdf_text:
            log("Empty PDF text, skipping")
            continue

        # RAG 
        rag = SimpleRAG()
        rag.build_index(cleaned_pdf_text)

        # STEP 1: TYPE DETECTION 
        type_context = rag.retrieve(
            "Identify whether this is a timetable or an office order"
        )

        doc_data = analyze_document(type_context)

        email_type = doc_data.get("document_type", "unknown")

        if email_type == "unknown":
            log("LLM failed → fallback to email classifier")
            email_type = classify_email(email)

        if not email_type or email_type == "unknown":
            log("Still unknown → forcing timetable")
            email_type = "timetable"

        log(f"Detected type: {email_type}")

        # OFFICE ORDER FLOW
        
        if email_type == "office_order":

            log("Processing office order")

            context = rag.retrieve(
                "Extract subject, category, subcategory, and release date from this office order"
            )

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
                res = create_office_order(payload)
                log(f"Office order created ID: {res.get('id')}")
            except Exception as e:
                log(f"Office order API failed: {e}")
                continue

        # TIMETABLE FLOW
        
        elif email_type == "timetable":

            log("Processing timetable")

            context = rag.retrieve(
                "Extract timetable title, semester (Winter/Monsoon/Summer), academic year, version type (new/revised), and release date"
            )

            doc_data = analyze_document(context)

            #EXTRACT 
            semester = doc_data.get("semester", "")
            academic_year = doc_data.get("academic_year", "")
            subject = doc_data.get("subject", "").strip()
            version_hint = doc_data.get("version_hint", "new")
            release_date = doc_data.get("release_date", "")

            # SMART SUBJECT 
            if not subject or subject.lower() in ["timetable", "course timetable"]:
                if semester and academic_year:
                    subject = f"{semester} Semester {academic_year} Timetable"
                else:
                    subject = "Timetable"

            # FALLBACKS 
            if not release_date:
                release_date = datetime.now().strftime("%Y-%m-%d")

            if not semester:
                semester = "Unknown"

            if not academic_year:
                academic_year = "unknown"

            # GROUP KEY 
            group_key = f"{semester}_{academic_year}".lower().replace(" ", "")

            # VERSION LOGIC 
            existing = get_timetables_by_subject(subject)

            if existing:
                version = max(item.get("version", 1) for item in existing) + 1
            else:
                version = 1

            # FINAL PAYLOAD
            payload = {
                "subject": subject,
                "semester": semester,
                "academic_year": academic_year,
                "group_key": group_key,
                "version": version,
                "version_hint": version_hint,
                "date": release_date,
                "file": web_pdf_path
            }

            log(f"Timetable payload: {payload}")

            try:
                res = create_timetable(payload)
                log(f"Timetable processed (v{res.get('version', version)})")
            except Exception as e:
                log(f"Timetable API failed: {e}")
                continue

        # UNKNOWN
        else:
            log("Unknown document type: skipped")

    log("Pipeline completed successfully")


# RUN #

if __name__ == "__main__":
    run_pipeline()