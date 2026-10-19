import {useEffect,useRef,type ReactNode} from 'react';
import {ArrowUp} from 'lucide-react';
import AudioCapture from './AudioCapture';
import BlurText from './BlurText';

const examples=['What’s on my calendar?','Why is the sky blue?','What is the home status?'];
export default function RequestConsole({message,setMessage,busy,capturing,setCapturing,send,beforeRecord,onAudio,response,recent}:{message:string;setMessage:(text:string)=>void;busy:boolean;capturing:boolean;setCapturing:(active:boolean)=>void;send:(text:string)=>void;beforeRecord:()=>Promise<void>;onAudio:(blob:Blob)=>Promise<void>;response:ReactNode;recent:string[]}){
 const input=useRef<HTMLInputElement>(null);
 useEffect(()=>{const shortcut=(e:KeyboardEvent)=>{const target=e.target as HTMLElement;if(e.key==='/'&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!target.closest('input,textarea,select,[contenteditable=true],[role=dialog]')){e.preventDefault();input.current?.focus();}};document.addEventListener('keydown',shortcut);return()=>document.removeEventListener('keydown',shortcut);},[]);
 const run=(text:string)=>{if(!busy&&!capturing&&text.trim()){setMessage(text);send(text);}};
 return <section className="request-console" aria-label="GuestGuard requests">
  <h1><BlurText text="Ask anything. Check what matters."/></h1>
  <form className={'command-input '+(capturing?'is-recording':'')} onSubmit={e=>{e.preventDefault();run(message);}}>
   <label className="sr-only" htmlFor="home-request">Your request</label><input ref={input} id="home-request" placeholder={capturing?'Listening…':'Ask GuestGuard…'} value={message} onChange={e=>setMessage(e.target.value)} maxLength={2000} readOnly={capturing} disabled={busy} autoComplete="off"/>
   <AudioCapture compact disabled={busy} beforeStart={beforeRecord} onPreview={setMessage} onCaptureChange={setCapturing} onAudio={onAudio}/>
   <button type="submit" className="button primary send-button" aria-label="Send request" title="Send request (Enter)" disabled={busy||capturing||!message.trim()}><ArrowUp size={19}/></button>
  </form>
  <div className="example-prompts" aria-label="Example requests">{examples.map(text=><button key={text} onClick={()=>run(text)} disabled={busy||capturing}>{text}</button>)}</div>
  <div className="response-area" aria-busy={busy}>{busy&&<div className="request-loading" role="status"><span className="loading-dot"/>Working…</div>}{response}</div>
  {recent.length>0&&<section className="recent-requests" aria-label="Recent requests"><h2>Recent requests</h2><ul>{recent.map(text=><li key={text}><button disabled={busy||capturing} onClick={()=>run(text)}>{text}</button></li>)}</ul></section>}
 </section>;
}
