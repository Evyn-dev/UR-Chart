import {useEffect,useState} from 'react';
import {Link,useNavigate,useSearchParams} from 'react-router-dom';
import {AlertTriangle,Bell,CalendarDays,Check,ClipboardList,HeartHandshake,HeartPulse,MapPin,MessageCircle,PhoneCall,Pill,ShieldAlert,UserRound,Printer} from 'lucide-react';
import {useSession} from '../hooks/session';
import {caregiversApi} from '../services/caregivers';
import {checkinsApi} from '../services/checkins';
import {medicationsApi} from '../services/medications';
import type {Checkin,MedicationSummary,Relationship} from '../types/api';

type Contact={relationship_id:string;priority:number;enabled:boolean;contact_name:string;caregiver_opted_in:boolean;phone_last_four:string|null};
type Attempt={relationship_id?:string;priority:number;sms:string;call:string;attempted_at:string};
type Event={id:string;created_at:string;status:string;share_location:boolean;location:string|null;notifications:Attempt[];acknowledged_at:string|null;acknowledged_by:string|null;patient_name?:string};
type Briefing={day:string;patient_name:string;scheduled_doses:number;doses_without_recorded_status:number;checkin_recorded:boolean;upcoming_appointments:Array<{title:string;date_time:string}>;message:string};
type Prep={patient_name:string;from:string;through:string;checkins:Array<{day:string;pain:number|null;wellbeing:number|null;activity_minutes:number|null;symptoms:string[];note:string|null}>;medications:Array<{name:string;dosage:string;schedule:string}>;dose_log_counts:Record<string,number>;suggested_questions:string[];notice:string};
type Appointment={id:string;date_time:string;title:string;place:string|null;notes:string|null};
type Note={id:string;body:string;created_at:string;relationship_id:string;author:string};

function useFetch<T>(path:string|null){
 const {api}=useSession();const [value,setValue]=useState<T|null>(null);const [error,setError]=useState('');
 const refresh=()=>{if(path)api<T>(path).then(setValue).catch(e=>setError(e instanceof Error?e.message:'Unable to load'))};
 useEffect(()=>{setValue(null);setError('');refresh()},[api,path]);
 return {value,error,refresh};
}
function errorMsg(e:unknown){return e instanceof Error?e.message:'Could not complete that action'}
function DateText({value}:{value:string}){return <>{new Date(value).toLocaleString()}</>}
function Page({title,detail,children}:{title:string;detail:string;children:React.ReactNode}){return <div className="eng-page"><div className="eng-intro"><div className="eyebrow">UR CHART · RECOVERY SUPPORT</div><h1>{title}</h1><p>{detail}</p></div>{children}</div>}
function Panel({title,children}:{title:string;children:React.ReactNode}){return <section className="eng-panel"><h2>{title}</h2>{children}</section>}
function Notice(){return <p className="eng-disclaimer"><ShieldAlert size={17}/> Fictional hackathon demonstration. This app is not medical monitoring, emergency dispatch, or a substitute for 911.</p>}
function Banner({text,error=false}:{text:string;error?:boolean}){return <div role="status" className={'eng-banner'+(error?' eng-error':'')}>{text}</div>}

