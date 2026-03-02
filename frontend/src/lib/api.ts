const API_URL = import.meta.env.VITE_API_URL || ''

export async function invokeGemini(roomId: string, lastMessageContent: string, idToken: string): Promise<ReadableStream<Uint8Array> | null> {
  const res = await fetch(`${API_URL}/api/chat/invoke`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
    body: JSON.stringify({ room_id: roomId, last_message_content: lastMessageContent }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  return res.body
}
