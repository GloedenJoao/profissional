from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal, init_db  # noqa: E402
from app.services.catalog_service import ensure_seed_catalog  # noqa: E402


if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        ensure_seed_catalog(db)
    print("Database initialized with seed strategy catalog.")
