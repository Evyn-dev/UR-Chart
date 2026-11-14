import {useCallback,useEffect,useState} from 'react';
import type {FormEvent} from 'react';
import './CurriculumPanel.css';
import {useSession} from '../hooks/session';
import type {CurriculumTask,CurriculumAudit} from '../types/api';

type Edit = {title:string;description:string;due_day:string;position:number;status:'pending'|'completed'|'archived'};
const blank:Edit = {title:'',description:'',due_day:'',position:0,status:'pending'};

export function CurriculumPanel({relationshipId}:{relationshipId?:string}){
 const {api}=useSession();
 const base=relationshipId?`/caregiver/relationships/${relationshipId}/curriculum`:'/curriculum';
 const editable=Boolean(relationshipId);
 const [items,setItems]=useState<CurriculumTask[]>([]);
 const [audit,setAudit]=useState<CurriculumAudit[]>([]);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 const [busy,setBusy]=useState(false);
 const [draft,setDraft]=useState<Edit>(blank);
 const [editing,setEditing]=useState<string|null>(null);
 const [showHistory,setShowHistory]=useState(false);
 const reload=useCallback(async()=>{
   const [tasks,changes]=await Promise.all([
     api<CurriculumTask[]>(base),
     api<CurriculumAudit[]>(base+'/audit')
   ]);
   setItems(tasks);setAudit(changes);
 },[api,base]);
 useEffect(()=>{let live=true;setLoading(true);setError('');Promise.all([
   api<CurriculumTask[]>(base),api<CurriculumAudit[]>(base+'/audit')
 ]).then(([tasks,changes])=>{if(live){setItems(tasks);setAudit(changes)}})
   .catch(e=>{if(live)setError(e instanceof Error?e.message:'Cannot load recovery tasks')})
   .finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[api,base]);
 function start(item:CurriculumTask){setEditing(item.id);setDraft({
   title:item.title,description:item.description,due_day:item.due_day||'',
   position:item.position,status:item.status
 })}
 async function save(e:FormEvent){e.preventDefault();if(!editable||busy)return;setBusy(true);setError('');setSuccess('');
   try{
     const payload={title:draft.title.trim(),description:draft.description.trim(),due_day:draft.due_day||null,position:Number(draft.position)};
     if(!payload.title)throw new Error('Enter a task title.');
     if(editing){
       const old=items.find(x=>x.id===editing);
       if(!old)throw new Error('Task no longer exists. Reload the page.');
       await api(base+'/'+editing,'PATCH',{...payload,status:draft.status,expected_version:old.version});
     }else await api(base,'POST',payload);
     await reload();setDraft(blank);setEditing(null);setSuccess('Educational task saved and recorded in change history.');
   }catch(e){setError(e instanceof Error?e.message:'Unable to save task')}finally{setBusy(false)}
 }
 async function setStatus(item:CurriculumTask,status:Edit['status']){
   if(!editable||busy)return;setBusy(true);setError('');setSuccess('');
   try{
     await api(base+'/'+item.id,'PATCH',{
       title:item.title,description:item.description,due_day:item.due_day,
       position:item.position,status,expected_version:item.version
     });
     await reload();setSuccess('Change saved to history.');
   }catch(e){setError(e instanceof Error?e.message:'Unable to update task')}finally{setBusy(false)}
 }
 return <section className="panel curriculum-panel" aria-label="Educational recovery curriculum">
   <div className="panel-header"><div><h2>Recovery checklist</h2>
   <p className="muted small">{editable?'Caregiver-managed educational tasks. Every edit is logged.':'Tasks shared by your caregiver. These are not medical orders.'}</p></div></div>
   {loading?<p className="muted">Loading checklist…</p>:
    <><div className="curriculum-task-list">
      {items.filter(x=>x.status!=='archived').length===0?<p className="muted">No tasks yet.</p>:
      items.filter(x=>x.status!=='archived').map(item=><div key={item.id} className="curriculum-task">
        <div><strong>{item.title}</strong><span className="muted small"> {item.status==='completed'?'✓ Completed':'Pending'}{item.due_day?' · '+item.due_day:''}</span>
          {item.description&&<p>{item.description}</p>}</div>
        {editable&&<div className="row-actions">
          <button type="button" className="btn small ghost" disabled={busy} onClick={()=>start(item)}>Edit</button>
          <button type="button" className="btn small ghost" disabled={busy} onClick={()=>setStatus(item,item.status==='completed'?'pending':'completed')}>{item.status==='completed'?'Reopen':'Complete'}</button>
          <button type="button" className="btn small ghost" disabled={busy} onClick={()=>window.confirm('Archive this educational task? The action will be logged.')&&setStatus(item,'archived')}>Archive</button>
        </div>}
      </div>)}
    </div>
    {editable&&<form onSubmit={save} className="caregiver-form curriculum-editor">
      <h3>{editing?'Edit educational task':'Add educational task'}</h3>
      <label>Task name<input required maxLength={200} value={draft.title} onChange={e=>setDraft(v=>({...v,title:e.target.value}))} placeholder="e.g. Prepare follow-up questions"/></label>
      <label>Details<textarea rows={2} maxLength={1000} value={draft.description} onChange={e=>setDraft(v=>({...v,description:e.target.value}))} placeholder="Nonclinical notes and reminders only"/></label>
      <div className="form-grid">
        <label>Due date<input type="date" value={draft.due_day} onChange={e=>setDraft(v=>({...v,due_day:e.target.value}))}/></label>
        <label>Order<input type="number" min={0} max={10000} value={draft.position} onChange={e=>setDraft(v=>({...v,position:Number(e.target.value)}))}/></label>
      </div>
      <div className="row-actions"><button className="btn small primary" disabled={busy}>{busy?'Saving…':editing?'Save changes':'Add task'}</button>
      {editing&&<button type="button" className="btn small ghost" onClick={()=>{setEditing(null);setDraft(blank)}}>Cancel</button>}</div>
    </form>}
    <button type="button" className="btn small ghost" onClick={()=>setShowHistory(v=>!v)}>{showHistory?'Hide':'View'} change history ({audit.length})</button>
    {showHistory&&<div className="curriculum-history">
      {audit.length?audit.map(a=><div key={a.id} className="history-line"><span>{new Date(a.created_at).toLocaleString()} · {a.actor_user_id} · {a.action}</span>
       <details><summary>Before / after</summary><pre>{JSON.stringify({before:a.before,after:a.after},null,2)}</pre></details></div>):
       <p className="muted">No changes have been logged yet.</p>}
    </div>}</>}
    {error&&<p role="alert" className="muted">{error}</p>}
    {success&&<p role="status">{success}</p>}
    <p className="small muted">This checklist is educational only. Caregivers cannot change medication orders or clinician restrictions here.</p>
 </section>
}
