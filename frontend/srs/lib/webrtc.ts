// Minimal helper for creating RTCPeerConnection with STUN/TURN from server
export async function createPeerConnection(config:{stun?:string, turn?:string}, onTrack?: (ev:any)=>void){
  const iceServers:any[] = []
  if(config.stun) iceServers.push({urls: config.stun})
  if(config.turn) iceServers.push({urls: config.turn})
  const pc = new RTCPeerConnection({ iceServers })
  pc.ontrack = onTrack || (()=>{})
  return pc
}
