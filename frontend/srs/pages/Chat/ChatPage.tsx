import React, { useEffect, useState } from 'react'
import { listServers, listChannels, listMessages, sendMessage } from '../../lib/api'
import { initSockets, getChatSocket } from '../../lib/socket'

export default function ChatPage({ user }:{user:any}){
  const [servers, setServers] = useState<any[]>([])
  const [channels, setChannels] = useState<any[]>([])
  const [activeServer, setActiveServer] = useState<number| null>(null)
  const [activeChannel, setActiveChannel] = useState<number| null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [text, setText] = useState('')

  useEffect(()=>{
    async function init(){
      const s = await listServers(String(user.id))
      setServers(s)
      initSockets(String(user.id))
      const socket = getChatSocket()
      socket?.on('message:new', (m:any)=>{
        if(m.channel_id === activeChannel) setMessages(prev => [...prev, m])
      })
    }
    init()
  },[])

  useEffect(()=>{
    async function loadChannels(){
      if(activeServer !== null){
        const res = await listChannels(activeServer)
        setChannels(res)
        if(res[0]) setActiveChannel(res[0].id)
      }
    }
    loadChannels()
  }, [activeServer])

  useEffect(()=>{
    async function loadMessages(){
      if(activeChannel !== null){
        const res = await listMessages(activeChannel)
        setMessages(res.messages)
      }
    }
    loadMessages()
  }, [activeChannel])

  async function handleSend(){
    if(!text || activeChannel===null) return
    await sendMessage(activeChannel, text, String(user.id))
    setText('')
  }

  return (
    <div className="h-screen grid grid-cols-12">
      <aside className="col-span-1 bg-[#07102a] p-2">
        {servers.map(s=> <div key={s.id} className="mb-2 p-2 bg-[#0c1530] rounded cursor-pointer" onClick={()=>setActiveServer(s.id)}>{s.name[0]}</div>)}
      </aside>
      <div className="col-span-3 bg-[#071029] p-4">
        <h3 className="mb-2">Channels</h3>
        {channels.map(c=> <div key={c.id} className="p-2 cursor-pointer" onClick={()=>setActiveChannel(c.id)}># {c.name}</div>)}
      </div>
      <main className="col-span-8 flex flex-col">
        <div className="flex-1 p-4 overflow-auto">
          {messages.map((m:any)=> <div key={m.id} className="mb-2"><b>{m.author_id}</b>: {m.content}</div>)}
        </div>
        <div className="p-4 bg-[#07102a] flex">
          <input className="flex-1 p-2 mr-2 bg-[#0b1222]" value={text} onChange={e=>setText(e.target.value)} />
          <button onClick={handleSend} className="px-4 py-2 bg-olegaccent rounded">Send</button>
        </div>
      </main>
    </div>
  )
}
