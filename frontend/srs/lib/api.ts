import axios from 'axios'

const API = axios.create({
  baseURL: '/api',
  withCredentials: true
})

export async function register(payload:{email:string,username:string,password:string}){
  const r = await API.post('/auth/register', payload)
  return r.data
}

export async function login(payload:{username:string,password:string}){
  const r = await API.post('/auth/login', payload)
  return r.data
}

export async function refresh(){
  const r = await API.post('/auth/refresh')
  return r.data
}

export async function getMe(){
  const token = window.localStorage.getItem('access_token')
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const r = await API.get('/auth/me', { headers })
  return r.data
}

export async function listServers(userId:string){
  const r = await API.get('/servers', { headers: { 'X-User-Id': userId }})
  return r.data
}

export async function listChannels(serverId:number){
  const r = await API.get(`/servers/${serverId}/channels`)
  return r.data
}

export async function listMessages(channelId:number, cursor?:number){
  const q = cursor ? `?cursor=${cursor}` : ''
  const r = await API.get(`/channels/${channelId}/messages${q}`)
  return r.data
}

export async function sendMessage(channelId:number, content:string, userId:string){
  const r = await API.post(`/messages/${channelId}/messages`, { content }, { headers: { 'X-User-Id': userId }})
  return r.data
}
