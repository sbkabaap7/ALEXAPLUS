import type {AgentResult} from './api';

export async function streamRequest(text:string,onDelta:(text:string)=>void):Promise<AgentResult>{
 const response=await fetch('/api/agent/stream',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
 if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.detail||'Request failed. Try again.');}
 if(!response.body)throw new Error('This browser could not read the reply.');
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',output:AgentResult|undefined;
 const consume=(line:string)=>{if(!line.trim())return;const packet=JSON.parse(line);if(packet.type==='delta')onDelta(packet.text);if(packet.type==='result')output=packet.result;};
 try{while(true){const {done,value}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let end;while((end=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,end));buffer=buffer.slice(end+1);}if(done){consume(buffer);break;}}}finally{reader.releaseLock();}
 if(!output)throw new Error('The reply was interrupted. Try again.');
 return output;
}
