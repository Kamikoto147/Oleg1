import { io, Socket } from 'socket.io-client'

let chatSocket: Socket | null = null
let rtcSocket: Socket | null = null

export function initSockets(userId:string){
  if(!chatSocket){
    chatSocket = io('/chat', { auth: { userId }, transports: ['websocket'] })
  }
  if(!rtcSocket){
    rtcSocket = io('/rtc', { auth: { userId }, transports: ['websocket'] })
  }
  return { chatSocket, rtcSocket }
}

export function getChatSocket(){ return chatSocket }
export function getRTCsocket(){ return rtcSocket }
