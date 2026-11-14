import {useEffect,useRef,useState} from 'react';

type SpeechResult = {resultIndex:number;results:ArrayLike<ArrayLike<{transcript:string}>>};
type Recognizer = {
 continuous:boolean;interimResults:boolean;lang:string;
 onresult:((e:SpeechResult)=>void)|null;onerror:((e:{error:string})=>void)|null;
 onend:(()=>void)|null;start:()=>void;stop:()=>void;
};
type SpeechWindow = Window & {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer};

function say(text:string){
 if(!('speechSynthesis' in window))return;
 window.speechSynthesis.cancel();
 const utterance=new SpeechSynthesisUtterance(text.slice(0,1500));
 utterance.rate=0.95;window.speechSynthesis.speak(utterance);
}

/** Voice and emergency UX stay entirely within the existing React assistant view. */
export function ChartVoice({onQuestion,latestReply}:{onQuestion:(text:string)=>void;latestReply:string}){
 const [enabled,setEnabled]=useState(false);
 const [status,setStatus]=useState('Voice off');
 const [emergency,setEmergency]=useState(false);
 const [location,setLocation]=useState('');
 const recognizer=useRef<Recognizer|null>(null);
 const enabledRef=useRef(false);
 const awaiting=useRef(false);
 const callback=useRef(onQuestion);
 callback.current=onQuestion;
 useEffect(()=>{if(latestReply)say(latestReply)},[latestReply]);
 useEffect(()=>()=>{enabledRef.current=false;recognizer.current?.stop();window.speechSynthesis?.cancel()},[]);
 function emergencyMode(){
  setEmergency(true);
  setStatus('Emergency panel opened');
  say('If this is a real emergency, call local emergency services now. In the United States call 911.');
 }
 function toggle(){
  if(enabledRef.current){
   enabledRef.current=false;recognizer.current?.stop();recognizer.current=null;
   awaiting.current=false;setEnabled(false);setStatus('Voice off');return;
  }
  const speechWindow=window as SpeechWindow;
  const Constructor=speechWindow.SpeechRecognition||speechWindow.webkitSpeechRecognition;
  if(!Constructor){setStatus('Browser speech recognition unavailable. Try Chrome.');return}
  const r=new Constructor();
  r.lang='en-US';r.continuous=true;r.interimResults=false;
  r.onresult=(event)=>{
   for(let i=event.resultIndex;i<event.results.length;i++){
    const phrase=event.results[i][0]?.transcript?.trim()||'';
    const lower=phrase.toLowerCase();
    if(lower.includes('chart emergency')){awaiting.current=false;emergencyMode();return}
    if(lower.includes('chart chart')){
     const tail=phrase.slice(lower.indexOf('chart chart')+11).trim();
     if(tail){awaiting.current=false;callback.current(tail);setStatus('Question sent')}
     else{awaiting.current=true;setStatus('Chart awake — say your question')}
     return;
    }
    if(awaiting.current&&phrase){awaiting.current=false;callback.current(phrase);setStatus('Question sent')}
   }
  };
  r.onerror=e=>{setStatus('Voice issue: '+e.error)};
  r.onend=()=>{
   if(enabledRef.current){
    try{r.start()}catch{enabledRef.current=false;setEnabled(false);setStatus('Voice stopped; click Enable voice')}
   }
  };
  try{r.start();recognizer.current=r;enabledRef.current=true;setEnabled(true);setStatus('Listening for Chart Chart / Chart Emergency')}
  catch{setStatus('Microphone could not start')}
 }
 function locate(){
  if(!navigator.geolocation){setLocation('Location unavailable');return}
  navigator.geolocation.getCurrentPosition(
   pos=>setLocation('Coordinates: '+pos.coords.latitude.toFixed(5)+', '+pos.coords.longitude.toFixed(5)+'. Tell emergency dispatch manually.'),
   ()=>setLocation('Location denied or unavailable'),{enableHighAccuracy:true,timeout:8000}
  );
 }
 return <div className="panel" style={{marginBottom:18}}>
  <div style={{display:'flex',alignItems:'center',gap:12,flexWrap:'wrap'}}>
   <button type="button" className="btn primary" onClick={toggle}>{enabled?'Stop voice':'Enable voice'}</button>
   <span className="muted small" role="status">{status}</span>
   <button type="button" className="btn emergency" onClick={emergencyMode}>Chart Emergency</button>
  </div>
  <p className="muted small" style={{marginTop:12,marginBottom:0}}>Say “Chart Chart,” followed by your question. Speech recognition and notifications are browser demos, not continuous background monitoring.</p>
  {emergency&&<div role="alert" style={{marginTop:15,padding:15,background:'#fff0ee',borderRadius:12}}>
    <strong>Emergency guidance (demo)</strong>
    <p>If this is a real medical emergency, call local emergency services now (911 in the US). No call is placed automatically.</p>
    <p className="small">{location||'Your location has not been requested. It is not sent to emergency services.'}</p>
    <button className="btn ghost" type="button" onClick={locate}>Show my location</button>
    <button className="btn ghost" type="button" onClick={()=>setEmergency(false)}>Close panel</button>
   </div>}
 </div>;
}
