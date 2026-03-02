import { useEffect, useState } from 'react'
import { onAuthStateChanged, User } from 'firebase/auth'
import { doc, getDoc } from 'firebase/firestore'
import { getAuthInstance, getDb } from './lib/firebase'
import Login from './components/Login'
import Chat from './components/Chat'

export type UserMeta = {
  uid: string
  email: string | null
  displayName: string
  orgId: string
  orgName?: string
  role: string
}

const auth = getAuthInstance()
const db = getDb()

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [userMeta, setUserMeta] = useState<UserMeta | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (u) => {
      setUser(u)
      if (!u) {
        setUserMeta(null)
        setLoading(false)
        return
      }
      try {
        const userSnap = await getDoc(doc(db, 'users', u.uid))
        if (!userSnap.exists()) {
          setUserMeta(null)
          setLoading(false)
          return
        }
        const d = userSnap.data()
        let orgName = ''
        if (d.orgId) {
          const orgSnap = await getDoc(doc(db, 'organizations', d.orgId))
          if (orgSnap.exists()) orgName = orgSnap.data().name || ''
        }
        setUserMeta({
          uid: u.uid,
          email: u.email || null,
          displayName: d.displayName || u.email || 'User',
          orgId: d.orgId || '',
          orgName,
          role: d.role || 'member',
        })
      } catch {
        setUserMeta(null)
      }
      setLoading(false)
    })
    return () => unsub()
  }, [])

  if (loading) return <div className="loading">Loading…</div>
  if (!user || !userMeta?.orgId) return <Login />
  return <Chat user={user} userMeta={userMeta} />
}
