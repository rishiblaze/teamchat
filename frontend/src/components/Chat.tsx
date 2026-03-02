import { useState, useEffect, useRef, useCallback } from 'react'
import {
  collection,
  query,
  where,
  onSnapshot,
  addDoc,
  serverTimestamp,
  doc,
  setDoc,
  deleteDoc,
  orderBy,
  limit,
  Timestamp,
} from 'firebase/firestore'
import { signOut } from 'firebase/auth'
import { invokeGemini } from '../lib/api'
import type { UserMeta } from '../App'

import { getDb as getDbLib, getAuthInstance as getAuthLib } from '../lib/firebase'

type Message = {
  id: string
  senderId: string
  senderName: string
  content: string
  timestamp: Timestamp
  type: 'user' | 'ai'
  streaming?: boolean
}

type Room = {
  id: string
  name: string
  description?: string
  memberIds: string[]
}

export default function Chat({ user, userMeta }: { user: { uid: string }; userMeta: UserMeta }) {
  const [rooms, setRooms] = useState<Room[]>([])
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [presence, setPresence] = useState<Record<string, { name: string }>>({})
  const [typing, setTyping] = useState<Record<string, string>>({})
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [newRoomName, setNewRoomName] = useState('')
  const [showNewRoom, setShowNewRoom] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const db = getDbLib()

  // Subscribe to rooms where user is member
  useEffect(() => {
    const q = query(
      collection(db, 'rooms'),
      where('memberIds', 'array-contains', user.uid)
    )
    const unsub = onSnapshot(q, (snap) => {
      const list: Room[] = []
      snap.docs.forEach((d) => {
        const data = d.data()
        list.push({
          id: d.id,
          name: data.name || '',
          description: data.description,
          memberIds: data.memberIds || [],
        })
      })
      setRooms(list)
      if (!currentRoomId && list.length) setCurrentRoomId(list[0].id)
    })
    return () => unsub()
  }, [user.uid, db])

  // Subscribe to messages for current room
  useEffect(() => {
    if (!currentRoomId) {
      setMessages([])
      return
    }
    const q = query(
      collection(db, 'rooms', currentRoomId, 'messages'),
      orderBy('timestamp', 'asc'),
      limit(100)
    )
    const unsub = onSnapshot(q, (snap) => {
      const list: Message[] = []
      snap.docs.forEach((d) => {
        const data = d.data()
        list.push({
          id: d.id,
          senderId: data.senderId || '',
          senderName: data.senderName || 'Unknown',
          content: data.content || '',
          timestamp: data.timestamp,
          type: (data.type as 'user' | 'ai') || 'user',
          streaming: data.streaming,
        })
      })
      setMessages(list)
    })
    return () => unsub()
  }, [currentRoomId, db])

  // Presence: write self on mount, remove on unmount; subscribe to others
  useEffect(() => {
    if (!currentRoomId) return
    const presenceRef = doc(db, 'rooms', currentRoomId, 'presence', user.uid)
    setDoc(presenceRef, { uid: user.uid, displayName: userMeta.displayName, updatedAt: serverTimestamp() })
    const unsub = onSnapshot(collection(db, 'rooms', currentRoomId, 'presence'), (snap) => {
      const who: Record<string, { name: string }> = {}
      snap.docs.forEach((d) => {
        const data = d.data()
        who[d.id] = { name: data.displayName || d.id }
      })
      setPresence(who)
    })
    return () => {
      deleteDoc(presenceRef)
      unsub()
    }
  }, [currentRoomId, user.uid, userMeta.displayName, db])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || !currentRoomId || sending) return
    setSending(true)
    setInput('')
    try {
      const messagesRef = collection(db, 'rooms', currentRoomId, 'messages')
      await addDoc(messagesRef, {
        senderId: user.uid,
        senderName: userMeta.displayName,
        content: text,
        timestamp: serverTimestamp(),
        type: 'user',
      })
      const isInvoke = /@gemini|@ai/i.test(text)
      if (isInvoke) {
        const token = await getAuthLib().currentUser?.getIdToken()
        if (token) {
          const stream = await invokeGemini(currentRoomId, text, token)
          if (stream) {
            const reader = stream.getReader()
            const dec = new TextDecoder()
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              dec.decode(value)
            }
          }
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setSending(false)
    }
  }

  // Typing indicator: write to rooms/roomId/typing/uid when user types, remove on blur/send
  const typingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const setTypingIndicator = useCallback(
    (value: boolean) => {
      if (!currentRoomId) return
      const ref = doc(db, 'rooms', currentRoomId, 'typing', user.uid)
      if (value) setDoc(ref, { displayName: userMeta.displayName })
      else deleteDoc(ref)
    },
    [currentRoomId, user.uid, userMeta.displayName, db]
  )
  useEffect(() => {
    if (!input.trim()) {
      setTypingIndicator(false)
      return
    }
    setTypingIndicator(true)
    if (typingRef.current) clearTimeout(typingRef.current)
    typingRef.current = setTimeout(() => setTypingIndicator(false), 3000)
    return () => {
      if (typingRef.current) clearTimeout(typingRef.current)
    }
  }, [input, setTypingIndicator])

  useEffect(() => {
    if (!currentRoomId) return
    const unsub = onSnapshot(collection(db, 'rooms', currentRoomId, 'typing'), (snap) => {
      const who: Record<string, string> = {}
      snap.docs.forEach((d) => {
        if (d.id !== user.uid) who[d.id] = d.data().displayName || d.id
      })
      setTyping(who)
    })
    return () => unsub()
  }, [currentRoomId, user.uid, db])

  const currentRoom = rooms.find((r) => r.id === currentRoomId)

  const createRoom = async () => {
    const name = newRoomName.trim()
    if (!name || !userMeta.orgId) return
    try {
      await addDoc(collection(db, 'rooms'), {
        orgId: userMeta.orgId,
        name,
        description: '',
        memberIds: [user.uid],
        createdAt: serverTimestamp(),
      })
      setNewRoomName('')
      setShowNewRoom(false)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="chat-layout">
      <header className="chat-header">
        <span className="logo">TeamChat AI</span>
        <span className="org">{userMeta.orgName || 'Organization'}</span>
        <div className="user-menu">
          <span>{userMeta.displayName}</span>
          <button type="button" onClick={() => signOut(getAuthLib())}>
            Sign out
          </button>
        </div>
      </header>
      <div className="chat-body">
        <aside className="room-list">
          <div className="room-list-header">ROOMS</div>
          {rooms.map((r) => (
            <button
              key={r.id}
              type="button"
              className={`room-item ${r.id === currentRoomId ? 'active' : ''}`}
              onClick={() => setCurrentRoomId(r.id)}
            >
              # {r.name}
              {currentRoomId === r.id && (
                <span className="online-count">👥 {Object.keys(presence).length}</span>
              )}
            </button>
          ))}
          <div className="new-room">
            {showNewRoom ? (
              <div className="new-room-form">
                <input
                  type="text"
                  placeholder="Room name"
                  value={newRoomName}
                  onChange={(e) => setNewRoomName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && createRoom()}
                  autoFocus
                />
                <div className="new-room-actions">
                  <button type="button" onClick={createRoom} disabled={!newRoomName.trim()}>Create</button>
                  <button type="button" onClick={() => { setShowNewRoom(false); setNewRoomName('') }}>Cancel</button>
                </div>
              </div>
            ) : (
              <button type="button" className="room-item new-room-btn" onClick={() => setShowNewRoom(true)}>
                + New Room
              </button>
            )}
          </div>
        </aside>
        <main className="chat-main">
          {currentRoom ? (
            <>
              <div className="messages-panel">
                <div className="messages">
                  {messages.map((m) => (
                    <div key={m.id} className={`message ${m.type}`}>
                      <span className="message-meta">
                        {m.senderName} · {m.timestamp?.toDate?.()?.toLocaleTimeString() || '—'}
                      </span>
                      <div className="message-content">
                        {m.content}
                        {m.streaming && <span className="cursor" />}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                {Object.keys(typing).length > 0 && (
                  <div className="typing-indicator">
                    {Object.values(typing).join(', ')} typing…
                  </div>
                )}
                <div className="online-list">
                  Online ({Object.keys(presence).length}): {Object.values(presence).map((p) => p.name).join(', ')}
                </div>
              </div>
              <div className="composer">
                <input
                  type="text"
                  placeholder="Type a message… [@Gemini or @AI to ask]"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                />
                <button type="button" onClick={sendMessage} disabled={sending}>
                  Send
                </button>
              </div>
            </>
          ) : (
            <div className="no-room">Select or create a room</div>
          )}
        </main>
      </div>
    </div>
  )
}
