from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEBSITE_DIR = PROJECT_ROOT / "office-orders-website"

if str(WEBSITE_DIR) not in sys.path:
    sys.path.insert(0, str(WEBSITE_DIR))

from rag_service import OfficeOrdersRAG  # noqa: E402


if __name__ == "__main__":
    rag = OfficeOrdersRAG()
    result = rag.ensure_index(force_rebuild=True)
    print(result)
