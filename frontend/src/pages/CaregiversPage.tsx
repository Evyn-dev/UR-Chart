import {useEffect,useRef,useState} from 'react';
import type {FormEvent,ReactNode} from 'react';
import {UserPlus,Users,ExternalLink} from 'lucide-react';
import {useSession} from '../hooks/session';
import {useResource} from '../hooks/useResource';
import {caregiversApi} from '../services/caregivers';
import {Empty,ErrorState,Loader,PageIntro,Panel,Success} from '../components/UI';
import type {Permission,Severity,Relationship,SharedDashboard} from '../types/api';
import {messageOf} from '../services/presentation';
import {Notice} from '../components/RecoveryUI';

const permissions: {key:Permission;label:string}[]=[{key:'recovery_summary',label:'Recovery summary'},{key:'medication_adherence',label:'Medication adherence'},{key:'checkin_summary',label:'Check-in statistics'},{key:'alerts',label:'Selected safety alert levels'}];
const asRecord=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
const asRows=(value:unknown):Record<string,unknown>[]=>Array.isArray(value)?value.map(asRecord):[];
const display=(value:unknown)=>value==null||value===''?'—':typeof value==='object'?JSON.stringify(value):String(value);

export function CaregiversPage(){
 const {api}=useSession();
 const outgoing=useResource(()=>caregiversApi(api).list(),[api]);
 const incoming=useResource(()=>caregiversApi(api).inbox(),[api]);
 const shared=useResource(()=>caregiversApi(api).active(),[api]);
 const [user,setUser]=useState('synthetic-demo-caregiver');
 const [selected,setSelected]=useState<Permission[]>(['recovery_summary']);
 const [severities,setSeverities]=useState<Severity[]>(['urgent','emergency']);
 const [busy,setBusy]=useState('');
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 const [sharedPreview,setSharedPreview]=useState<SharedDashboard|null>(null);
 const [openedRelationship,setOpenedRelationship]=useState('');
 const previewRequest=useRef(0);
 useEffect(()=>()=>{previewRequest.current++},[api]);

 async function viewShared(id:string){
  if(openedRelationship===id){previewRequest.current++;setOpenedRelationship('');setSharedPreview(null);return}
  const requestId=++previewRequest.current;setOpenedRelationship(id);setSharedPreview(null);setError('');
  try{const dashboard=await caregiversApi(api).dashboard(id);if(requestId===previewRequest.current)setSharedPreview(dashboard)}
  catch(e){if(requestId===previewRequest.current){setOpenedRelationship('');setError(messageOf(e))}}
 }
 async function perform(label:string,run:()=>Promise<unknown>){
  previewRequest.current++;setOpenedRelationship('');setSharedPreview(null);setBusy(label);setError('');setSuccess('');
  try{await run();setSuccess('Changes saved.');outgoing.reload();incoming.reload();shared.reload();return true}
  catch(e){setError(messageOf(e));return false}finally{setBusy('')}
 }
 async function invite(e:FormEvent){
  e.preventDefault();if(!selected.length){setError('Select at least one permission.');return}
  if(await perform('invite',()=>caregiversApi(api).invite(user.trim(),selected,selected.includes('alerts')?severities:[])))setUser('')
 }
 function updatePermission(key:Permission){setSelected(previous=>previous.includes(key)?previous.filter(s=>s!==key):[...previous,key])}

 return <>
  <PageIntro eyebrow="RECOVERY IS A TEAM EFFORT" title="Caregiver access" subtitle="Share selected recovery summaries with someone you trust. You can revoke their access at any time."/>
  <Notice>Caregivers receive read-only access to the full contents of each section the patient checks. Unchecked sections remain private. They cannot edit medications, doses, check-ins, or patient records.</Notice>
  <div className="content-columns">
   <div className="content-main">
    <Panel title="Invite a caregiver" subtitle="For this demo, use the caregiver role with the same access code in another browser session">
     <form className="caregiver-form" onSubmit={invite}>
      <label>Caregiver demo user ID<input value={user} onChange={e=>setUser(e.target.value)} required placeholder="synthetic-demo-caregiver"/></label>
      <fieldset><legend>What can they see?</legend>{permissions.map(p=><label className="check-row" key={p.key}><input type="checkbox" checked={selected.includes(p.key)} onChange={()=>updatePermission(p.key)}/>{p.label}</label>)}</fieldset>
      {selected.includes('alerts')&&<fieldset><legend>Alert severities to share</legend>{(['routine','needs_clinical_review','urgent','emergency'] as Severity[]).map(s=><label className="check-row" key={s}><input type="checkbox" checked={severities.includes(s)} onChange={()=>setSeverities(prev=>prev.includes(s)?prev.filter(x=>x!==s):[...prev,s])}/>{s.replace(/_/g,' ')}</label>)}</fieldset>}
      <button className="btn primary" disabled={Boolean(busy)||!user.trim()||(selected.includes('alerts')&&severities.length===0)}><UserPlus size={17}/>Send invitation</button>
     </form>
    </Panel>
    <Panel title="Your invited caregivers" subtitle="Pending and active relationships">
     {outgoing.loading?<Loader/>:outgoing.error?<ErrorState message={outgoing.error} onRetry={outgoing.reload}/>:outgoing.data?.length?outgoing.data.map(r=><RelationshipRow key={r.id} relationship={r} action={r.status==='active'||r.status==='pending'?<button disabled={Boolean(busy)} className="btn small ghost" onClick={()=>window.confirm('Revoke access for this caregiver?')&&perform(r.id,()=>caregiversApi(api).revoke(r))}>Revoke access</button>:null}/>):<Empty message="No caregiver invitations yet"/>}
    </Panel>
   </div>
   <div className="content-side">
    <Panel title="Invitations for you" subtitle="Accept invitations, then open the patient's chart here">
     {incoming.loading||shared.loading?<Loader/>:incoming.error?<ErrorState message={incoming.error} onRetry={incoming.reload}/>:shared.error?<ErrorState message={shared.error} onRetry={shared.reload}/>:<>
      {incoming.data?.map(r=><RelationshipRow key={r.id} relationship={r} action={<div className="row-actions"><button className="btn small primary" disabled={Boolean(busy)} onClick={()=>perform(r.id,()=>caregiversApi(api).respond(r,'accept'))}>Accept</button><button className="btn small ghost" disabled={Boolean(busy)} onClick={()=>perform(r.id,()=>caregiversApi(api).respond(r,'decline'))}>Decline</button></div>}/>)}
      {shared.data?.map(r=><div key={r.id} className="shared-row">
       <b>Accepted invitation · Patient chart</b>
       <span>{r.permissions.map(p=>permissions.find(option=>option.key===p)?.label||p).join(', ')||'No sharing scopes'}</span>
       <button type="button" className="btn small primary" disabled={Boolean(busy)} aria-expanded={openedRelationship===r.id} onClick={()=>viewShared(r.id)}><ExternalLink size={15}/>{openedRelationship===r.id?'Close patient chart':"Open patient's chart"}</button>
       {openedRelationship===r.id&&<div className="shared-chart" aria-live="polite">{!sharedPreview?<Loader/>:<SharedChart dashboard={sharedPreview}/>}</div>}
      </div>)}
      {!incoming.data?.length&&!shared.data?.length&&<Empty message="No invitations yet"/>}
     </>}
    </Panel>
   </div>
  </div>
  {error&&<ErrorState message={error}/>} {success&&<Success message={success}/>}
 </>
}

