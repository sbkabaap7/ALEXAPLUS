import {useEffect,useRef,useState} from 'react';

export default function BlurText({text}:{text:string}){
 const ref=useRef<HTMLSpanElement>(null),[visible,setVisible]=useState(false);
 useEffect(()=>{
  const node=ref.current;
  if(!node)return;
  const observer=new IntersectionObserver(([entry])=>{if(entry.isIntersecting){setVisible(true);observer.disconnect();}},{threshold:.1});
  observer.observe(node);
  return()=>observer.disconnect();
 },[]);
 return <span ref={ref} className={'blur-words '+(visible?'is-visible':'')} aria-label={text}>
  {text.split(' ').map((word,index)=><span className="blur-word" aria-hidden="true" key={`${word}-${index}`} style={{animationDelay:`${index*90}ms`}}>{word}</span>)}
 </span>;
}
