"""
Create Firebase Auth users for testing. Run once, then run seed_data.py.
Set GOOGLE_APPLICATION_CREDENTIALS and run: python -m scripts.create_auth_users
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from firebase_admin import credentials, auth, initialize_app

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if cred_path and os.path.isfile(cred_path):
    cred = credentials.Certificate(cred_path)
else:
    cred = credentials.ApplicationDefault()
try:
    initialize_app(cred)
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
