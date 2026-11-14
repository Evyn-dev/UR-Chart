import {useState} from 'react';
import {Check,Clock3} from 'lucide-react';
import {useSession} from '../hooks/session';
import {medicationsApi} from '../services/medications';
import {Empty,ErrorState,Success} from '../components/UI';
import type {MedicationSummary,Dose} from '../types/api';
import {messageOf} from '../services/presentation';
import {friendlyTime} from '../services/presentation';

export function DaySummary({summary,onChanged}:{summary:MedicationSummary;onChanged:()=>void}){
 const {api}=useSession();const [busy,setBusy]=useState('');const [error,setError]=useState('');const [success,setSuccess]=useState('');const names=new Map(summary.medications.map(m=>[m.id,m.name]));
 const doses=[...summary.today_doses].sort((a,b)=>a.scheduled_for.localeCompare(b.scheduled_for));
 async function record(dose:Dose,status:'taken'|'skipped'|'missed'){
  let units:number|undefined;
  if(status==='taken'){
    const value=window.prompt('Optional: How many supply units were used? Leave blank if unknown.');
    if(value===null)return;
    if(value.trim()!==''){
      const parsed=Number(value);
      if(!Number.isInteger(parsed)||parsed<1||parsed>100000){setError('Supply units must be a positive whole number or left blank.');return}
      units=parsed;
    }
  }
  setBusy(dose.schedule_id+dose.scheduled_for);setError('');setSuccess('');
  try{await medicationsApi(api).log(dose,status,units);setSuccess(`Recorded ${status}.`);onChanged()}catch(e){setError(messageOf(e))}finally{setBusy('')}
 }
 return <><div className="dose-list">{doses.length?doses.map((dose,i)=><div className="dose-row" key={`${dose.schedule_id}-${dose.scheduled_for}-${i}`}>
  <div className="time-chip"><Clock3 size={16}/>{dose.local_time||friendlyTime(dose.scheduled_for)}</div><div className="dose-name"><strong>{names.get(dose.medication_id)||'Medication'}</strong><span>{dose.status==='unrecorded'?(dose.overdue?'Overdue, not recorded':'Awaiting record'):`Recorded: ${dose.status}`}</span></div>
  {dose.status==='unrecorded'&&dose.due?<div className="dose-actions"><button className="btn tiny primary" disabled={Boolean(busy)} onClick={()=>record(dose,'taken')}><Check size={15}/> Taken</button><button className="btn tiny ghost" disabled={Boolean(busy)} onClick={()=>record(dose,'skipped')}>Skipped</button><button className="btn tiny ghost" disabled={Boolean(busy)} onClick={()=>record(dose,'missed')}>Missed</button></div>:<span className="muted small">{dose.status==='unrecorded'?'Scheduled':dose.status}</span>}
 </div>):<Empty message="No scheduled doses today" detail="Your medication schedule will appear here when reminder times are configured."/>}</div>
 {error&&<ErrorState message={error}/>} {success&&<Success message={success}/>}</>
}