export function EmergencyConnect(){
 const {api,role}=useSession();const [searchParams,setSearchParams]=useSearchParams();
 const {value:contacts,refresh:refreshContacts}=useFetch<Contact[]>(role==='patient'?'/engagement/contacts':null);
 const {value:history,refresh:refreshHistory}=useFetch<Event[]>(role==='patient'?'/engagement/emergencies':'/engagement/caregiver/emergencies');
 const {value:prep}=useFetch<Prep>(role==='patient'?'/engagement/visit-prep':null);
 const {value:relationships}=useFetch<Relationship[]>(role==='patient'?'/caregivers':'/caregiver/relationships');
 const [sending,setSending]=useState(false);const [location,setLocation]=useState('');const [locSharing,setLocSharing]=useState(false);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');const [caregiverPhone,setCaregiverPhone]=useState('');
 const [contactName,setContactName]=useState('Caregiver');const [priority,setPriority]=useState(1);
 const activate=async()=>{if(sending)return;setSending(true);setError('');setNotice('');
  try{const result=await api<Event>('/engagement/emergencies','POST',{share_location:locSharing,location:locSharing?location:null});
   refreshHistory();setNotice(result.notifications.some(x=>x.sms==='provider_accepted'||x.call==='provider_accepted')?
    'Notification provider accepted a request. Delivery and caregiver response are not guaranteed.':'Emergency mode activated. No real caregiver message or phone call was sent in demo mode.');}
  catch(e){setError(errorMsg(e))}finally{setSending(false)}
 };
 useEffect(()=>{if(role==='patient'&&searchParams.get('activate')==='1'){
  setSearchParams({}, {replace:true});void activate();
 }},[role,searchParams,setSearchParams]);
 const shareLocation=()=>{
  if(!navigator.geolocation){setError('Location access is not available.');return}
  navigator.geolocation.getCurrentPosition(position=>{
   setLocation(position.coords.latitude.toFixed(5)+', '+position.coords.longitude.toFixed(5));
   setLocSharing(true);setNotice('Location ready to share on your next emergency activation.');},
   ()=>setError('Location permission was denied. Emergency mode still works without location.'),
   {enableHighAccuracy:false,timeout:8000,maximumAge:60000});
 };
 const configure=async(id:string,enabled:boolean,rank:number,name:string)=>{
  setError('');try{await api('/engagement/contacts','POST',{relationship_id:id,enabled,priority:rank,contact_name:name});refreshContacts();setNotice('Emergency contact preference saved. The caregiver must also consent to receiving calls or texts.')}
  catch(e){setError(errorMsg(e))}
 };
 const optIn=async(id:string)=>{
  try{await api('/engagement/contacts/opt-in','POST',{relationship_id:id,phone:caregiverPhone,consent:true});setNotice('Phone opt-in saved. Only patient-approved emergency contacts can receive notifications.');setCaregiverPhone('')}
  catch(e){setError(errorMsg(e))}
 };
 const ack=async(id:string)=>{try{await api('/engagement/caregiver/emergencies/'+id+'/acknowledge','POST',{});refreshHistory();setNotice('Acknowledgment recorded. This does not dispatch medical help.')}catch(e){setError(errorMsg(e))}};
 const escalate=async(id:string)=>{try{await api('/engagement/emergencies/'+id+'/escalate','POST',{});refreshHistory();setNotice('Secondary caregiver attempt recorded; check delivery status below.')}catch(e){setError(errorMsg(e))}};
 const activeRelationships=(relationships||[]).filter(r=>r.status==='active');
 return <Page title="Clara Emergency Connect" detail="Open immediate emergency options and coordinate with consenting caregivers.">
  <Notice/>
  <div className="eng-emergency">
   <AlertTriangle size={30}/>
   <div><h2>Emergency assistance</h2><p>For severe chest pain, serious breathing problems, stroke symptoms, or collapse, contact emergency services immediately. Never wait for an app notification.</p></div>
   <a className="eng-call" href="tel:911"><PhoneCall size={19}/> Call 911</a>
  </div>
  {role==='patient'&&<>
   <Panel title="Emergency actions">
    <p>Activating this records an event and attempts to notify consenting caregivers if a real notification provider has been securely configured. Demo mode does not send calls or texts.</p>
    <div className="eng-actions"><button className="btn primary" disabled={sending} onClick={()=>void activate()}><ShieldAlert size={18}/>{sending?'Activating…':'Notify my caregiver'}</button>
    <button className="btn secondary" type="button" onClick={shareLocation}><MapPin size={18}/> Allow location for next alert</button>
    {locSharing&&<button type="button" className="btn secondary" onClick={()=>{setLocSharing(false);setLocation('')}}>Stop sharing location</button>}</div>
    <small>{locSharing?'Your approximate GPS coordinates will be included if you activate the alert.':'No location is shared without permission.'}</small>
   </Panel>
   <Panel title="Emergency medical card">
    <p><strong>Patient:</strong> {prep?.patient_name||'Loading patient record…'}</p>
    <p><strong>Allergies:</strong> Not entered as a verified structured allergy record. Check your medical paperwork.</p>
    <p><strong>Recorded medications:</strong></p>
    <ul>{prep?.medications.map(m=><li key={m.name}>{m.name} — {m.dosage}</li>)||<li>Loading medication list…</li>}</ul>
    <p><strong>Conditions and procedures:</strong> Refer to the patient's approved discharge plan; unverified demo narratives are not medical diagnoses.</p>
    <p><strong>Caregiver contacts:</strong> {contacts?.filter(c=>c.enabled).map(c=>c.contact_name).join(', ')||'None configured'}</p>
   </Panel>
   <Panel title="Choose your emergency contacts">
    <p>First invite your caregiver through <Link to="/caregivers">Caregiver access</Link>. After they accept, enable them here. They must separately consent to using their phone number.</p>
    {activeRelationships.length===0?<p>No accepted caregiver relationships yet.</p>:activeRelationships.map(r=>{
     const c=contacts?.find(x=>x.relationship_id===r.id);
     return <div className="eng-contact" key={r.id}>
      <b>{c?.contact_name||'Caregiver'} · {c?.priority===2?'Secondary':'Primary'}</b>
      <small>{c?.caregiver_opted_in?'Phone opt-in confirmed (••••'+(c.phone_last_four||'')+')':'Caregiver phone opt-in pending'}</small>
      <div className="eng-actions">
       <button type="button" className="btn secondary" onClick={()=>void configure(r.id,!c?.enabled,c?.priority||1,c?.contact_name||'Caregiver')}>{c?.enabled?'Disable alerts':'Enable alerts'}</button>
       <button type="button" className="btn secondary" onClick={()=>void configure(r.id,c?.enabled||false,c?.priority===2?1:2,c?.contact_name||'Caregiver')}>Set as {c?.priority===2?'primary':'secondary'}</button>
      </div>
     </div>})}
   </Panel>
  </>}
  {role==='caregiver'&&<Panel title="Opt in to emergency calls and texts">
   <p>Only you can provide a phone number for notifications. Accept the patient's invitation and grant consent before any real messaging can occur.</p>
   {activeRelationships.map(r=><div className="eng-contact" key={r.id}><b>Approved patient relationship</b><label>My phone (international format)<input value={caregiverPhone} onChange={e=>setCaregiverPhone(e.target.value)} placeholder="+15551234567" autoComplete="tel"/></label><button className="btn primary" onClick={()=>void optIn(r.id)}>Consent to notifications</button><p><small>Demo mode never sends real calls or SMS.</small></p></div>)}
   {activeRelationships.length===0&&<p>There are no accepted invitations yet.</p>}
  </Panel>}
  <Panel title={role==='caregiver'?'Patient alerts you can acknowledge':'Recent emergency activations'}>
   {!history?<p>Loading emergency events…</p>:history.length===0?<p>No emergency activations recorded yet.</p>:history.map(e=><article className="eng-event" key={e.id}>
    <div><strong>{e.patient_name||'Emergency Connect'} · {e.status}</strong><small><DateText value={e.created_at}/></small></div>
    {e.acknowledged_at?<p><Check size={16}/> Acknowledged at <DateText value={e.acknowledged_at}/></p>:<p>No caregiver acknowledgment recorded.</p>}
    {e.notifications?.map((a,i)=><p key={i}><small>{a.priority===1?'Primary':'Secondary'}: SMS {a.sms.replaceAll('_',' ')} · Call {a.call.replaceAll('_',' ')}</small></p>)}
    {e.location&&<p><MapPin size={15}/> Location shared with this alert: {e.location}</p>}
    {role==='caregiver'&&!e.acknowledged_at&&<button className="btn primary" onClick={()=>void ack(e.id)}>Acknowledge alert</button>}
    {role==='patient'&&!e.acknowledged_at&&<button className="btn secondary" onClick={()=>void escalate(e.id)}>Attempt secondary caregiver (after 2 minutes)</button>}
   </article>)}
  </Panel>
  {notice&&<Banner text={notice}/>}
  {error&&<Banner text={error} error/>}
 </Page>
}

