from firebase_admin import auth


def verify_token(id_token: str) -> dict:
    """Verify Firebase ID token and return decoded claims."""
    decoded = auth.verify_id_token(id_token)
    return decoded


def get_uid_from_headers(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        decoded = verify_token(token)
        return decoded.get("uid")
    except Exception:
        return None
