import {useEffect,useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {HeartPulse,MessageCircle,Mic,MicOff,Send,X,Plus,Volume2,VolumeX,ShieldAlert,ChevronDown} from 'lucide-react';
import {useLocation} from 'react-router-dom';
import {useSession} from '../hooks/session';
import {chatApi} from '../services/chat';
import type {Message} from '../types/api';
import {AssistantStatus} from './AssistantStatus';

type SpeechResult={resultIndex:number;results:ArrayLike<ArrayLike<{transcript:string}>>};
type Recognizer={continuous:boolean;interimResults:boolean;lang:string;onresult:((e:SpeechResult)=>void)|null;onerror:((e:{error:string})=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void};
type SpeechWindow=Window & {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer};

/** Prefer higher-quality voices already installed on the user's device. No racial identity is inferred. */
function selectVoice(voices:SpeechSynthesisVoice[]):SpeechSynthesisVoice|undefined{
 const english=voices.filter(v=>v.lang.toLowerCase().startsWith('en'));
 const preferences=[/microsoft.*(aria|jenny|ava|emma|sonia)/i,/(aria|jenny|ava|emma|sonia).*natural/i,/google.*female/i,/samantha/i,/victoria/i,/zira/i,/female/i];
 for(const pattern of preferences){const selected=english.find(v=>pattern.test(v.name));if(selected)return selected}
 return english.find(v=>v.default)||english[0];
}
function errorText(error:unknown){return error instanceof Error?error.message:'Unable to contact Clara.'}

export function ClaraAssistant(){
 const {api}=useSession();
 const {pathname}=useLocation();
 const [open,setOpen]=useState(false);
 const [messages,setMessages]=useState<Message[]>([]);
 const [conversation,setConversation]=useState('');
 const [draft,setDraft]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [speaking,setSpeaking]=useState(false);
 const [muted,setMuted]=useState(false);
 const [micActive,setMicActive]=useState(false);
 const [voiceStatus,setVoiceStatus]=useState('Tap the microphone to talk, or say “Clara” if microphone access is active.');
 const [emergency,setEmergency]=useState(false);
 const [showHistory,setShowHistory]=useState(false);
 const [history,setHistory]=useState<Array<{id:string;title:string}>>([]);
 const transcriptEnd=useRef<HTMLDivElement|null>(null);
 const input=useRef<HTMLInputElement|null>(null);
 const recognizer=useRef<Recognizer|null>(null);
 const running=useRef(false);
 const keepListening=useRef(false);
 const direct=useRef(false);
 const awaitingWake=useRef(false);
 const sending=useRef(false);
 const conversationRef=useRef('');
 const speakRef=useRef<(text:string)=>void>(()=>{});
 const sendRef=useRef<(text:string)=>void>(()=>{});
 const openRef=useRef(false);
 const muteRef=useRef(false);
 const utteranceRef=useRef<SpeechSynthesisUtterance|null>(null);
 openRef.current=open;muteRef.current=muted;

 useEffect(()=>{if(pathname==='/assistant')setOpen(true)},[pathname]);
 useEffect(()=>{if(open)transcriptEnd.current?.scrollIntoView({block:'end',behavior:'smooth'})},[open,messages,busy]);
 useEffect(()=>{if(open)input.current?.focus()},[open]);
 useEffect(()=>{if(open)chatApi(api).list().then(items=>setHistory(items)).catch(()=>{/* history optional */})},[open,api]);

 function speak(text:string){
  if(muteRef.current||!('speechSynthesis' in window))return;
  window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text.replace(/[*#_]/g,'').slice(0,2600));
  utterance.voice=selectVoice(window.speechSynthesis.getVoices())||null;
  utterance.lang=utterance.voice?.lang||'en-US';
  utterance.rate=.94;utterance.pitch=1.04;utterance.volume=1;
  utterance.onstart=()=>setSpeaking(true);
  utterance.onend=()=>{setSpeaking(false);utteranceRef.current=null};
  utterance.onerror=()=>{setSpeaking(false);utteranceRef.current=null};
  utteranceRef.current=utterance;
  window.speechSynthesis.speak(utterance);
 }
 speakRef.current=speak;
 async function sendMessage(raw:string){
  const message=raw.trim();
  if(!message||sending.current)return;
  sending.current=true;setBusy(true);setError('');setOpen(true);setDraft('');
  // Show what the user said while the response is being generated.
  const optimisticId='local-'+Date.now().toString();
  setMessages(previous=>[...previous,{id:optimisticId,role:'user',content:message,created_at:new Date().toISOString(),updated_at:new Date().toISOString()}]);
  try{
   const reply=await chatApi(api).send(message,conversationRef.current||undefined);
   conversationRef.current=reply.conversation_id;setConversation(reply.conversation_id);
   setMessages(previous=>[...previous.filter(item=>item.id!==optimisticId),reply.user_message,reply.assistant_message]);
   chatApi(api).list().then(items=>setHistory(items)).catch(()=>{/* history optional */});
   speakRef.current(reply.assistant_message.content);
  }catch(e){
   setMessages(previous=>previous.filter(item=>item.id!==optimisticId));
   setDraft(message);setError(errorText(e));
  }finally{sending.current=false;setBusy(false)}
 }
 sendRef.current=(value:string)=>{void sendMessage(value)};
 function submit(e:FormEvent){e.preventDefault();void sendMessage(draft)}
 function resetConversation(){conversationRef.current='';setConversation('');setMessages([]);setDraft('');setError('');setShowHistory(false)}
 async function selectConversation(id:string){
  setError('');setShowHistory(false);
  try{const item=await chatApi(api).get(id);conversationRef.current=id;setConversation(id);setMessages(item.messages||[])}
  catch(e){setError(errorText(e))}
 }
 function showEmergency(){
  setOpen(true);setEmergency(true);setMicActive(false);direct.current=false;awaitingWake.current=false;
  if('speechSynthesis' in window)window.speechSynthesis.cancel();
  setSpeaking(false);
  setVoiceStatus('Emergency guidance opened. No emergency call is placed.');
 }
 useEffect(()=>{
  const browser=window as SpeechWindow;
  const Ctor=browser.SpeechRecognition||browser.webkitSpeechRecognition;
  if(!Ctor){setVoiceStatus('Speech recognition is unavailable in this browser. You can type to Clara.');return}
  const r=new Ctor();
  recognizer.current=r;r.lang='en-US';r.continuous=true;r.interimResults=false;
  r.onresult=event=>{
   for(let i=event.resultIndex;i<event.results.length;i++){
    const phrase=event.results[i][0]?.transcript?.trim()||'';
    if(!phrase)continue;
    const lower=phrase.toLowerCase();
    if(/^emergency([\s.!?,]|$)/i.test(phrase)){showEmergency();return}
    // The wake phrase and name have replaced "Chart Chart".
    const match=/\bclara\b/i.exec(phrase);
    if(match){
     setOpen(true);
     const remainder=phrase.slice(match.index+match[0].length).trim();
     if(remainder){direct.current=false;awaitingWake.current=false;setMicActive(false);sendRef.current(remainder)}
     else{awaitingWake.current=true;direct.current=false;setMicActive(true);setVoiceStatus('Clara is listening — ask your question.')}
     return;
    }
    if(direct.current||awaitingWake.current){
     direct.current=false;awaitingWake.current=false;setMicActive(false);
     setVoiceStatus('Question sent. Say Clara to ask another.');
     sendRef.current(phrase);return;
    }
   }
  };
  r.onerror=event=>{
   if(event.error==='not-allowed'||event.error==='service-not-allowed'){
    keepListening.current=false;running.current=false;direct.current=false;awaitingWake.current=false;
    setMicActive(false);setVoiceStatus('Microphone access was blocked. Allow it in browser settings and try again.');
   }else if(event.error!=='no-speech'&&event.error!=='aborted'){
    setVoiceStatus('Voice issue: '+event.error+'. Tap the mic to retry.');
   }
  };
  r.onend=()=>{
   running.current=false;
   if(keepListening.current){
    try{r.start();running.current=true}
    catch{keepListening.current=false;direct.current=false;setMicActive(false);setVoiceStatus('Voice paused. Tap the mic to restart.')}
   }
  };
  // Best effort only: browser permissions often prevent microphone startup without a click.
  try{r.start();running.current=true;keepListening.current=true;setVoiceStatus('Say “Clara” or tap the microphone to speak.')}
  catch{/* User can grant microphone access by tapping the microphone inside the panel. */}
  return()=>{
   keepListening.current=false;r.onresult=null;r.onerror=null;r.onend=null;
   try{r.stop()}catch{/* already stopped */}
   recognizer.current=null;
   if('speechSynthesis' in window)window.speechSynthesis.cancel();
  };
 },[]);
 function tapMic(){
  const r=recognizer.current;
  if(!r){setVoiceStatus('Speech recognition unavailable. Please type your question.');return}
  if(direct.current||awaitingWake.current){
   direct.current=false;awaitingWake.current=false;setMicActive(false);
   setVoiceStatus('Direct listening stopped. Say Clara for hands-free use.');return;
  }
  direct.current=true;awaitingWake.current=false;setMicActive(true);setVoiceStatus('Listening — ask your question now.');
  if(!running.current){
   try{keepListening.current=true;r.start();running.current=true}
   catch{direct.current=false;setMicActive(false);setVoiceStatus('Could not start microphone. Check permissions and try again.')}
  }
 }
 function toggleMute(){
  const next=!muted;setMuted(next);muteRef.current=next;
  if(next&&'speechSynthesis' in window){window.speechSynthesis.cancel();setSpeaking(false)}
 }
 return <>
   {!open&&<button type="button" className="clara-launcher" onClick={()=>setOpen(true)} aria-label="Open Clara recovery assistant" title="Ask Clara">
     <HeartPulse size={28}/><span>Clara</span>
   </button>}
   {open&&<section className="clara-window" role="dialog" aria-label="Clara recovery assistant">
     <header className="clara-header">
       <span className="clara-mark"><HeartPulse size={23}/></span>
       <div className="clara-heading"><strong>Clara</strong><span>Your recovery companion · demo</span></div>
       <button type="button" aria-label={muted?'Unmute Clara voice':'Mute Clara voice'} title={muted?'Unmute voice':'Mute voice'} className="clara-icon-btn" onClick={toggleMute}>{muted?<VolumeX size={19}/>:<Volume2 size={19}/>}</button>
       <button type="button" aria-label="Minimize Clara" title="Minimize" className="clara-icon-btn" onClick={()=>setOpen(false)}><ChevronDown size={20}/></button>
       <button type="button" aria-label="Close Clara" title="Close" className="clara-icon-btn" onClick={()=>setOpen(false)}><X size={20}/></button>
     </header>
     <div className="clara-toolbar">
       <button type="button" onClick={resetConversation}><Plus size={15}/> New chat</button>
       <button type="button" onClick={()=>setShowHistory(value=>!value)} aria-expanded={showHistory}><MessageCircle size={15}/> History</button>
       <button type="button" className="clara-safety-link" onClick={showEmergency}><ShieldAlert size={15}/> Emergency</button>
     </div>
     {showHistory&&<div className="clara-history" aria-label="Recent conversations">
       {history.length?history.slice(0,12).map(item=><button type="button" key={item.id} className={conversation===item.id?'current':''} onClick={()=>{void selectConversation(item.id)}}>{item.title||'Recovery conversation'}</button>):<p>No past chats yet.</p>}
     </div>}
     {emergency&&<div className="clara-emergency" role="alert">
       <strong>Emergency guidance</strong>
       <p>If this is a real emergency, call local emergency services now (911 in the US). Clara cannot dispatch emergency help or monitor your condition.</p>
       <button type="button" onClick={()=>setEmergency(false)}>Dismiss</button>
     </div>}
     <div className="clara-chat-scroll" aria-live="polite">
       {messages.length===0&&<div className="clara-welcome"><span className="clara-welcome-icon"><HeartPulse size={28}/></span><h3>Hi, I'm Clara.</h3><p>Ask me about general recovery information or records saved in UR Chart. I'm a fictional-data educational assistant, not a clinician.</p><button type="button" onClick={()=>{setDraft('What should I ask my care team about recovery?');input.current?.focus()}}>Help me prepare questions</button></div>}
       {messages.map(item=><div key={item.id} className={'clara-message '+(item.role==='user'?'clara-user':'clara-reply')}><span>{item.role==='user'?'You':'Clara'}</span><p>{item.content}</p></div>)}
       <AssistantStatus thinking={busy} speaking={speaking}/>
       <div ref={transcriptEnd}/>
     </div>
     {error&&<div className="clara-error" role="alert">{error}</div>}
     <div className="clara-voice-info" role="status">{voiceStatus}</div>
     <form className="clara-compose" onSubmit={submit}>
       <button type="button" className={'clara-mic'+(micActive?' is-listening':'')} onClick={tapMic} aria-label={micActive?'Stop listening':'Speak to Clara without wake word'} aria-pressed={micActive}>{micActive?<MicOff size={19}/>:<Mic size={19}/>}</button>
       <input ref={input} aria-label="Message Clara" value={draft} onChange={event=>setDraft(event.target.value)} maxLength={4000} placeholder="Ask Clara anything about recovery..." />
       <button type="submit" aria-label="Send to Clara" disabled={busy||!draft.trim()} className="clara-send"><Send size={19}/></button>
     </form>
     <div className="clara-footer">Synthetic demo · Not emergency monitoring or medical advice</div>
   </section>}
 </>;
}
