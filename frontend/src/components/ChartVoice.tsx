import {useEffect,useRef,useState} from 'react';
import {Mic, MicOff} from 'lucide-react';

type SpeechResult = {resultIndex:number;results:ArrayLike<ArrayLike<{transcript:string}>>};
type Recognizer = {
 continuous:boolean;interimResults:boolean;lang:string;
 onresult:((e:SpeechResult)=>void)|null;onerror:((e:{error:string})=>void)|null;
 onend:(()=>void)|null;start:()=>void;stop:()=>void;
};
type SpeechWindow = Window & {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer};

function say(text:string, onSpeakingChange:(speaking:boolean)=>void){
 if(!('speechSynthesis' in window))return;
 window.speechSynthesis.cancel();
 const utterance=new SpeechSynthesisUtterance(text.slice(0,1500));
 utterance.rate=0.95;
 utterance.onstart=()=>onSpeakingChange(true);
 utterance.onend=()=>onSpeakingChange(false);
 utterance.onerror=()=>onSpeakingChange(false);
 window.speechSynthesis.speak(utterance);
}

/**
 * Button: one-tap, no wake phrase required. Hands-free wake phrase: "Chart Chart"
 * whenever browser recognition has been allowed and can continue running.
 * The browser may deny automatic microphone startup until a user interaction.
 */