function SharedChart({dashboard}:{dashboard:SharedDashboard}){
 const permissions=new Set(dashboard.permissions);
 const medication=asRecord(dashboard.medication_adherence);
 const checkin=asRecord(dashboard.checkin_summary);
 const recovery=asRecord(dashboard.recovery_summary);
 const medicationRows=asRows(medication.medications);
 const doseRows=asRows(medication.today_doses);
 const logRows=asRows(medication.completed_records);
 const checkinRows=asRows(checkin.recent);
 return <div className="shared-chart-content">
  <h3>{dashboard.patient_display_name}'s shared patient chart</h3>
  <p className="muted">Read-only access · Only patient-authorized sections are displayed.</p>
  {permissions.has('recovery_summary')&&dashboard.recovery_summary&&<section><h4>Recovery summary</h4><p>Period: {display(recovery.start)} – {display(recovery.end)}</p><p>Check-in days recorded: {display(recovery.checkin_days)} of {display(recovery.expected_days)}</p><p>Check-in recorded today: {recovery.checkin_recorded_today?'Yes':'No'}</p></section>}
  {permissions.has('medication_adherence')&&dashboard.medication_adherence&&<section><h4>Medication chart and adherence</h4><p>Period: {display(medication.start)} – {display(medication.end)}</p><p>Medication records included: {display(medication.medications_included)}</p><h5>Medications</h5>{medicationRows.length?<div className="table-scroll"><table className="data-table"><thead><tr><th>Medication</th><th>Dosage</th><th>Schedule</th><th>Status</th></tr></thead><tbody>{medicationRows.map((m,i)=><tr key={String(m.id??i)}><td>{display(m.name)}</td><td>{display(m.dosage)}</td><td>{display(m.schedule)}</td><td>{m.active?'Active':'Archived'}</td></tr>)}</tbody></table></div>:<p className="muted">No medication records in this page.</p>}<h5>Adherence by medication</h5><pre className="safe-json">{JSON.stringify(medication.adherence_by_medication??{},null,2)}</pre><h5>Today's doses</h5><pre className="safe-json">{JSON.stringify(doseRows,null,2)}</pre><h5>Recorded dose history</h5><pre className="safe-json">{JSON.stringify(logRows,null,2)}</pre><h5>Refill warnings</h5><pre className="safe-json">{JSON.stringify(medication.refill_warnings??[],null,2)}</pre><p className="muted">Showing {medicationRows.length} medication records. {medication.has_more?'More medication records are available through pagination.':''}</p></section>}
  {permissions.has('checkin_summary')&&dashboard.checkin_summary&&<section><h4>Check-in history and statistics</h4><pre className="safe-json">{JSON.stringify(checkin.trends??{},null,2)}</pre>{checkinRows.length?<div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Wellbeing</th><th>Pain</th><th>Activity</th><th>Symptoms</th><th>Notes</th></tr></thead><tbody>{checkinRows.map((c,i)=><tr key={String(c.id??i)}><td>{display(c.day)}</td><td>{display(c.wellbeing)}</td><td>{display(c.pain_level)}</td><td>{display(c.activity_minutes)} min</td><td>{display(c.symptoms)}</td><td>{display(c.note)}</td></tr>)}</tbody></table></div>:<p className="muted">No check-ins in this period.</p>}</section>}
  {permissions.has('alerts')&&dashboard.alerts&&<section><h4>Patient-selected safety alerts</h4>{dashboard.alerts.length?dashboard.alerts.map(alert=><div className="refill-line" key={alert.id}><span><b>{alert.severity}</b> · {alert.status}<br/>{alert.guidance}</span></div>):<p className="muted">No shared alerts in this period.</p>}</section>}
 </div>
}

function RelationshipRow({relationship:r,action}:{relationship:Relationship;action:ReactNode}){
 return <div className="relationship-row"><div className="caregiver-avatar"><Users size={21}/></div><div className="relationship-info"><strong>{r.caregiver_user_id}</strong><span>{r.status} · {r.permissions.join(', ').replace(/_/g,' ')||'No sharing scopes'}</span></div>{action}</div>
}
