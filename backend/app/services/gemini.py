"""Vertex AI Gemini streaming and context formatting."""
from typing import Iterator

from app.config import get_settings


def format_history_for_gemini(messages: list[dict], limit: int) -> str:
    from datetime import datetime
    lines = []
    for m in messages[-limit:]:
        name = m.get("senderName") or "Unknown"
        content = (m.get("content") or "").strip()
        ts = m.get("timestamp")
        if hasattr(ts, "strftime"):
            time_str = ts.strftime("%H:%M")
        elif hasattr(ts, "seconds"):
            time_str = datetime.utcfromtimestamp(ts.seconds).strftime("%H:%M")
        else:
            time_str = str(ts) if ts else ""
        lines.append(f"[{time_str}] {name}: {content}")
    return "\n".join(lines)


def is_ai_invocation(content: str) -> bool:
    if not content:
        return False
    normalized = content.strip().lower()
    return "@gemini" in normalized or "@ai" in normalized


def build_system_instruction(participant_names: list[str]) -> str:
    names = ", ".join(participant_names) if participant_names else "the team"
    return (
        "You are Gemini AI in a collaborative team chat. Multiple users are in the same room. "
        "When you respond, you may address users by name when relevant. "
        f"Participants in this conversation may include: {names}. "
        "Keep responses concise but helpful. Format with clear structure when needed."
    )


def stream_gemini_response(
    project_id: str,
    location: str,
    conversation_text: str,
    last_sender_name: str,
    participant_names: list[str],
) -> Iterator[str]:
    """Stream tokens from Vertex AI Gemini. Yields text chunks (sync iterator)."""
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=project_id, location=location)
    except Exception as e:
        raise RuntimeError(f"Vertex AI init failed: {e}") from e

    model = GenerativeModel("gemini-2.5-flash")
    prompt = (
        "[Conversation History]\n"
        f"{conversation_text}\n"
        "---\n"
        f"Respond to the conversation. The last message is from {last_sender_name}. "
        f"Multiple users are participating: {', '.join(participant_names) or 'the team'}."
    )
    try:
        responses = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 2048, "temperature": 0.7},
            stream=True,
        )
        for chunk in responses:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"I'm having trouble responding right now: {e}. Please try again."
