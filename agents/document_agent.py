# agents/document_agent.py

import json
from openai import OpenAI
from config import (
    NVIDIA_API_KEY,
    NVIDIA_API_BASE,
    NVIDIA_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS
)

client = OpenAI(
    base_url=NVIDIA_API_BASE,
    api_key=NVIDIA_API_KEY
)

# SYSTEM PROMPT

SYSTEM_PROMPT = """
You are an expert university administrative assistant.

You are given CONTEXT extracted from an official academic document.

TASKS:

1. Identify document_type:
   - "office_order"
   - "timetable"

2. Extract SUBJECT (VERY IMPORTANT):
   - Must be CLEAN and CONSISTENT
   - Remove words like: Draft, Version, Final Copy
   - Normalize:
        "Course Schedule" → "Course Timetable"

3. Extract release_date:
   - Format: YYYY-MM-DD
   - If not found, return ""

4. IF document_type = "office_order":

CATEGORY (STRICT):
You MUST choose ONLY ONE from:
[
  "Academic",
  "Faculty Matters",
  "Finance & Accounts",
  "HR",
  "Institute",
  "IRD",
  "Stores & Purchase",
  "Student Affairs"
]

If unsure → choose "Institute"

SUBCATEGORY:
- Generate a short meaningful label (2–4 words)

5. IF document_type = "timetable":

Extract the following:

- semester:
    Must be one of:
    ["Winter", "Monsoon", "Summer"]

- academic_year:
    Example formats:
    "2025-26", "2024-25"

- version_hint:
    Identify if document is:
    - "new"
    - "revised"
    - "old"

Rules:
- If words like "revised", "updated", "final" → "revised"
- If clearly first version → "new"
- If outdated → "old"

RULES:

- Return ONLY valid JSON
- No explanation
- No markdown
- Do NOT hallucinate

OUTPUT:

{
  "document_type": "",
  "subject": "",
  "category": "",
  "subcategory": "",
  "release_date": "",
  "semester": "",
  "academic_year": "",
  "version_hint": ""
}

----------------------------------------
CONTEXT:
{context}
"""

# MAIN FUNCTION

def analyze_document(pdf_text) -> dict:
    """
    Universal document analysis (office order + timetable)
    """

    if isinstance(pdf_text, dict):
        text_content = pdf_text.get("text", "")
    else:
        text_content = str(pdf_text)

    text_content = text_content.strip()[:12000]

    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text_content}
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS
    )

    content = response.choices[0].message.content.strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from LLM:\n{content}")

    # ---------------- POST-PROCESSING ---------------- #

    result.setdefault("document_type", "unknown")
    result.setdefault("subject", "")
    result.setdefault("category", "")
    result.setdefault("subcategory", "")
    result.setdefault("release_date", "")

    # NEW FIELDS (IMPORTANT)
    result.setdefault("semester", "")
    result.setdefault("academic_year", "")
    result.setdefault("version_hint", "new")

    # Clean subject
    if result["subject"]:
        result["subject"] = (
            result["subject"]
            .replace("Re:", "")
            .replace("Fwd:", "")
            .replace("Draft", "")
            .replace("Final", "")
            .strip()
        )

    # Normalize semester
    if result["semester"]:
        result["semester"] = result["semester"].capitalize()

    # Normalize version
    if result["version_hint"] not in ["new", "revised", "old"]:
        result["version_hint"] = "new"

    return result