export function ChartVoice({onQuestion,latestReply,onSpeakingChange}:{onQuestion:(text:string)=>void;latestReply:string;onSpeakingChange:(speaking:boolean)=>void}){
 const [listening,setListening]=useState(false);
 const [directMode,setDirectMode]=useState(false);
 const [status,setStatus]=useState('Tap the microphone to speak, or say Chart Chart when voice is active.');
 const [emergency,setEmergency]=useState(false);
 const [location,setLocation]=useState('');
 const recognizer=useRef<Recognizer|null>(null);
 const running=useRef(false);
 const keepListening=useRef(false);
 const direct=useRef(false);
 const awaitingWake=useRef(false);
 const callback=useRef(onQuestion);
 const speakingCallback=useRef(onSpeakingChange);
 callback.current=onQuestion;
 speakingCallback.current=onSpeakingChange;

 useEffect(()=>{if(latestReply)say(latestReply, value=>speakingCallback.current(value))},[latestReply]);

 useEffect(()=>{
  const speechWindow=window as SpeechWindow;
  const Constructor=speechWindow.SpeechRecognition||speechWindow.webkitSpeechRecognition;
  if(!Constructor){
   setStatus('Speech recognition is unavailable in this browser. Try Chrome.');
   return;
  }
  const r=new Constructor();
  r.lang='en-US';r.continuous=true;r.interimResults=false;
  recognizer.current=r;
  const submit=(value:string)=>{
   const question=value.trim();
   if(!question)return;
   direct.current=false;awaitingWake.current=false;
   setDirectMode(false);setStatus('Question sent. Say Chart Chart to ask another.');
   callback.current(question);
  };
  const activateEmergency=()=>{
   direct.current=false;awaitingWake.current=false;
   setDirectMode(false);setEmergency(true);setStatus('Emergency guidance opened');
   say('If this is a real emergency, call local emergency services now. In the United States call 911.',value=>speakingCallback.current(value));
  };
  r.onresult=event=>{
   for(let i=event.resultIndex;i<event.results.length;i++){
    const phrase=event.results[i][0]?.transcript?.trim()||'';
    if(!phrase)continue;
    const lower=phrase.toLowerCase();
    if(lower.includes('chart emergency')){activateEmergency();return}
    if(lower.includes('chart chart')){
     const tail=phrase.slice(lower.indexOf('chart chart')+'chart chart'.length).trim();
     if(tail)submit(tail);
     else {
      direct.current=false;awaitingWake.current=true;
      setDirectMode(true);setStatus('Chart awake — say your question');
     }
     return;
    }
    if(direct.current||awaitingWake.current){submit(phrase);return}
   }
  };
  r.onerror=e=>{
   if(e.error==='not-allowed'||e.error==='service-not-allowed'){
    keepListening.current=false;running.current=false;
    direct.current=false;awaitingWake.current=false;
    setListening(false);setDirectMode(false);
    setStatus('Microphone blocked. Allow access in browser settings, then tap the mic.');
   }else if(e.error!=='no-speech'&&e.error!=='aborted'){
    setStatus('Voice issue: '+e.error+'. Tap the mic to retry.');
   }
  };
  r.onend=()=>{
   running.current=false;setListening(false);
   if(keepListening.current){
    try{r.start();running.current=true;setListening(true)}
    catch{
     keepListening.current=false;direct.current=false;setDirectMode(false);
     setStatus('Voice paused. Tap the mic to resume.');
    }
   }
  };
  // Try hands-free wake listening if the browser already permits it.
  // Browsers often require an explicit click before first microphone activation.
  try{r.start();running.current=true;keepListening.current=true;setListening(true);setStatus('Say Chart Chart, or tap the mic to speak directly.')}
  catch{/* The microphone button provides the user-initiated start path. */}
  return ()=>{
   keepListening.current=false;running.current=false;
   r.onend=null;r.onresult=null;r.onerror=null;
   try{r.stop()}catch{/* already stopped */}
   recognizer.current=null;
   window.speechSynthesis?.cancel();
   speakingCallback.current(false);
  };
 },[]);

 function micClick(){
  const r=recognizer.current;
  if(!r){setStatus('Speech recognition is unavailable in this browser.');return}
  if(direct.current){
   direct.current=false;awaitingWake.current=false;setDirectMode(false);
   setStatus('Direct listening stopped. Say Chart Chart for hands-free use.');
   return;
  }
  direct.current=true;awaitingWake.current=false;setDirectMode(true);
  setStatus('Listening — ask your question now (no wake phrase needed).');
  if(!running.current){
   try{
    keepListening.current=true;r.start();running.current=true;setListening(true);
   }catch{
    direct.current=false;keepListening.current=false;setDirectMode(false);
    setStatus('Could not access microphone. Check browser permission, then retry.');
   }
  }
 }
 function emergencyMode(){
  direct.current=false;awaitingWake.current=false;setDirectMode(false);
  setEmergency(true);setStatus('Emergency guidance opened');
  say('If this is a real emergency, call local emergency services now. In the United States call 911.',value=>speakingCallback.current(value));
 }
 function locate(){
  if(!navigator.geolocation){setLocation('Location unavailable');return}
  navigator.geolocation.getCurrentPosition(
   pos=>setLocation('Coordinates: '+pos.coords.latitude.toFixed(5)+', '+pos.coords.longitude.toFixed(5)+'. Tell emergency dispatch manually.'),
   ()=>setLocation('Location denied or unavailable'),{enableHighAccuracy:true,timeout:8000}
  );
 }
 return <>
  <div className="chart-voice-hint" role="status">
    <span>{status}</span>
    <span className="muted small">{listening?'Hands-free wake listening active':'Wake listening may require microphone permission'}</span>
    <button type="button" className="btn emergency" onClick={emergencyMode}>Chart Emergency</button>
  </div>
  {emergency&&<div className="panel" role="alert" style={{marginBottom:18,background:'#fff0ee'}}>
    <strong>Emergency guidance (demo)</strong>
    <p>If this is a real medical emergency, call local emergency services now (911 in the US). No call is placed automatically.</p>
    <p className="small">{location||'Your location has not been requested. It is not sent to emergency services.'}</p>
    <button className="btn ghost" type="button" onClick={locate}>Show my location</button>
    <button className="btn ghost" type="button" onClick={()=>setEmergency(false)}>Close panel</button>
  </div>}
  <button
    type="button"
    className={'chart-voice-fab'+(directMode?' chart-voice-fab-active':'')}
    aria-label={directMode?'Stop direct voice listening':'Talk to Chart without saying Chart Chart'}
    aria-pressed={directMode}
    title={directMode?'Stop listening':'Tap to speak to Chart'}
    onClick={micClick}
  >
   {directMode?<MicOff size={27} strokeWidth={2.2}/>:<Mic size={27} strokeWidth={2.2}/>}
   <span className="chart-voice-fab-indicator" aria-hidden="true"/>
  </button>
 </>;
}
