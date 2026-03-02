"""Tenant (org) and room access validation."""
from fastapi import HTTPException

from app.core.firebase import get_firestore


def get_user_org(uid: str) -> dict | None:
    db = get_firestore()
    user_ref = db.collection("users").document(uid)
    user = user_ref.get()
    if not user.exists:
        return None
    data = user.to_dict()
    return {"org_id": data.get("orgId"), "role": data.get("role"), "display_name": data.get("displayName")}


def validate_room_access(uid: str, org_id: str, room_id: str) -> dict:
    """Validate user can access room. Returns room snapshot dict or raises."""
    db = get_firestore()
    room_ref = db.collection("rooms").document(room_id)
    room = room_ref.get()
    if not room.exists:
        raise HTTPException(status_code=404, detail="Room not found")
    data = room.to_dict()
    if data.get("orgId") != org_id:
        raise HTTPException(status_code=404, detail="Room not found")
    member_ids = data.get("memberIds") or []
    if uid not in member_ids:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    return data
