"""Rooms API: manage room membership (admin only)."""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from firebase_admin import firestore as admin_firestore

from app.core.auth import get_uid_from_headers
from app.core.firebase import get_firestore
from app.services.tenant import get_user_org, validate_room_access

router = APIRouter()


def _require_uid(authorization: str | None = Header(None)) -> str:
    uid = get_uid_from_headers(authorization)
    if not uid:
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return uid


def _require_admin(authorization: str | None) -> tuple[str, str]:
    """Return (uid, org_id) or raise if not authenticated / not admin."""
    uid = _require_uid(authorization)
    user_meta = get_user_org(uid)
    if not user_meta or not user_meta.get("org_id"):
        raise HTTPException(status_code=403, detail="User not associated with an organization")
    if user_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return uid, user_meta["org_id"]


@router.get("/org-users")
async def list_org_users(authorization: str | None = Header(None)):
    """Return all users in the requesting user's organization."""
    uid = _require_uid(authorization)
    user_meta = get_user_org(uid)
    if not user_meta or not user_meta.get("org_id"):
        raise HTTPException(status_code=403, detail="User not associated with an organization")
    org_id = user_meta["org_id"]

    db = get_firestore()
    docs = db.collection("users").where("orgId", "==", org_id).get()
    users = []
    for doc in docs:
        d = doc.to_dict()
        users.append({
            "uid": doc.id,
            "displayName": d.get("displayName", ""),
            "email": d.get("email", ""),
            "role": d.get("role", "member"),
        })
    return {"users": users}


class AddMemberBody(BaseModel):
    user_id: str


@router.post("/{room_id}/members")
async def add_member(
    room_id: str,
    body: AddMemberBody,
    authorization: str | None = Header(None),
):
    """Add a user to a room. Admin only. Target user must be in the same org."""
    uid, org_id = _require_admin(authorization)
    validate_room_access(uid, org_id, room_id)

    db = get_firestore()
    target_doc = db.collection("users").document(body.user_id).get()
    if not target_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    if target_doc.to_dict().get("orgId") != org_id:
        raise HTTPException(status_code=403, detail="User does not belong to your organization")

    db.collection("rooms").document(room_id).update(
        {"memberIds": admin_firestore.ArrayUnion([body.user_id])}
    )
    return {"ok": True}


@router.delete("/{room_id}/members/{user_id}")
async def remove_member(
    room_id: str,
    user_id: str,
    authorization: str | None = Header(None),
):
    """Remove a user from a room. Admin only. Admin cannot remove themselves."""
    uid, org_id = _require_admin(authorization)
    validate_room_access(uid, org_id, room_id)

    if user_id == uid:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the room")

    db = get_firestore()
    db.collection("rooms").document(room_id).update(
        {"memberIds": admin_firestore.ArrayRemove([user_id])}
    )
    return {"ok": True}
