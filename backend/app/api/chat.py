"""Chat API: invoke Gemini and stream response, writing to Firestore."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.core.firebase import get_firestore
from app.config import get_settings
from app.services.tenant import validate_room_access
from app.services.gemini import (
    format_history_for_gemini,
    is_ai_invocation,
    stream_gemini_response,
)

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=4)


class InvokeBody(BaseModel):
    room_id: str
    last_message_content: str


@router.post("/invoke")
async def invoke_ai(body: InvokeBody, request: Request):
    """Invoke Gemini for the room. Call this when the last user message contains @Gemini or @AI.
    Creates an AI message in Firestore and streams content into it. Returns SSE stream of chunks.
    """
    # Auth and org resolved by TenantMiddleware — available on request.state
    uid: str = request.state.uid
    org_id: str = request.state.org_id
    user_name: str = request.state.display_name

    room_id = body.room_id
    last_message_content = body.last_message_content
    if not is_ai_invocation(last_message_content):
        raise HTTPException(status_code=400, detail="Last message must mention @Gemini or @AI")

    validate_room_access(uid, org_id, room_id)

    db = get_firestore()
    room_ref = db.collection("rooms").document(room_id)
    messages_ref = room_ref.collection("messages")

    # Fetch last N messages (including the one that invoked AI)
    limit = get_settings().ai_context_message_limit
    docs = list(messages_ref.order_by("timestamp", direction="DESCENDING").limit(limit).get())
    messages = []
    participant_names = set()
    for msg_doc in reversed(docs):
        d = msg_doc.to_dict()
        d["id"] = msg_doc.id
        messages.append(d)
        name = d.get("senderName")
        if name:
            participant_names.add(name)
    last_sender_name = (messages[-1].get("senderName") or user_name) if messages else user_name
    participant_names = list(participant_names) or [user_name]

    conversation_text = format_history_for_gemini(messages, limit)
    project_id = get_settings().google_cloud_project
    if not project_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_PROJECT not configured")
    location = get_settings().vertex_ai_location

    # Create placeholder AI message in Firestore
    ai_ref = messages_ref.document()
    ai_ref.set({
        "senderId": "gemini-ai",
        "senderName": "Gemini AI",
        "content": "",
        "timestamp": datetime.now(timezone.utc),
        "type": "ai",
        "streaming": True,
    })

    async def stream_and_update():
        full_content = []
        loop = asyncio.get_event_loop()
        try:
            def run_stream():
                return list(stream_gemini_response(
                    project_id, location, conversation_text,
                    last_sender_name, participant_names,
                ))
            chunks = await loop.run_in_executor(_executor, run_stream)
            for chunk in chunks:
                full_content.append(chunk)
                new_content = "".join(full_content)
                ai_ref.update({"content": new_content})
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            ai_ref.update({"streaming": False})
        except Exception as e:
            ai_ref.update({
                "content": "".join(full_content) + f"\n\n[Error: {e}]",
                "streaming": False,
            })
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_and_update(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
