import React, { useState } from 'react'
import { login, register } from '../../lib/api'

export default function LoginPage({ onLogin }:{onLogin:any}){
  const [mode,setMode]=useState<'login'|'register'>('login')
  const [username,setUsername]=useState('')
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')

  async function submit(e:any){
    e.preventDefault()
    try {
      if(mode==='login'){
        const res = await login({ username, password })
        if(res.access){ localStorage.setItem('access_token', res.access); onLogin(res.user) }
      } else {
        const res = await register({ email, username, password })
        if(res.access){ localStorage.setItem('access_token', res.access); onLogin(res.user) }
      }
    } catch(err){ alert('Auth failed') }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form className="bg-[#07102a] p-6 rounded-md w-80" onSubmit={submit}>
        <h2 className="text-xl mb-4">{mode==='login' ? 'Login' : 'Register'}</h2>
        {mode==='register' && <input className="w-full mb-2 p-2" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />}
        <input className="w-full mb-2 p-2" placeholder="Username or email" value={username} onChange={e=>setUsername(e.target.value)} />
        <input className="w-full mb-4 p-2" placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        <button className="w-full py-2 bg-olegaccent rounded">{mode==='login'?'Sign in':'Create'}</button>
        <div className="mt-3 text-sm">
          <button type="button" onClick={()=> setMode(mode==='login'?'register':'login')} className="underline">
            {mode==='login' ? 'Create account' : 'Have account? Sign in'}
          </button>
        </div>
      </form>
    </div>
  )
}
