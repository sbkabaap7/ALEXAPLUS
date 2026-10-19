import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react';
import {Check,KeyRound,Shield,Trash2} from 'lucide-react';
import {api,type AgentResult,type Health,type Identity,type State,type VoiceResult} from '../services/api';
import {Modal} from '../components/ui';
import AudioCapture from '../components/AudioCapture';
import RequestConsole from '../components/RequestConsole';
import CinematicHome from '../components/CinematicHome';
import {streamRequest} from '../services/stream';

const privateTools=new Set(['list_calendar_events','list_reminders','read_personal_note']);

export default function App(){
 const [state,setState]=useState<State|null>(null),[health,setHealth]=useState<Health|null>(null),[identity,setIdentity]=useState<Identity|null>(null);
 const [connected,setConnected]=useState(true),[setupOpen,setSetupOpen]=useState(false),[busy,setBusy]=useState(false),[capturing,setCapturing]=useState(false);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[message,setMessage]=useState(''),[streamText,setStreamText]=useState(''),[voiceFeedback,setVoiceFeedback]=useState('');
 const [result,setResult]=useState<AgentResult|null>(null),[recent,setRecent]=useState<string[]>([]),[pin,setPin]=useState('');
 const [samples,setSamples]=useState<Blob[]>([]),[consent,setConsent]=useState(false),[confirmDelete,setConfirmDelete]=useState(false),[editingVoice,setEditingVoice]=useState(false);
 const sessionRef=useRef<State|null>(null);
 const refresh=useCallback(async()=>{
  try{
   const h=await api<Health>('/health');setHealth(h);setConnected(true);
   const s=await api<State>('/state').catch(()=>null);sessionRef.current=s;setState(s);
   setIdentity(s&&s.mode!=='LOCKED'?await api<Identity>('/identity'):null);
  }catch{setConnected(false);}
 },[]);
 useEffect(()=>{void refresh();const timer=window.setInterval(async()=>{
  try{const s=await api<State>('/state');sessionRef.current=s;setState(s);setConnected(true);}catch{/* A new session is started on the next action. */}
 },4000);return()=>window.clearInterval(timer);},[refresh]);
 useEffect(()=>{if(state?.mode!=='PRIVATE')setResult(previous=>previous?.tool&&privateTools.has(previous.tool)&&previous.result?.decision==='ALLOW'?null:previous);},[state?.mode,state?.speaker_status,state?.authentication_status]);
 const ensureSession=async()=>{
  if(!sessionRef.current||sessionRef.current.mode==='LOCKED'){
   const next=await api<State>('/session','POST');sessionRef.current=next;setState(next);setRecent([]);
  }
 };
 const act=async(work:()=>Promise<void>,success='')=>{
  setBusy(true);setError('');setNotice('');
  try{await work();if(success)setNotice(success);await refresh();}
  catch(e){setError(e instanceof Error?e.message:'Something went wrong. Try again.');}
  finally{setBusy(false);}
 };
 const openSetup=async()=>{setError('');setNotice('');setSetupOpen(true);try{await ensureSession();await refresh();}catch(e){setError(e instanceof Error?e.message:'Cannot start a session.');}};
 const closeSetup=()=>{if(busy)return;setSetupOpen(false);setPin('');setSamples([]);setConsent(false);setConfirmDelete(false);setEditingVoice(false);setError('');setNotice('');};
 const submitPin=(event:FormEvent)=>{event.preventDefault();void act(async()=>{
  await ensureSession();await api('/pin/setup','POST',{pin});setPin('');
 },'PIN saved.');};
 const saveVoice=()=>void act(async()=>{
  await api('/pin/verify','POST',{pin});
  const form=new FormData();form.append('consent','true');
  samples.forEach((sample,index)=>form.append('samples',sample,'sample-'+(index+1)+'.wav'));
  await api('/identity/enroll','POST',form);setSamples([]);setConsent(false);setPin('');setEditingVoice(false);
 },'Voice saved.');
 const deleteVoice=()=>void act(async()=>{await api('/pin/verify','POST',{pin});await api('/identity','DELETE');setSamples([]);setPin('');setConfirmDelete(false);setEditingVoice(false);},'Saved voice deleted.');
 const beforeRecord=async()=>{
  await ensureSession();const next=await api<State>('/voice/start','POST');sessionRef.current=next;setState(next);
  setResult(null);setVoiceFeedback('');setStreamText('');setMessage('');
 };
 const verify=async(blob:Blob)=>act(async()=>{
  const form=new FormData();form.append('audio',blob,'capture.wav');
  const output=await api<VoiceResult>('/voice','POST',form);
  sessionRef.current=output.state;setState(output.state);setResult(output.agent);
  setVoiceFeedback(output.agent?'':output.transcript.message||'I couldn’t hear a request. Try again or type it.');
  if(output.transcript.text){setMessage(output.transcript.text);setRecent(previous=>[output.transcript.text,...previous.filter(item=>item!==output.transcript.text)].slice(0,5));}
 });
 const ask=(text:string)=>{
  if(!text.trim()||busy||capturing)return;
  void act(async()=>{
   await ensureSession();setResult(null);setVoiceFeedback('');setStreamText('');setMessage(text);
   setRecent(previous=>[text,...previous.filter(item=>item!==text)].slice(0,5));
   const output=await streamRequest(text,delta=>setStreamText(previous=>previous+delta));
   setResult(output);setStreamText('');
  });
 };
 const response=result?<div className="agent-output" aria-live="polite"><p className="agent-answer">{result.response}</p></div>:streamText?<p className="stream-text">{streamText}</p>:voiceFeedback?<div className="agent-output" role="status"><p>{voiceFeedback}</p></div>:null;
 return <div className="app-shell is-overview">
  <header className="site-header"><button className="site-brand" aria-label="GuestGuard home" onClick={()=>{closeSetup();window.scrollTo({top:0,behavior:'smooth'});}}><Shield size={25}/><span>GuestGuard<span className="brand-period">.</span></span></button><button className="button setup-trigger" onClick={()=>void openSetup()}><KeyRound size={16}/>Voice &amp; PIN</button></header>
  <main><CinematicHome><RequestConsole message={message} setMessage={setMessage} busy={busy} capturing={capturing} setCapturing={setCapturing} send={ask} beforeRecord={beforeRecord} onAudio={verify} recent={recent} response={response}/></CinematicHome></main>
  {!connected&&<div className="connection-error" role="alert">GuestGuard isn’t responding. <button onClick={()=>void refresh()}>Retry</button></div>}
  {error&&!setupOpen&&<div className="connection-error" role="alert">{error}</div>}
  {setupOpen&&<Modal title="Voice & PIN" onClose={closeSetup}><div className="setup-content">
   <div className="setup-status"><span><strong>PIN</strong> {health?.pin_configured?'Saved':'Not set'}</span><span><strong>Voice</strong> {identity?.enrolled?'Saved':'Not saved'}</span></div>
   {!health?.pin_configured&&<form className="setup-block" onSubmit={submitPin}>
    <h3>Set a PIN</h3><p>You'll use it only to save, replace, or delete your voice.</p>
    <label className="field-label" htmlFor="pin-setup">Choose a PIN</label>
    <input id="pin-setup" type="password" inputMode="numeric" autoComplete="new-password" pattern="[0-9]{6,12}" minLength={6} maxLength={12} required value={pin} onChange={event=>setPin(event.target.value)}/>
    <button className="button primary" disabled={busy||pin.length<6}>Save PIN</button>
   </form>}
   {identity?.enrolled&&!editingVoice&&<div className="setup-block">
    <h3>Your voice is saved</h3><p>Ask using this voice to open private information. Your saved voice stays available in later sessions.</p>
    <div className="button-row"><button className="button" onClick={()=>{setPin('');setConfirmDelete(false);setEditingVoice(true);}}>Replace saved voice</button><button className="text-button" onClick={()=>{setPin('');setConfirmDelete(true);}}>Delete saved voice</button></div>
   </div>}
   {health?.pin_configured&&(!identity?.enrolled||editingVoice)&&<div className="setup-block">
    <h3>{editingVoice?'Replace your voice':'Save your voice'}</h3><p>Record three short samples in a quiet room.</p>
    <label className="check-row"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/><span>I agree to save my voice on this computer. I can delete it later.</span></label>
    <div className="sample-progress" aria-label={samples.length+' of 3 voice samples recorded'}>{[1,2,3].map(index=><span key={index} className={samples.length>=index?'complete':''}>{samples.length>=index?<Check size={14}/>:index}</span>)}</div>
    {consent&&samples.length<3&&<AudioCapture label={'Record sample '+(samples.length+1)} disabled={busy} onAudio={blob=>setSamples(current=>[...current,blob].slice(0,3))}/>}
    <label className="field-label" htmlFor="pin-save">PIN to {editingVoice?'replace':'save'} voice</label>
    <input id="pin-save" type="password" inputMode="numeric" autoComplete="current-password" pattern="[0-9]{6,12}" minLength={6} maxLength={12} value={pin} onChange={event=>setPin(event.target.value)}/>
    <div className="button-row"><button className="button primary" disabled={busy||pin.length<6||!consent||samples.length!==3} onClick={saveVoice}>{editingVoice?'Replace voice':'Save voice'}</button>{samples.length>0&&<button className="button" disabled={busy} onClick={()=>setSamples([])}>Discard samples</button>}{editingVoice&&<button className="button" disabled={busy} onClick={()=>{setEditingVoice(false);setSamples([]);setConsent(false);setPin('');}}>Cancel</button>}</div>
   </div>}
   {identity?.enrolled&&confirmDelete&&<div className="setup-block delete-block">
    <h3>Delete your saved voice?</h3><label className="field-label" htmlFor="pin-delete">PIN to delete voice</label>
    <input id="pin-delete" type="password" inputMode="numeric" autoComplete="current-password" pattern="[0-9]{6,12}" minLength={6} maxLength={12} value={pin} onChange={event=>setPin(event.target.value)}/>
    <div className="button-row"><button className="button danger" disabled={busy||pin.length<6} onClick={deleteVoice}><Trash2 size={15}/>Delete voice</button><button className="button" onClick={()=>{setConfirmDelete(false);setPin('');}}>Cancel</button></div>
   </div>}
   {notice&&<p className="setup-notice" role="status">{notice}</p>}{error&&<p className="setup-error" role="alert">{error}</p>}
  </div></Modal>}
 </div>;
}
