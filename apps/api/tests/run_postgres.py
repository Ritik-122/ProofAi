"""Run authentication tests in isolated schemas of the local test database."""
import json
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
credentials = json.loads((root / ".local/database-credentials.json").read_text())
env = os.environ.copy()
env["TEST_DATABASE_URL"] = f"postgresql+psycopg://proofai:{credentials['app']}@127.0.0.1:55432/proofai_test"
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", "--tb=short"], env=env))
