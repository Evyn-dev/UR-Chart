import {useEffect,useState} from 'react';
import {Bell,BellOff} from 'lucide-react';
import {useSession} from '../hooks/session';
import type {MedicationSummary} from '../types/api';

function prefKey(id:string){return 'urchart-reminders-'+id}
const updateEvent='urchart-reminders-changed';

/** Optional reminders while this web page remains open. Browser background delivery is not guaranteed. */
export function MedicationReminders(){
 const {api,patient,role}=useSession();
 useEffect(()=>{
  if(role!=='patient'||!('Notification' in window))return;
  let disposed=false;
  async function check(){
   if(localStorage.getItem(prefKey(patient.id))!=='on'||Notification.permission!=='granted')return;
   try{
    const summary=await api<MedicationSummary>('/medications/summary');
    if(disposed)return;
    const now=new Date();
    for(const dose of summary.today_doses){
     if(dose.status!=='unrecorded'||!dose.due)continue;
     const scheduled=new Date(dose.scheduled_for);
     const offset=now.getTime()-scheduled.getTime();
     if(offset<0||offset>3*60*1000)continue;
     const key='urchart-reminded-'+patient.id+'-'+dose.medication_id+'-'+dose.scheduled_for;
     if(localStorage.getItem(key))continue;
     localStorage.setItem(key,'1');
     const medication=summary.medications.find(m=>m.id===dose.medication_id);
     new Notification('UR Chart medication reminder',{
      body:(medication?.name||'A scheduled medication')+' is due. Follow your own care instructions and record what happened.',
      tag:key,
     });
    }
   }catch{/* Background reminders are best-effort while the tab is open. */}
  }
  const interval=window.setInterval(()=>void check(),60000);
  void check();
  return()=>{disposed=true;window.clearInterval(interval)};
 },[api,patient.id,role]);
 return null;
}

export function MedicationReminderToggle(){
 const {patient}=useSession();
 const [enabled,setEnabled]=useState(()=>{try{return localStorage.getItem(prefKey(patient.id))==='on'}catch{return false}});
 const [message,setMessage]=useState('Reminders only work while this browser is open and allowed to show notifications.');
 async function toggle(){
  if(enabled){try{localStorage.removeItem(prefKey(patient.id))}catch{/* optional storage */}setEnabled(false);window.dispatchEvent(new Event(updateEvent));setMessage('Browser medication reminders are off.');return}
  if(!('Notification' in window)){setMessage('This browser does not support notifications.');return}
  const permission=await Notification.requestPermission();
  if(permission!=='granted'){setMessage('Notification permission was not granted.');return}
  try{localStorage.setItem(prefKey(patient.id),'on')}catch{setMessage('Your browser did not allow storing the preference.');return}
  setEnabled(true);window.dispatchEvent(new Event(updateEvent));
  setMessage('Browser reminders enabled while UR Chart stays open. They are not guaranteed in the background.');
 }
 return <div className="eng-reminder-toggle">
  <button type="button" className={'btn '+(enabled?'secondary':'primary')} onClick={()=>void toggle()}>{enabled?<BellOff size={17}/>:<Bell size={17}/>} {enabled?'Disable browser reminders':'Enable browser medication reminders'}</button>
  <p role="status">{message}</p>
 </div>;
}
