import {useEffect,useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {ArrowRight,HeartPulse,MessageCircle,Plus,Send} from 'lucide-react';
import {useSession} from '../hooks/session';
import {useResource} from '../hooks/useResource';
import {chatApi} from '../services/chat';
import {ErrorState,Loader,PageIntro} from '../components/UI';
import type {Message} from '../types/api';
import {messageOf} from '../services/presentation';
import {ChartVoice} from '../components/ChartVoice';

export function AssistantPage(){
 const {api}=useSession();const conversations=useResource(()=>chatApi(api).list(),[api]);
 const [current,setCurrent]=useState('');const [messages,setMessages]=useState<Message[]>([]);
 const [draft,setDraft]=useState('');const [working,setWorking]=useState(false);
 const [error,setError]=useState('');const [historyBusy,setHistoryBusy]=useState(false);
 const [latestReply,setLatestReply]=useState('');const [replyId,setReplyId]=useState('');const generation=useRef(0);const sending=useRef(false);
 useEffect(()=>()=>{generation.current++},[api]);
 function startConversation(){generation.current++;setCurrent('');setMessages([]);setLatestReply('');setError('');setHistoryBusy(false)}
 async function load(id:string){
  if(sending.current)return;
  const request=++generation.current;setCurrent(id);setHistoryBusy(true);setMessages([]);setLatestReply('');setError('');
  try{const record=await chatApi(api).get(id);if(request===generation.current)setMessages(record.messages||[])}
  catch(e){if(request===generation.current)setError(messageOf(e))}
  finally{if(request===generation.current)setHistoryBusy(false)}
 }
 async function sendText(text:string){
  const message=text.trim();if(!message||sending.current||historyBusy)return;
  sending.current=true;setWorking(true);setError('');const request=++generation.current;
  try{
   const result=await chatApi(api).send(message,current||undefined);
   if(request!==generation.current)return;
   setCurrent(result.conversation_id);setMessages(previous=>[...previous,result.user_message,result.assistant_message]);
   setLatestReply(result.assistant_message.content);setReplyId(result.assistant_message.id);setDraft('');conversations.reload();
  }catch(e){if(request===generation.current)setError(messageOf(e))}
  finally{sending.current=false;if(request===generation.current)setWorking(false)}
 }
 function send(e:FormEvent){e.preventDefault();void sendText(draft)}
 return <><PageIntro eyebrow="SUPPORT ON YOUR TERMS" title="Recovery assistant" subtitle="Approved instructions with optional local AI. Replies identify their source. This prototype cannot diagnose or offer personalized medical advice."/><ChartVoice onQuestion={text=>void sendText(text)} latestReply={latestReply} replyId={replyId} busy={working||historyBusy}/><div className="assistant-layout"><aside className="assistant-conversations"><button className="btn primary wide" disabled={working} onClick={startConversation}><Plus size={17}/>New conversation</button><h3>Conversations</h3>{conversations.loading?<Loader/>:conversations.error?<ErrorState message={conversations.error} onRetry={conversations.reload}/>:conversations.data?.length?conversations.data.map(c=><button key={c.id} className={'conversation-link '+(current===c.id?'selected':'')} disabled={working} onClick={()=>load(c.id)}><MessageCircle size={16}/><span>{c.title||'Recovery conversation'}</span></button>):<p className="muted small">No previous conversations.</p>}</aside><section className="assistant-chat"><div className="assistant-header"><span className="assistant-avatar"><HeartPulse size={21}/></span><div><b>UR Chart recovery assistant</b><p>Educational prototype • response source shown in each reply</p></div><span className="status-tag enabled">Demo</span></div><div className="assistant-messages" aria-live="polite">{historyBusy?<Loader/>:messages.length?messages.map(m=><div className={'chat-bubble '+(m.role==='user'?'mine':'theirs')} key={m.id}><small>{m.role==='user'?'You':'UR Chart'}</small><p>{m.content}</p></div>):<div className="chat-placeholder"><div className="assistant-avatar large"><MessageCircle size={30}/></div><h2>What can I help clarify?</h2><p>Hosted chat quotes approved instructions. Optional local AI describes your recorded information and falls back to approved instructions if unavailable.</p><div className="prompt-suggestions">{['What does my approved recovery plan say?','What questions could I ask my care team?'].map(s=><button key={s} onClick={()=>setDraft(s)}>{s}<ArrowRight size={14}/></button>)}</div></div>}</div>{error&&<ErrorState message={error}/>}<form className="assistant-compose" onSubmit={send}><input aria-label="Message to recovery assistant" maxLength={4000} placeholder="Ask about recovery instructions…" value={draft} disabled={working||historyBusy} onChange={e=>setDraft(e.target.value)}/><button className="btn primary" disabled={working||historyBusy||!draft.trim()} aria-label="Send message"><Send size={18}/></button></form><div className="assistant-disclaimer">Not a clinician. Chat does not create reminders or contact your care team or emergency services.</div></section></div></>}
