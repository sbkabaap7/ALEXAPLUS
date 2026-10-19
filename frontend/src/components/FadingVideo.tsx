import {useEffect,useRef} from 'react';

export default function FadingVideo({src,poster,className=''}:{src:string;poster:string;className?:string}){
 const videoRef=useRef<HTMLVideoElement>(null);
 useEffect(()=>{
  const video=videoRef.current;if(!video)return;
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const sync=()=>{
   if(motion.matches){video.pause();video.style.opacity='0';return;}
   if(document.hidden)return;
   void video.play().then(()=>{video.style.opacity='1';}).catch(()=>{video.style.opacity='0';});
  };
  motion.addEventListener('change',sync);
  document.addEventListener('visibilitychange',sync);
  window.addEventListener('pageshow',sync);
  window.addEventListener('focus',sync);
  video.addEventListener('canplay',sync);
  const retry=window.setInterval(()=>{if(video.paused&&!motion.matches)sync();},3000);
  sync();
  return()=>{window.clearInterval(retry);motion.removeEventListener('change',sync);document.removeEventListener('visibilitychange',sync);window.removeEventListener('pageshow',sync);window.removeEventListener('focus',sync);video.removeEventListener('canplay',sync);video.pause();};
 },[src]);
 return <video ref={videoRef} className={'scene-video '+className} src={src} poster={poster} autoPlay muted loop playsInline preload="metadata" aria-hidden="true" tabIndex={-1} style={{opacity:0}}/>;
}