export function DailyBriefing(){
 const {value:brief,error}=useFetch<Briefing>('/engagement/daily-briefing');
 const {value:summary}=useFetch<MedicationSummary>('/medications/summary');
 return <Page title="Clara's daily briefing" detail="A simple summary of recorded tasks and upcoming plans — refreshed when you open this page.">
  <Notice/>{error&&<Banner text={error} error/>}
  <Panel title={brief?'Good day, '+brief.patient_name.split(' ')[0]+' · '+brief.day:'Loading your briefing…'}>
   {brief&&<><p><Pill size={18}/> {brief.scheduled_doses} scheduled medication doses today, with {brief.doses_without_recorded_status} not yet confirmed.</p>
    <p><ClipboardList size={18}/> Today's check-in: <strong>{brief.checkin_recorded?'Recorded':'Not recorded yet'}</strong></p>
    <p><CalendarDays size={18}/> Upcoming appointments: {brief.upcoming_appointments.length||'None saved'}</p>
    {brief.upcoming_appointments.map((a,i)=><p key={i}><DateText value={a.date_time}/> — {a.title}</p>)}
    <p>{brief.message}</p>
   </>}
  </Panel>
  <Panel title="Medication watchlist">
   <p>Unrecorded is not the same as missed. Review your schedule and record what actually happened.</p>
   {summary?.medications.map(m=>{
    const adherence=summary.adherence[m.id];
    return <p key={m.id}><strong>{m.name}</strong> — {adherence?.overdue_unrecorded||0} overdue unrecorded · {adherence?.confirmed_missed||0} confirmed missed</p>
   })||<p>Loading medication status…</p>}
   <Link to="/medications" className="btn secondary">Review medications</Link>
  </Panel>
  <div className="eng-actions"><Link to="/check-in" className="btn primary">Record today's check-in</Link><Link to="/appointments" className="btn secondary">Appointments</Link><Link to="/doctor-visit" className="btn secondary">Prepare for a doctor visit</Link></div>
 </Page>
}

