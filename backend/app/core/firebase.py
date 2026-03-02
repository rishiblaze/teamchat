import os
import json
import base64
from firebase_admin import credentials, firestore, initialize_app

_db = None
_initialized = False


def init_firebase() -> None:
    global _initialized
    if _initialized:
        return
    try:
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            data = json.loads(
                base64.b64decode(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"]).decode()
            )
            cred = credentials.Certificate(data)
        else:
            cred = credentials.ApplicationDefault()
        initialize_app(cred)
    except Exception as e:
        import warnings
        warnings.warn(f"Firebase init skipped: {e}")
    _initialized = True


def get_firestore() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.client()
    return _db
