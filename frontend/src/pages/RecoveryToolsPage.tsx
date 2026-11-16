import {useEffect,useMemo,useState} from 'react';
import {Link} from 'react-router-dom';
import {Activity,ArrowRight,BellRing,CalendarDays,Check,ClipboardList,Download,HeartHandshake,MapPin,Phone,PhoneCall,Pill,ShieldAlert,Stethoscope,Sun,Users,X} from 'lucide-react';
import {useSession} from '../hooks/session';
import {medicationsApi} from '../services/medications';
import {caregiversApi} from '../services/caregivers';
import {checkinsApi} from '../services/checkins';
import type {Checkin,MedicationSummary,Relationship} from '../types/api';
import './RecoveryTools.css';

type EmergencyState='idle'|'preview'|'acknowledged';
type Appointment={date:string;title:string};
const day=(d:Date)=>d.toLocaleDateString('en-CA');
const safeText=(s:string)=>s.replace(/[<>]/g,'').trim().slice(0,180);
function prettyDay(s:string){const d=new Date(s+'T12:00:00');return Number.isNaN(d.getTime())?s:d.toLocaleDateString(undefined,{month:'short',day:'numeric'})}

export function RecoveryToolsPage(){
 const {api,patient,role}=useSession();
 const [meds,setMeds]=useState<MedicationSummary|null>(null);
 const [checkins,setCheckins]=useState<Checkin[]>([]);
 const [relations,setRelations]=useState<Relationship[]>([]);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [emergency,setEmergency]=useState<EmergencyState>('idle');
 const [locationAllowed,setLocationAllowed]=useState(false);
 const [demoLocation,setDemoLocation]=useState('Location not shared');
 const [backupEnabled,setBackupEnabled]=useState(false);
 const [reminderOptIn,setReminderOptIn]=useState(false);
 const [appointments,setAppointments]=useState<Appointment[]>([]);
 const [appointmentTitle,setAppointmentTitle]=useState('');
 const [appointmentDate,setAppointmentDate]=useState('');
 const [doctorNotes,setDoctorNotes]=useState('');
 const [reportReady,setReportReady]=useState(false);
 const [doseBusy,setDoseBusy]=useState('');
 const [status,setStatus]=useState('');
 const today=useMemo(()=>day(new Date()),[]);
 const start=useMemo(()=>{const d=new Date();d.setDate(d.getDate()-13);return day(d)},[]);
 const isCaregiver=role==='caregiver';
 async function refresh(){
  setLoading(true);setError('');
  const all=await Promise.allSettled([
   medicationsApi(api).summary(start,today),
   checkinsApi(api).list(start,today),
   caregiversApi(api).list()
  ]);
  if(all[0].status==='fulfilled')setMeds(all[0].value);
  if(all[1].status==='fulfilled')setCheckins(all[1].value);
  if(all[2].status==='fulfilled')setRelations(all[2].value);
  if(all.every(item=>item.status==='rejected'))setError('Recovery data could not be loaded. Make sure the backend is running.');
  setLoading(false);
 }
 useEffect(()=>{void refresh()},[api,start,today]);
 const recordedDays=new Set(checkins.map(c=>c.day)).size;
 const recent=checkins.slice().sort((a,b)=>b.day.localeCompare(a.day));
 const due=meds?.today_doses.filter(d=>d.due && d.status==='unrecorded')||[];
 const activeCaregivers=relations.filter(r=>r.status==='accepted'||r.status==='active');
 const milestones=[
  {name:'First recovery check-in',done:recordedDays>0,detail:recordedDays>0?'Your first recorded observation is available.':'Add your first daily check-in.'},
  {name:'Three recorded days',done:recordedDays>=3,detail:recordedDays+' of 3 recorded days'},
  {name:'Seven recorded days',done:recordedDays>=7,detail:recordedDays+' of 7 recorded days'},
  {name:'Caregiver connection',done:activeCaregivers.length>0,detail:activeCaregivers.length+' active demo connections'}
 ];
 const summaryLines=[
  'UR CHART — PATIENT-REVIEWED APPOINTMENT PREP (DEMO ONLY)',
  'Patient: '+patient.display_name,
  'Generated: '+new Date().toLocaleString(),
  'Recorded check-ins (past 14 days): '+recordedDays,
  'Latest observations: '+(recent.slice(0,5).map(c=>c.day+': pain '+(c.pain_level??'not reported')+'/10, symptoms '+((c.symptoms||[]).join(', ')||'none recorded')).join('; ')||'No entries'),
  'Medication list: '+(meds?.medications.map(m=>m.name+' ('+m.dosage+')').join(', ')||'No medications recorded'),
  'Due doses requiring confirmation: '+due.length,
  'Patient questions / notes: '+(doctorNotes.trim()||'None entered'),
  'IMPORTANT: Self-reported or synthetic data. Review and correct with clinician. Not a diagnosis or clearance.'
 ];
 function exportPrep(){
  const blob=new Blob([summaryLines.join('\n\n')],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='UR-Chart-visit-prep.txt';a.click();URL.revokeObjectURL(url);setReportReady(true);
 }
 function addAppointment(e:React.FormEvent){
  e.preventDefault();
  if(!appointmentDate||!appointmentTitle.trim())return;
  setAppointments(v=>[...v,{date:appointmentDate,title:safeText(appointmentTitle)}].sort((a,b)=>a.date.localeCompare(b.date)));
  setAppointmentDate('');setAppointmentTitle('');
 }
 async function logDose(d:(typeof due)[number]){
  setDoseBusy(d.schedule_id);setStatus('');
  try{await medicationsApi(api).log(d,'taken');setStatus('Dose confirmation saved to the demo backend.');await refresh()}
  catch(e){setStatus(e instanceof Error?e.message:'Could not save dose')}
  finally{setDoseBusy('')}
 }
 function updateLocation(checked:boolean){
  setLocationAllowed(checked);
  if(!checked){setDemoLocation('Location not shared');return}
  if(!navigator.geolocation){setDemoLocation('Location unavailable');return}
  navigator.geolocation.getCurrentPosition(
   p=>setDemoLocation(p.coords.latitude.toFixed(3)+', '+p.coords.longitude.toFixed(3)+' (approximate; preview only)'),
   ()=>setDemoLocation('Permission denied or position unavailable'),
   {enableHighAccuracy:false,timeout:6000,maximumAge:60000}
  );
 }
 return <div className="rt-page">
  <div className="rt-header"><div><span className="rt-eyebrow">UR CHART / RECOVERY SUITE</span><h1>Everything supporting your recovery</h1><p>Clara-linked tools for medication routines, recovery progress, trusted caregivers and visit preparation.</p></div><span className="rt-demo">FICTIONAL DATA · DEMO</span></div>
  {error&&<p role="alert" className="rt-warning">{error}</p>}
  {isCaregiver&&<div className="rt-warning">This page is designed for the patient role. Caregiver access and shared data permissions are managed in the existing <Link to="/caregivers">caregiver portal</Link>.</div>}
  <section className="rt-hero" aria-label="Clara daily briefing">
   <div className="rt-sun"><Sun size={30}/></div><div><span className="rt-eyebrow">CLARA DAILY BRIEFING</span><h2>Good {new Date().getHours()<12?'morning':new Date().getHours()<17?'afternoon':'evening'}, {patient.display_name.split(' ')[0]}.</h2><p>Today you have <b>{due.length}</b> due dose{due.length===1?'':'s'} awaiting confirmation, <b>{recordedDays}</b> check-in day{recordedDays===1?'':'s'} in your recent history, and <b>{appointments.length}</b> locally planned appointment{appointments.length===1?'':'s'}.</p><small>The briefing summarizes your recorded data; it does not assess medical safety. Local appointments are not stored by the backend.</small></div><Link className="rt-btn" to="/assistant">Ask Clara <ArrowRight size={16}/></Link>
  </section>
  <div className="rt-grid">
   <section className="rt-panel rt-emergency" id="emergency">
    <div className="rt-panel-head"><span className="rt-icon red"><ShieldAlert size={22}/></span><div><h2>Clara Emergency Connect</h2><p>Show immediate guidance and preview contacting trusted caregivers.</p></div></div>
    <div className="rt-warning"><b>Real emergency?</b> Call 911 in the United States, or your local emergency number. This prototype does not place calls, text anyone, dispatch help or monitor your condition.</div>
    <div className="rt-actions"><a className="rt-btn red" href="tel:911"><PhoneCall size={17}/> Call 911</a><button className="rt-btn secondary" type="button" onClick={()=>setEmergency('preview')}>Activate demo emergency mode</button></div>
    {emergency!=='idle'&&<div className="rt-emergency-card" role="status"><div className="rt-line"><b>Demo emergency card</b><button className="rt-text-button" onClick={()=>setEmergency('idle')} aria-label="Close emergency preview"><X size={16}/></button></div><p>{patient.display_name} · Emergency help card · No calls or texts sent.</p><label className="rt-check"><input type="checkbox" checked={locationAllowed} onChange={e=>updateLocation(e.target.checked)}/> Permit one-time approximate location preview</label><p><MapPin size={15}/> {demoLocation}</p><p><Users size={15}/> {activeCaregivers.length} active caregiver connection(s) · delivery not configured</p><label className="rt-check"><input type="checkbox" checked={backupEnabled} onChange={e=>setBackupEnabled(e.target.checked)}/> Include backup caregiver in demo escalation plan</label><button className="rt-btn secondary" onClick={()=>setEmergency('acknowledged')}>Simulate caregiver acknowledging alert</button>{emergency==='acknowledged'&&<strong>Demo only: simulated acknowledgement. No real caregiver has been contacted.</strong>}</div>}
   </section>
   <section className="rt-panel">
    <div className="rt-panel-head"><span className="rt-icon"><Pill size={22}/></span><div><h2>Smart medication adherence</h2><p>Review due doses, mark confirmed doses and spot unrecorded medication activity.</p></div></div>
    <div className="rt-stat">{loading?'Loading…':due.length} <small>due dose{due.length===1?'':'s'} to review</small></div>
    <label className="rt-check"><input type="checkbox" checked={reminderOptIn} onChange={e=>setReminderOptIn(e.target.checked)}/> Enable reminder preview on this page</label>
    {reminderOptIn&&<p className="rt-note"><BellRing size={15}/> Reminder preference is preview-only; no background push alerts or caregiver SMS.</p>}
    <ul className="rt-list">{due.slice(0,5).map(d=><li key={d.schedule_id+d.scheduled_for}><span>{meds?.medications.find(m=>m.id===d.medication_id)?.name||'Scheduled medication'}<small>{d.local_time} · {d.overdue?'Overdue':'Due'}</small></span><button disabled={!!doseBusy} className="rt-mini" onClick={()=>void logDose(d)}>{doseBusy===d.schedule_id?'Saving…':'Confirm taken'}</button></li>)}</ul>
    {due.length===0&&<p className="rt-note">No due unrecorded doses returned for today. This does not mean medication is unnecessary.</p>}
    {status&&<p role="status" className="rt-note">{status}</p>}
    <Link to="/medications" className="rt-link">Open full medication manager <ArrowRight size={16}/></Link>
   </section>
   <section className="rt-panel">
    <div className="rt-panel-head"><span className="rt-icon green"><Activity size={22}/></span><div><h2>Recovery timeline</h2><p>Patient-reported milestones from your recorded recovery activity.</p></div></div>
    <div className="rt-timeline">{milestones.map((item,i)=><div className="rt-milestone" key={item.name}><span className={item.done?'rt-complete':'rt-pending'}>{item.done?<Check size={15}/>:i+1}</span><div><strong>{item.name}</strong><small>{item.detail}</small></div></div>)}</div>
    <p className="rt-note">These are engagement milestones, not clinical healing goals or medical clearance.</p><Link className="rt-link" to="/progress">Review progress chart <ArrowRight size={16}/></Link>
   </section>
   <section className="rt-panel">
    <div className="rt-panel-head"><span className="rt-icon"><HeartHandshake size={22}/></span><div><h2>Caregiver companion portal</h2><p>Permission-based sharing, invitations and acknowledgements.</p></div></div>
    <div className="rt-stat">{activeCaregivers.length} <small>active shared connection{activeCaregivers.length===1?'':'s'}</small></div>
    <p>Use the existing caregiver portal to invite or revoke a fictional caregiver and control which patient data they can access.</p>
    <p className="rt-note">Emergency SMS, phone dialing, caregiver messaging and delivery receipts are planned integrations—not live here.</p>
    <Link className="rt-link" to="/caregivers">Manage caregiver access <ArrowRight size={16}/></Link>
   </section>
   <section className="rt-panel">
    <div className="rt-panel-head"><span className="rt-icon orange"><CalendarDays size={22}/></span><div><h2>Upcoming appointments</h2><p>Plan visits in this page preview.</p></div></div>
    <form className="rt-form" onSubmit={addAppointment}><label>Visit date<input required min={today} type="date" value={appointmentDate} onChange={e=>setAppointmentDate(e.target.value)}/></label><label>Visit purpose<input required maxLength={180} placeholder="e.g. Cardiology follow-up" value={appointmentTitle} onChange={e=>setAppointmentTitle(e.target.value)}/></label><button className="rt-btn secondary" type="submit">Add demo appointment</button></form>
    <ul className="rt-list">{appointments.map((a,i)=><li key={i}><span><b>{a.title}</b><small>{prettyDay(a.date)}</small></span><button className="rt-text-button" onClick={()=>setAppointments(v=>v.filter((_,j)=>i!==j))}>Remove</button></li>)}</ul>
    <p className="rt-note">Appointments are page-local only and disappear on refresh. No clinical booking is made.</p>
   </section>
   <section className="rt-panel">
    <div className="rt-panel-head"><span className="rt-icon green"><Stethoscope size={22}/></span><div><h2>Doctor visit preparation</h2><p>Turn recent patient entries into a reviewable visit summary.</p></div></div>
    <p>Includes up to five recent check-ins, the medication list, due confirmations and your own questions. Nothing is automatically sent to a clinician.</p>
    <label className="rt-notes">Questions for the clinician<textarea maxLength={1800} rows={4} placeholder="Write questions or topics to review…" value={doctorNotes} onChange={e=>{setDoctorNotes(e.target.value);setReportReady(false)}}/></label>
    <div className="rt-actions"><button className="rt-btn" onClick={exportPrep}><Download size={16}/> Download visit summary</button><button className="rt-btn secondary" onClick={()=>window.print()}><ClipboardList size={16}/> Print</button></div>{reportReady&&<p role="status" className="rt-note">Downloaded. Review the report carefully before sharing.</p>}
   </section>
  </div>
  <p className="rt-disclaimer">UR Chart is an educational hackathon prototype with synthetic records. It does not deliver emergency response, medical diagnosis, real notification services, or secure production patient messaging.</p>
 </div>
}
