"""
Create Firebase Auth users for testing. Run once, then run seed_data.py.
Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT (or have project_id in service account JSON).
Run from backend: python -m scripts.create_auth_users
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env from backend root so GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are set
_backend_root = Path(__file__).resolve().parent.parent
_env_file = _backend_root / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from firebase_admin import credentials, auth, initialize_app

def _project_id():
    pid = os.getenv("GOOGLE_CLOUD_PROJECT")
    if pid:
        return pid
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.isfile(cred_path):
        with open(cred_path) as f:
            return json.load(f).get("project_id")
    return None

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if cred_path:
    if not os.path.isfile(cred_path):
        sys.exit(
            f"Credentials file not found: {cred_path}\n"
            "In backend/.env set GOOGLE_APPLICATION_CREDENTIALS to the full path of your\n"
            "Firebase service account JSON (e.g. backend/serviceAccountKey.json).\n"
            "Download it from Firebase Console → Project settings → Service accounts."
        )
    cred = credentials.Certificate(cred_path)
else:
    cred = credentials.ApplicationDefault()

project_id = _project_id()
if not project_id:
    sys.exit(
        "Firebase needs a project ID. Set GOOGLE_CLOUD_PROJECT in .env (e.g. your-gcp-project-id)\n"
        "or use a service account JSON that contains project_id."
    )
options = {"projectId": project_id}
try:
    initialize_app(cred, options=options)
except Exception:
    pass

# Same emails as in seed_data - use a single test password for all
TEST_PASSWORD = "TestPass123!"

USERS = [
    "sarah@acme.example.com",
    "mike@acme.example.com",
    "lisa@acme.example.com",
    "alice@globex.example.com",
    "bob@globex.example.com",
]

def main():
    for email in USERS:
        try:
            user = auth.get_user_by_email(email)
            print(f"User exists: {email} ({user.uid})")
        except auth.UserNotFoundError:
            user = auth.create_user(email=email, password=TEST_PASSWORD, email_verified=True)
            print(f"Created: {email} ({user.uid})")
    print("Password for all: " + TEST_PASSWORD)


if __name__ == "__main__":
    main()
