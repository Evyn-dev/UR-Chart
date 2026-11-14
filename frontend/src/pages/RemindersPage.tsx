import {useState} from 'react';
import type {FormEvent} from 'react';
import {useSession} from '../hooks/session';
import {useResource} from '../hooks/useResource';
import {useReminderNotifications} from '../hooks/reminderNotifications';
import {remindersApi,localReminderTime,reminderInstant} from '../services/reminders';
import type {Reminder,ReminderAction,Repeat} from '../services/reminders';
import {messageOf} from '../services/presentation';
import {Empty,ErrorState,Loader,PageIntro,Panel,Success} from '../components/UI';
import {Notice} from '../components/RecoveryUI';

export function RemindersPage(){
 const {api,patient}=useSession();const notifications=useReminderNotifications();
 const [offset,setOffset]=useState(0);const resource=useResource(()=>remindersApi(api).list(offset),[api,offset]);
 const [editing,setEditing]=useState<Reminder|null>(null);const [title,setTitle]=useState('');const [notes,setNotes]=useState('');
 const [time,setTime]=useState('');const [zone,setZone]=useState(patient.timezone);const [repeat,setRepeat]=useState<Repeat>('once');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [success,setSuccess]=useState('');
 function reset(){setEditing(null);setTitle('');setNotes('');setTime('');setZone(patient.timezone);setRepeat('once')}
 function edit(reminder:Reminder){setEditing(reminder);setTitle(reminder.title);setNotes(reminder.notes);setTime(localReminderTime(reminder.due_at,reminder.timezone));setZone(reminder.timezone);setRepeat(reminder.repeat);setError('');setSuccess('')}
 async function save(event:FormEvent){
  event.preventDefault();if(busy)return;setBusy(true);setError('');setSuccess('');
  try{
   const body={title,notes,due_at:reminderInstant(time,zone),timezone:zone,repeat};
   if(editing)await remindersApi(api).edit(editing,body);else await remindersApi(api).create(body);
   reset();setOffset(0);resource.reload();setSuccess('Reminder saved.');
  }catch(e){setError(messageOf(e))}finally{setBusy(false)}
 }
 async function action(reminder:Reminder,value:ReminderAction){
  if(value==='delete'&&!window.confirm(`Delete reminder “${reminder.title}”?`))return;
  setBusy(true);setError('');setSuccess('');
  try{await remindersApi(api).action(reminder,value);if(editing?.id===reminder.id)reset();resource.reload();setSuccess('Reminder updated.')}
  catch(e){setError(messageOf(e));resource.reload()}finally{setBusy(false)}
 }
 return <>
  <PageIntro eyebrow="YOUR PERSONAL TASKS" title="Reminders" subtitle="Personal tasks stored with your account, separate from medication dose schedules."/>
  <Notice>Browser notifications require this app to remain open and permission to be granted. Sleeping devices and background tabs can delay notifications. This is not a medication alarm or emergency service.</Notice>
  <Panel title="Optional browser notifications"><button className="btn ghost" onClick={()=>void notifications.toggle()}>{notifications.enabled?'Disable notifications':'Enable notifications'}</button><p role="status" className="muted small">{notifications.status}</p></Panel>
  <Panel title={editing?'Edit reminder':'Create a reminder'} subtitle="Recurrence uses the selected time zone. A repeated fall-back hour uses its first occurrence; a spring gap shifts that occurrence forward.">
   <form className="form-grid" onSubmit={save}>
    <label>Reminder title<input required maxLength={120} value={title} onChange={e=>setTitle(e.target.value)}/></label>
    <label>Date and time<input required type="datetime-local" value={time} onChange={e=>setTime(e.target.value)}/></label>
    <label>Time zone<input required value={zone} onChange={e=>setZone(e.target.value)} placeholder="America/New_York"/></label>
    <label>Repeat<select value={repeat} onChange={e=>setRepeat(e.target.value as Repeat)}><option value="once">Once</option><option value="daily">Daily</option><option value="weekdays">Weekdays</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
    <label>Notes<textarea maxLength={500} value={notes} onChange={e=>setNotes(e.target.value)}/></label>
    <div className="form-actions"><button className="btn primary" disabled={busy}>{editing?'Save changes':'Create reminder'}</button>{editing&&<button type="button" className="btn ghost" onClick={reset}>Cancel edit</button>}</div>
   </form>
   {error&&<ErrorState message={error}/>} {success&&<Success message={success}/>}
  </Panel>
  <Panel title="Your reminders" subtitle="Completing or dismissing a recurring task schedules its next occurrence; overdue occurrences are skipped.">
   {resource.loading?<Loader/>:resource.error?<ErrorState message={resource.error} onRetry={resource.reload}/>:resource.data?.length?resource.data.map(reminder=><article className="reminder-card" key={reminder.id} aria-label={reminder.title}>
    <h3>{reminder.title}</h3><p>{reminder.notes}</p>
    <p>{localReminderTime(reminder.due_at,reminder.timezone).replace('T',' ')} · {reminder.timezone} · {reminder.repeat}</p>
    <p className="muted small">{reminder.active?'Active':'Inactive'}{reminder.last_action?` · Last action: ${reminder.last_action}`:''}</p>
    <div className="row-actions">
     <button className="btn small ghost" disabled={busy} onClick={()=>edit(reminder)}>Edit</button>
     {reminder.active&&<><button className="btn small primary" disabled={busy} onClick={()=>void action(reminder,'complete')}>Complete</button><button className="btn small ghost" disabled={busy} onClick={()=>void action(reminder,'dismiss')}>Dismiss</button>{Date.parse(reminder.due_at)<=Date.now()&&<button className="btn small ghost" disabled={busy} onClick={()=>void action(reminder,'snooze')}>Snooze 10 minutes</button>}</>}
     <button className="btn small ghost" disabled={busy} onClick={()=>void action(reminder,'toggle')}>{reminder.active?'Deactivate':'Reactivate'}</button>
     <button className="btn small ghost" disabled={busy} onClick={()=>void action(reminder,'delete')}>Delete</button>
    </div>
   </article>):<Empty message="No reminders on this page"/>}
   <div className="row-actions"><button className="btn ghost" disabled={offset===0||resource.loading} onClick={()=>setOffset(value=>Math.max(0,value-50))}>Previous</button><button className="btn ghost" disabled={resource.data?.length!==50||resource.loading} onClick={()=>setOffset(value=>value+50)}>Next</button></div>
  </Panel>
 </>;
}
