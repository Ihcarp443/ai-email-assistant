import os
import sys
from pathlib import Path
import pytest
from dotenv import load_dotenv
# Make the repo root importable (so `graph`, `config`, `agents`, `services` resolve)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv()

@pytest.fixture(scope="session", autouse=True)
def _check_env():
    missing = [
        var
        for var in ("HF_TOKEN", "GROQ_API_KEY")
        if not os.getenv(var)
    ]
    if missing:
        pytest.skip(
            f"Skipping eval suite: missing env vars {missing}. "
            f"Set them (e.g. in a .env loaded via `python-dotenv`) to run evals."
        )
