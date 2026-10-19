export interface State {session_id:string; mode:'PRIVATE'|'GUEST'|'LOCKED'|'UNKNOWN'; speaker_status:string; guest_presence:string; authentication_status:string; similarity:number|null; pin_until:number; candidate_until:number; expires_at:number}
export interface Health {status:string; mcp_sdk:string; transport:string; voice:{name:string;available:boolean;loaded:boolean;threshold:number;margin:number;liveness:boolean}; stt_available:boolean;agent:string;pin_configured:boolean}
export interface Audit {id:number; timestamp:number;session_id:string;speaker_status:string;guest_presence:string;tool:string;sensitivity:string;decision:string;reason:string;result_status:string}
export interface AgentResult {mode:string;response:string;tool?:string;result?:{decision:string;reason:string;status:string;data?:unknown};timeline:{stage:string;elapsed_ms:number;protocol?:string;count?:number;tool?:string;decision?:string;reason?:string}[];error:boolean}
export interface Identity {enrolled:boolean;enrollment:null|{sample_count:number;consent_at:number;model:string};model:Health['voice']}
export interface VoiceResult {assessment:{speaker_status:string;similarity:number|null;quality:{duration:number;speech_seconds:number}};transcript:{text:string;available:boolean;message:string};agent:AgentResult|null;state:State}
export interface Rules {matrix:{label:string;sensitivity:string;cells:Record<string,{decision:string;reason:string}>}[];settings:{audit_days:number}}

export async function api<T>(path:string, method='GET', body?:unknown):Promise<T> {
 const form=body instanceof FormData;
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:body&&!form?{'Content-Type':'application/json'}:undefined,body:body?(form?body:JSON.stringify(body)):undefined});
 const data=await response.json().catch(()=>({detail:'Unexpected server response'}));
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:response.status===422?'Input rejected. Check the form and try again.':'Request failed');
 return data as T;
}
export const readable=(value:string)=>value.toLowerCase().replaceAll('_',' ');
