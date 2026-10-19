import {useEffect,useRef,useState} from 'react';
import {Mic,Square,Upload} from 'lucide-react';


export function encodeWav(chunks:Float32Array[], rate:number) {
 const size=chunks.reduce((sum,chunk)=>sum+chunk.length,0);
 const buffer=new ArrayBuffer(44+size*2),view=new DataView(buffer);
 const text=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
 text(0,'RIFF');view.setUint32(4,36+size*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,size*2,true);
 let offset=44;for(const chunk of chunks)for(const sample of chunk){view.setInt16(offset,Math.max(-1,Math.min(1,sample))*(sample<0?32768:32767),true);offset+=2;}
 return new Blob([buffer],{type:'audio/wav'});
}

type CaptureProps={onAudio:(blob:Blob)=>Promise<void>|void;disabled?:boolean;label?:string;compact?:boolean;beforeStart?:()=>Promise<void>;onPreview?:(text:string)=>void;onCaptureChange?:(capturing:boolean)=>void};

export default function AudioCapture({onAudio,disabled=false,label='Record voice',compact=false,beforeStart,onPreview,onCaptureChange}:CaptureProps) {
 const [recording,setRecording]=useState(false),[pending,setPending]=useState(false),[finishing,setFinishing]=useState(false),[seconds,setSeconds]=useState(0),[error,setError]=useState('');
 const generation=useRef(0),recordingRef=useRef(false),pendingRef=useRef(false);
 const context=useRef<AudioContext|null>(null),stream=useRef<MediaStream|null>(null),chunks=useRef<Float32Array[]>([]),timer=useRef<ReturnType<typeof setInterval>|null>(null),startAt=useRef(0),callback=useRef(onAudio),node=useRef<AudioWorkletNode|null>(null),previewTask=useRef<Promise<void>|null>(null),previewAbort=useRef<AbortController|null>(null),lastPreview=useRef(0),previewCallback=useRef(onPreview),stopRef=useRef<()=>void>(()=>{});
 callback.current=onAudio;previewCallback.current=onPreview;
 useEffect(()=>{onCaptureChange?.(recording||pending||finishing);},[recording,pending,finishing,onCaptureChange]);
 useEffect(()=>()=>onCaptureChange?.(false),[onCaptureChange]);
 const release=()=>{generation.current++;recordingRef.current=false;if(node.current)node.current.port.onmessage=null;if(timer.current)clearInterval(timer.current);stream.current?.getTracks().forEach(t=>t.stop());node.current?.disconnect();void context.current?.close();stream.current=null;context.current=null;};
 const stop=async()=>{if(!recordingRef.current)return;const blob=encodeWav(chunks.current,context.current?.sampleRate||48000);release();setRecording(false);setFinishing(true);chunks.current=[];try{await previewTask.current;await callback.current(blob);}finally{setFinishing(false);}};
 stopRef.current=()=>void stop();
 useEffect(()=>{const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'&&recordingRef.current){e.preventDefault();stopRef.current();}};document.addEventListener('keydown',escape);return()=>{document.removeEventListener('keydown',escape);previewAbort.current?.abort();release();chunks.current=[];};},[]);
 const preview=()=>{
  if(!previewCallback.current||previewTask.current||!context.current)return;
  const attempt=generation.current,form=new FormData();form.append('audio',encodeWav(chunks.current,context.current.sampleRate),'preview.wav');const controller=new AbortController();previewAbort.current=controller;
  previewTask.current=(async()=>{try{const response=await fetch('/api/voice/preview',{method:'POST',credentials:'same-origin',body:form,signal:controller.signal});if(!response.ok)return;const data=await response.json();if(attempt===generation.current&&recordingRef.current){if(data.text)previewCallback.current?.(data.text);if(!data.available)setError(data.message);}}catch(e){if(!(e instanceof DOMException&&e.name==='AbortError')&&attempt===generation.current)setError('Live text is unavailable. Your recording will be checked when you stop.');}finally{previewTask.current=null;}})();
 };
 const start=async()=>{
  if(pendingRef.current||recordingRef.current||finishing)return;
  pendingRef.current=true;setError('');setPending(true);chunks.current=[];const attempt=++generation.current;
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error('Microphone access needs localhost or HTTPS. You can also upload a WAV file.');
   const acquired=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:false}});
   if(attempt!==generation.current){acquired.getTracks().forEach(track=>track.stop());return;}
   stream.current=acquired;
   await beforeStart?.();if(attempt!==generation.current)return;
   const ctx=new AudioContext();context.current=ctx;await ctx.resume();
   await ctx.audioWorklet.addModule(new URL('./capture.worklet.js',import.meta.url));
   if(attempt!==generation.current)return;
   const source=ctx.createMediaStreamSource(stream.current),capture=new AudioWorkletNode(ctx,'guestguard-capture');node.current=capture;
   capture.port.onmessage=e=>chunks.current.push(new Float32Array(e.data));
   const mute=ctx.createGain();mute.gain.value=0;source.connect(capture);capture.connect(mute);mute.connect(ctx.destination);
   setPending(false);setRecording(true);recordingRef.current=true;setSeconds(0);startAt.current=Date.now();lastPreview.current=0;
   timer.current=setInterval(()=>{const elapsed=Math.floor((Date.now()-startAt.current)/1000);setSeconds(elapsed);if(elapsed>=15){void stop();return;}if(elapsed>=4&&elapsed-lastPreview.current>=3&&!previewTask.current){lastPreview.current=elapsed;preview();}},200);
  }catch(e){release();setPending(false);setRecording(false);setError(e instanceof Error?e.message:'Microphone access failed.');}finally{pendingRef.current=false;}
 };
 const micButton=<button type="button" className={'mic-button '+(recording?'mic-active':'')} title={recording?'Stop recording (Esc)':label} aria-label={recording?'Stop recording':pending?'Requesting microphone…':label} aria-pressed={recording} disabled={(disabled||pending||finishing)&&!recording} onClick={()=>recording?void stop():void start()}>{recording?<Square size={18}/>:<Mic size={19}/>}</button>;
 const status=<span className="recording-status" role="status">{recording?<><span className="listening-dot"/>Recording · {seconds}s</>:pending?'Allow microphone access':finishing?'Checking recording…':null}</span>;
 if(compact)return <div className="compact-capture">{micButton}{(recording||pending||finishing)&&<div className="mic-feedback">{status}{recording&&<span>Audio is processed on this computer.</span>}</div>}{error&&<p className="capture-error" role="alert">{error}</p>}</div>;
 return <div className={'capture '+(recording?'recording':'')}><div className="capture-top">{micButton}<span>{recording?'Recording':pending?'Waiting for permission':finishing?'Checking recording…':'Mic off'}</span><span className="capture-clock">{seconds}s / 15s</span></div>{recording&&<div className="recording-note">{status}<span>Audio is processed on this computer.</span></div>}<div className="capture-actions"><span>Record 3–15 seconds</span><label className="button upload"><Upload size={16}/>Upload WAV<input aria-label="Upload WAV sample" type="file" accept=".wav,audio/wav" disabled={disabled||recording||pending||finishing} onChange={e=>{const file=e.target.files?.[0];if(file)void onAudio(file);e.target.value='';}}/></label></div>{error&&<p role="alert" className="error">{error}</p>}</div>;
}
