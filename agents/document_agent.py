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

You are given CONTEXT extracted from an official academic document using retrieval.

Your job is to extract structured information accurately.

------------------------
TASKS:

1. Identify document_type:
   - "office_order"
   - "timetable"

2. Extract SUBJECT (VERY IMPORTANT):
   - Must be CLEAN and CONSISTENT
   - Remove words like: Draft, Version, Final Copy, Circulation
   - Normalize similar phrases:
        "Course Schedule" → "Course Timetable"
   - Keep only core academic meaning

   Example:
   "Final TT Winter 2026 circulation Draft 5"
   "Winter Semester 2026 (AY 2025-26) Course Timetable"

3. Extract release_date:
   - Format: YYYY-MM-DD
   - If not found, return ""

4. If document_type = "office_order":
   - Extract category
   - Extract subcategory

------------------------
STRICT RULES:

- Return ONLY valid JSON
- No explanation
- No markdown
- Do NOT hallucinate
- If unsure → use ""

------------------------
OUTPUT FORMAT:

{
  "document_type": "",
  "subject": "",
  "category": "",
  "subcategory": "",
  "release_date": ""
}

------------------------
CONTEXT:
{context}
"""
# MAIN FUNCTION

def analyze_document(pdf_text) -> dict:
    """
    Universal document analysis (office order + timetable)
    """

    # Handle OCR or raw text
    if isinstance(pdf_text, dict):
        text_content = pdf_text.get("text", "")
    else:
        text_content = str(pdf_text)

    text_content = text_content.strip()
    text_content = text_content[:12000]

    # LLM CALL
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


    # POST-PROCESSING

    result.setdefault("document_type", "unknown")
    result.setdefault("subject", "")
    result.setdefault("category", "")
    result.setdefault("subcategory", "")
    result.setdefault("release_date", "")

    # Clean subject
    if result["subject"]:
        result["subject"] = (
            result["subject"]
            .replace("Re:", "")
            .replace("Fwd:", "")
            .strip()
        )

    return result