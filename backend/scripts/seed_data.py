"""
Seed Firestore with organizations, users (Firestore docs only; create Auth users in Firebase Console or Admin SDK),
rooms, and sample messages. Run after creating Firebase Auth users via scripts.create_auth_users.

Usage:
  Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT in backend/.env, then:
  python -m scripts.seed_data
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env from backend root
_backend_root = Path(__file__).resolve().parent.parent
_env_file = _backend_root / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from firebase_admin import credentials, firestore, auth, initialize_app


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
            "Firebase service account JSON (e.g. backend/service-account.json)."
        )
    cred = credentials.Certificate(cred_path)
else:
    cred = credentials.ApplicationDefault()

project_id = _project_id()
if not project_id:
    sys.exit(
        "Firebase needs a project ID. Set GOOGLE_CLOUD_PROJECT in backend/.env\n"
        "or use a service account JSON that contains project_id."
    )

try:
    initialize_app(cred, options={"projectId": project_id})
except Exception:
    pass  # already initialized

db = firestore.client()

ORGANIZATIONS = [
    {"slug": "acme-corp", "name": "Acme Corp"},
    {"slug": "globex", "name": "Globex Inc"},
]

# Map: org slug -> list of { email, password, display_name, role }
USERS = {
    "acme-corp": [
        {"email": "sarah@acme.example.com", "display_name": "Sarah", "role": "admin"},
        {"email": "mike@acme.example.com", "display_name": "Mike", "role": "member"},
        {"email": "lisa@acme.example.com", "display_name": "Lisa", "role": "member"},
    ],
    "globex": [
        {"email": "alice@globex.example.com", "display_name": "Alice", "role": "admin"},
        {"email": "bob@globex.example.com", "display_name": "Bob", "role": "member"},
    ],
}

# Predefined rooms and sample messages (org_slug -> list of rooms with optional messages)
ROOMS_DATA = {
    "acme-corp": [
        {
            "name": "general",
            "description": "General discussion",
            "member_emails": ["sarah@acme.example.com", "mike@acme.example.com", "lisa@acme.example.com"],
            "messages": [
                ("sarah@acme.example.com", "Sarah", "We need to decide on the caching strategy for our API"),
                ("mike@acme.example.com", "Mike", "I'm thinking Redis, but worried about costs at scale"),
                ("lisa@acme.example.com", "Lisa", "We're already on GCP, should we consider Memorystore?"),
            ],
        },
        {
            "name": "engineering",
            "description": "Engineering team",
            "member_emails": ["sarah@acme.example.com", "mike@acme.example.com", "lisa@acme.example.com"],
            "messages": [],
        },
        {
            "name": "design",
            "description": "Design",
            "member_emails": ["sarah@acme.example.com", "lisa@acme.example.com"],
            "messages": [],
        },
    ],
    "globex": [
        {
            "name": "general",
            "description": "Globex general",
            "member_emails": ["alice@globex.example.com", "bob@globex.example.com"],
            "messages": [],
        },
    ],
}


def get_uid_by_email(email: str) -> str | None:
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except Exception:
        return None


def main():
    # 1. Create organizations (use fixed IDs for predictable references)
    org_ids = {}
    for o in ORGANIZATIONS:
        doc_id = o["slug"].replace("-", "_")  # acme_corp, globex
        ref = db.collection("organizations").document(doc_id)
        ref.set({"slug": o["slug"], "name": o["name"], "createdAt": datetime.now(timezone.utc)})
        org_ids[o["slug"]] = ref.id
        print(f"Created org {o['slug']} -> {ref.id}")

    # 2. Create user docs (must have Firebase Auth users first)
    email_to_uid = {}
    for slug, users in USERS.items():
        org_id = org_ids[slug]
        for u in users:
            email = u["email"]
            uid = get_uid_by_email(email)
            if not uid:
                print(f"  Skip user doc for {email}: no Firebase Auth user. Create user in Firebase Console first.")
                continue
            email_to_uid[email] = uid
            db.collection("users").document(uid).set({
                "email": email,
                "displayName": u["display_name"],
                "orgId": org_id,
                "role": u["role"],
            })
            print(f"  User doc: {email} -> {uid}")

    # 3. Create rooms and messages
    for slug, rooms in ROOMS_DATA.items():
        org_id = org_ids[slug]
        for r in rooms:
            member_ids = []
            for em in r["member_emails"]:
                uid = email_to_uid.get(em)
                if uid:
                    member_ids.append(uid)
            if not member_ids:
                member_ids = ["placeholder"]  # replace when users exist
            room_ref = db.collection("rooms").document()
            room_ref.set({
                "orgId": org_id,
                "name": r["name"],
                "description": r.get("description", ""),
                "memberIds": member_ids,
                "createdAt": datetime.now(timezone.utc),
            })
            print(f"  Room: {r['name']} -> {room_ref.id}")
            for i, (email, sender_name, content) in enumerate(r.get("messages", [])):
                uid = email_to_uid.get(email) or "gemini-ai"
                if uid == "gemini-ai" and sender_name != "Gemini AI":
                    continue
                room_ref.collection("messages").add({
                    "senderId": uid,
                    "senderName": sender_name,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc),
                    "type": "user",
                })
    print("Seed done. Create Firebase Auth users (email/password) for the emails above if not already present.")


if __name__ == "__main__":
    main()
