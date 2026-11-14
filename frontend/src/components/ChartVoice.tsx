import {useEffect,useRef,useState} from 'react';
import {Notice} from './RecoveryUI';

type SpeechResult={resultIndex:number;results:ArrayLike<ArrayLike<{transcript:string}>>};
type Recognizer={
 continuous:boolean;interimResults:boolean;lang:string;
 onresult:((event:SpeechResult)=>void)|null;onerror:((event:{error:string})=>void)|null;
 onend:(()=>void)|null;start:()=>void;stop:()=>void;
};
type SpeechWindow=Window & {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer};

/** Explicit browser voice controls; the emergency phrase only opens guidance. */
export function ChartVoice({onQuestion,latestReply,busy=false}:{onQuestion:(text:string)=>void;latestReply:string;busy?:boolean}){
 const [listening,setListening]=useState(false);const [spoken,setSpoken]=useState(false);
 const [status,setStatus]=useState('Voice off');const [emergency,setEmergency]=useState(false);
 const recognizer=useRef<Recognizer|null>(null);const awaiting=useRef(false);
 const callback=useRef(onQuestion);callback.current=onQuestion;
 const busyRef=useRef(busy);busyRef.current=busy;
 const lastSpoken=useRef(latestReply);
 const supportsOutput=typeof window.speechSynthesis!=='undefined'&&typeof window.SpeechSynthesisUtterance!=='undefined';
 useEffect(()=>{
  if(latestReply===lastSpoken.current)return;
  lastSpoken.current=latestReply;
  if(!spoken||!latestReply||!supportsOutput)return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(latestReply.slice(0,1500)));
 },[latestReply,spoken,supportsOutput]);
 useEffect(()=>()=>{
  const current=recognizer.current;
  if(current){current.onresult=null;current.onend=null;current.onerror=null;current.stop()}
  window.speechSynthesis?.cancel();
 },[]);
 function stop(){
  const current=recognizer.current;recognizer.current=null;awaiting.current=false;
  if(current){current.onresult=null;current.onend=null;current.onerror=null;current.stop()}
  setListening(false);
 }
 function openEmergency(){setEmergency(true);awaiting.current=false;setStatus('Emergency guidance opened. No one has been contacted.')}
 function toggle(){
  if(listening){stop();setStatus('Voice off');return}
  const speechWindow=window as SpeechWindow;
  const Constructor=speechWindow.SpeechRecognition||speechWindow.webkitSpeechRecognition;
  if(!Constructor){setStatus('Speech recognition is unavailable in this browser. You can still type your message.');return}
  const current=new Constructor();recognizer.current=current;
  current.lang='en-US';current.continuous=true;current.interimResults=false;
  current.onresult=event=>{
   for(let i=event.resultIndex;i<event.results.length;i++){
    const phrase=event.results[i][0]?.transcript?.trim()||'';
    if(/\bchart emergency\b/i.test(phrase)){openEmergency();return}
    if(busyRef.current||window.speechSynthesis?.speaking){setStatus('Please wait for the reply before asking again.');return}
    const wake=/\bchart chart\b/i.exec(phrase);
    if(wake){
     const question=phrase.slice(wake.index+wake[0].length).replace(/^[,.:\s]+/,'');
     awaiting.current=!question;
     if(question){callback.current(question);setStatus('Question sent')}
     else setStatus('Chart awake — say your question');
     return;
    }
    if(awaiting.current&&phrase){awaiting.current=false;callback.current(phrase);setStatus('Question sent')}
   }
  };
  current.onerror=event=>{
   stop();setStatus(event.error==='not-allowed'||event.error==='service-not-allowed'
    ?'Microphone permission was denied. You can still type your message.'
    :'Speech recognition stopped. Try enabling voice again or type your message.');
  };
  current.onend=()=>{recognizer.current=null;awaiting.current=false;setListening(false);setStatus('Voice stopped. Enable voice to listen again.')};
  try{current.start();setListening(true);setStatus('Listening for “Chart Chart” or “Chart Emergency”')}
  catch{stop();setStatus('Microphone could not start. You can still type your message.')}
 }
 return <div className="panel voice-controls">
  <div className="row-actions">
   <button type="button" className="btn ghost" aria-pressed={listening} onClick={toggle}>{listening?'Stop voice':'Enable voice'}</button>
   <label className="check-row"><input type="checkbox" checked={spoken} disabled={!supportsOutput} onChange={e=>{setSpoken(e.target.checked);if(!e.target.checked)window.speechSynthesis?.cancel()}}/>Read new replies aloud</label>
   <button type="button" className="btn emergency" onClick={openEmergency}>Chart Emergency</button>
  </div>
  <p role="status" className="muted small">{status}</p>
  <p className="muted small">Voice is optional and requires microphone permission. Say “Chart Chart” followed by your question. Your browser may send speech to its recognition service. Listening ends when you leave this page.</p>
  {!supportsOutput&&<p className="muted small">Spoken replies are unavailable in this browser.</p>}
  {emergency&&<div role="alert"><Notice>If you may be experiencing an emergency, call emergency services now (911 in the US, or your local emergency number). Do not wait for this prototype. No call is placed and no one is contacted automatically.</Notice><button type="button" className="btn ghost" onClick={()=>setEmergency(false)}>Close emergency guidance</button></div>}
 </div>;
}
