const API_URL = import.meta.env.VITE_API_URL || ''

export type OrgUser = {
  uid: string
  displayName: string
  email: string
  role: string
}

export async function fetchOrgUsers(idToken: string): Promise<OrgUser[]> {
  const res = await fetch(`${API_URL}/api/rooms/org-users`, {
    headers: { Authorization: `Bearer ${idToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  const data = await res.json()
  return data.users as OrgUser[]
}

export async function addRoomMember(roomId: string, userId: string, idToken: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/rooms/${roomId}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${idToken}` },
    body: JSON.stringify({ user_id: userId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
}

export async function removeRoomMember(roomId: string, userId: string, idToken: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/rooms/${roomId}/members/${userId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${idToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
}

export async function invokeGemini(roomId: string, lastMessageContent: string, idToken: string): Promise<ReadableStream<Uint8Array> | null> {
  const maxRetries = 3
  const baseDelayMs = 1000
  let lastError: Error | null = null

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
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
        const msg = err.detail || res.statusText
        const errObj = new Error(msg)
        ;(errObj as { status?: number }).status = res.status
        throw errObj
      }
      return res.body
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e))
      const status = (e as { status?: number })?.status
      const isRetryable =
        status === 503 ||
        status === 502 ||
        status === 504 ||
        (status == null && (e as Error).name !== 'AbortError')
      if (!isRetryable || attempt === maxRetries - 1) throw lastError
      const delayMs = baseDelayMs * Math.pow(2, attempt)
      await new Promise((r) => setTimeout(r, delayMs))
    }
  }
  throw lastError ?? new Error('Invoke failed')
}
