"""Rooms API: manage room membership (admin only)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from firebase_admin import firestore as admin_firestore

from app.core.firebase import get_firestore
from app.services.tenant import validate_room_access

router = APIRouter()


def _require_admin(request: Request) -> tuple[str, str]:
    """Return (uid, org_id) or raise 403 if the caller is not an admin.

    uid and org_id are already resolved by TenantMiddleware — this just
    adds the role guard on top.
    """
    if request.state.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return request.state.uid, request.state.org_id


@router.get("/org-users")
async def list_org_users(request: Request):
    """Return all users in the requesting user's organization."""
    org_id: str = request.state.org_id

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
async def add_member(room_id: str, body: AddMemberBody, request: Request):
    """Add a user to a room. Admin only. Target user must be in the same org."""
    uid, org_id = _require_admin(request)
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
async def remove_member(room_id: str, user_id: str, request: Request):
    """Remove a user from a room. Admin only. Admin cannot remove themselves."""
    uid, org_id = _require_admin(request)
    validate_room_access(uid, org_id, room_id)

    if user_id == uid:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the room")

    db = get_firestore()
    db.collection("rooms").document(room_id).update(
        {"memberIds": admin_firestore.ArrayRemove([user_id])}
    )
    return {"ok": True}