export function RecoveryMilestones(){
 const {api}=useSession();const [rows,setRows]=useState<Checkin[]>([]);const [error,setError]=useState('');
 useEffect(()=>{checkinsApi(api).list().then(setRows).catch(e=>setError(errorMsg(e)))},[api]);
 const ordered=[...rows].sort((a,b)=>(a.day||'').localeCompare(b.day||''));
 const latest=ordered.at(-1);
 return <Page title="Recovery journey" detail="Milestones come from recorded activity and check-ins, not automatic clinical clearance.">
  <Notice/>{error&&<Banner text={error} error/>}
  <div className="eng-timeline"><article><span className="eng-milestone-dot"/> <strong>Recovery tracking started</strong><p>{ordered[0]?.day||'Add your first check-in to begin'}</p></article>
   {ordered.map((r,i)=><article key={r.id}><span className="eng-milestone-dot"/><strong>Day {i+1} · {r.day}</strong><p>Pain {r.pain_level??'—'}/10 · Wellbeing {r.wellbeing??'—'}/5 · {r.activity_minutes??'—'} activity minutes</p><p>{r.note||'No note entered'}</p></article>)}
   {latest&&<article><span className="eng-milestone-dot"/><strong>Next step</strong><p>Continue logging your recovery and follow your actual medical instructions. No exercise or activity has been medically cleared by this app.</p></article>}
  </div>
  <Link to="/check-in" className="btn primary">Add a check-in</Link>
 </Page>
}

export function DoctorVisitPrep(){
 const {value:prep,error}=useFetch<Prep>('/engagement/visit-prep');
 const [extra,setExtra]=useState('');
 return <Page title="Doctor visit preparation" detail="Turn your last seven days of records into a patient-reviewed discussion guide.">
  <Notice/>{error&&<Banner text={error} error/>}
  {prep&&<div className="eng-print"><Panel title={prep.patient_name+' · '+prep.from+' to '+prep.through}>
   <h3>Recorded medications</h3><ul>{prep.medications.map(m=><li key={m.name}>{m.name} — {m.dosage}; {m.schedule}</li>)}</ul>
   <h3>Dose record counts</h3><p>Recorded taken: {prep.dose_log_counts.taken} · skipped: {prep.dose_log_counts.skipped} · missed: {prep.dose_log_counts.missed}</p>
   <h3>Daily symptoms and activity</h3><ul>{prep.checkins.map(c=><li key={c.day}>{c.day}: pain {c.pain??'—'}/10, energy {c.wellbeing??'—'}/5, {c.activity_minutes??'—'} activity minutes; {c.symptoms.join(', ')||'none recorded'}; {c.note||''}</li>)}</ul>
   <h3>Questions to ask</h3><ul>{prep.suggested_questions.map(q=><li key={q}>{q}</li>)}</ul>
   <label>Additional questions you want to discuss<textarea value={extra} onChange={e=>setExtra(e.target.value)} maxLength={2000} rows={3} placeholder="Write your questions here…"/></label>
   <p>{prep.notice}</p>
  </Panel></div>}
  <button className="btn primary" type="button" onClick={()=>window.print()}><Printer size={18}/> Print or save PDF</button>
 </Page>
}

