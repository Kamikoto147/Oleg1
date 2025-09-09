import React, { useEffect, useState } from 'react'
import LoginPage from './pages/Auth/LoginPage'
import ChatPage from './pages/Chat/ChatPage'
import { getMe } from './lib/api'

export default function App(){
  const [user, setUser] = useState<any|null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    async function init(){
      try {
        const res = await getMe()
        if(res.user) setUser(res.user)
      } catch(e){}
      setLoading(false)
    }
    init()
  },[])

  if(loading) return <div className="p-6">Loading...</div>
  if(!user) return <LoginPage onLogin={(u:any)=>setUser(u)} />
  return <ChatPage user={user} />
}
