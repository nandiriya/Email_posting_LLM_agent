# config.py
import os

# NVIDIA QWEN LLM CONFIG
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

NVIDIA_API_BASE = os.getenv(
    "NVIDIA_API_BASE",
    "https://integrate.api.nvidia.com/v1"
)

NVIDIA_MODEL = os.getenv(
    "NVIDIA_MODEL",
    "qwen/qwen3-next-80b-a3b-instruct"
)

if not NVIDIA_API_KEY:
    raise EnvironmentError("NVIDIA_API_KEY not set")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 800))

# EMAIL CONFIGURATION

TARGET_EMAIL = os.getenv(
    "TARGET_EMAIL",
    "webupdateragent@gmail.com"
)

IMAP_SERVER = os.getenv(
    "IMAP_SERVER",
    "imap.gmail.com"
)

IMAP_PORT = int(os.getenv("IMAP_PORT", 993))



# FILE & STORAGE PATHS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PDF_STORAGE_PATH = os.path.join(
    BASE_DIR,
    "office-orders-website",
    "static",
    "pdfs"
)

EMAIL_DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "incoming_emails"
)


# WEBSITE CONFIGURATION

WEBSITE_BASE_URL = os.getenv(
    "WEBSITE_BASE_URL",
    "http://127.0.0.1:5000"
)

CREATE_ORDER_ENDPOINT = "/api/office-orders"
UPDATE_ORDER_ENDPOINT = "/api/office-orders/update"
DELETE_ORDER_ENDPOINT = "/api/office-orders/delete"


# DEBUG / LOGGING

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