export function AppointmentPlanner(){
 const {api}=useSession();const {value:rows,refresh,error}=useFetch<Appointment[]>('/engagement/appointments');
 const [title,setTitle]=useState('');const [when,setWhen]=useState('');const [place,setPlace]=useState('');const [feedback,setFeedback]=useState('');
 const submit=async(e:React.FormEvent)=>{e.preventDefault();try{await api('/engagement/appointments','POST',{title,date_time:new Date(when).toISOString(),place:place||null,notes:null});setTitle('');setWhen('');setPlace('');setFeedback('Appointment saved to this prototype account. No clinician was contacted or booked.');refresh()}catch(err){setFeedback(errorMsg(err))}};
 return <Page title="Appointments" detail="Save a personal reminder for your upcoming visits. This does not book appointments with clinics.">
  <Panel title="Add an appointment"><form className="eng-form" onSubmit={submit}><label>Appointment name<input required maxLength={150} value={title} onChange={e=>setTitle(e.target.value)} placeholder="Follow-up with care team"/></label><label>Date and time<input type="datetime-local" required value={when} onChange={e=>setWhen(e.target.value)}/></label><label>Location (optional)<input maxLength={180} value={place} onChange={e=>setPlace(e.target.value)} placeholder="Clinic or telehealth"/></label><button className="btn primary" type="submit">Save appointment</button></form></Panel>
  {feedback&&<Banner text={feedback}/>}
  {error&&<Banner text={error} error/>}
  <Panel title="Saved appointments">{rows?.length?rows.map(a=><p key={a.id}><CalendarDays size={17}/> <strong>{a.title}</strong> — <DateText value={a.date_time}/> {a.place&&' · '+a.place}</p>):<p>No appointments saved yet.</p>}</Panel>
 </Page>
}

export function CaregiverSupportMessages(){
 const {api,role}=useSession();const {value:relationships}=useFetch<Relationship[]>(role==='caregiver'?'/caregiver/relationships':'/caregivers');
 const {value:notes,refresh}=useFetch<Note[]>(role==='caregiver'?'/engagement/caregiver/notes':'/engagement/notes');
 const [body,setBody]=useState('');const [feedback,setFeedback]=useState('');
 const send=async(e:React.FormEvent)=>{e.preventDefault();const rel=relationships?.find(r=>r.status==='active');
  if(!rel){setFeedback('An accepted relationship is needed.');return}
  try{await api('/engagement/caregiver/notes','POST',{relationship_id:rel.id,body});setBody('');setFeedback('Your support note has been saved.');refresh()}catch(err){setFeedback(errorMsg(err))}};
 return <Page title="Caregiver support" detail="Optional supportive notes between consenting caregivers and patients. Not a clinician messaging service.">
  <Notice/>
  {role==='caregiver'&&<Panel title="Leave a supportive note"><form className="eng-form" onSubmit={send}><label>Your message<textarea required maxLength={700} rows={3} value={body} onChange={e=>setBody(e.target.value)} placeholder="I'm here if you need help today."/></label><button className="btn primary" type="submit"><MessageCircle size={17}/> Send supportive note</button></form></Panel>}
  {feedback&&<Banner text={feedback}/>}
  <Panel title="Recent caregiver notes">{notes?.length?notes.map(n=><article className="eng-event" key={n.id}><strong>{n.author}</strong><p>{n.body}</p><small><DateText value={n.created_at}/></small></article>):<p>No notes yet. Caregivers must accept an invitation before they can leave a note.</p>}</Panel>
  <Link className="btn secondary" to="/caregivers">Manage caregiver access</Link>
 </Page>
}
