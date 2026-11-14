import {useEffect,useRef,useState} from 'react';
import type {ChangeEvent,FormEvent} from 'react';
import {FileText,Upload,Download,Trash2,ShieldCheck,ShieldOff,Users,Lock,RefreshCw} from 'lucide-react';
import {useSession} from '../hooks/session';
import type {Relationship} from '../types/api';

type DocumentRow={
 id:string;name:string;content_type:string;byte_size:number;created_at:string;
 patient_id:string;shared_with_caregivers:boolean;uploader_role:string;can_manage:boolean
};
const MAX_BYTES=3*1024*1024;
const extensionMime:Record<string,string>={pdf:'application/pdf',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',txt:'text/plain',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'};
const mimeTypes=new Set(['application/pdf','image/png','image/jpeg','text/plain','application/vnd.openxmlformats-officedocument.wordprocessingml.document']);
const labelSize=(size:number)=>size<1024?size+' B':(size/1024/1024).toFixed(2)+' MB';

export function DocumentsPage(){
 const {api,role,patient}=useSession();
 const [documents,setDocuments]=useState<DocumentRow[]>([]);
 const [relationships,setRelationships]=useState<Relationship[]>([]);
 const [patientId,setPatientId]=useState('');
 const [file,setFile]=useState<File|null>(null);
 const [busy,setBusy]=useState(false);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const fileRef=useRef<HTMLInputElement|null>(null);
 const load=async()=>{
  setError('');setLoading(true);
  try{
   const [docs,rels]=await Promise.all([
    api<DocumentRow[]>('/documents'),
    role==='caregiver'?api<Relationship[]>('/caregiver/relationships'):Promise.resolve([]),
   ]);
   setDocuments(docs);setRelationships(rels);
   setPatientId(current=>current||rels.find(r=>r.status==='active')?.patient_id||'');
  }catch(e){setError(e instanceof Error?e.message:'Unable to load documents.')}
  finally{setLoading(false)}
 };
 useEffect(()=>{void load()},[api,role]);

 function choose(e:ChangeEvent<HTMLInputElement>){
  const next=e.target.files?.[0]||null;
  setError('');setNotice('');
  if(!next){setFile(null);return}
  const detected=next.type||(extensionMime[next.name.split('.').pop()?.toLowerCase()||'']||'');
  if(!mimeTypes.has(detected)){setError('Upload PDF, DOCX, PNG, JPG, or UTF-8 TXT files only.');setFile(null);return}
  if(next.size>MAX_BYTES){setError('Files must be 3 MB or smaller.');setFile(null);return}
  setFile(next);
 }
 async function submit(e:FormEvent){
  e.preventDefault();if(!file||busy)return;
  if(role==='caregiver'&&!patientId){setError('Choose an accepted patient first.');return}
  setBusy(true);setError('');setNotice('');
  try{
   await api.uploadFile(file,role==='caregiver'?patientId:undefined);
   setFile(null);if(fileRef.current)fileRef.current.value='';
   setNotice(role==='caregiver'?'Document added to the patient record.':'Document uploaded privately. Turn on sharing for any file the caregiver should see.');
   await load();
  }catch(err){setError(err instanceof Error?err.message:'Upload failed.')}
  finally{setBusy(false)}
 }
 async function save(blob:DocumentRow){
  setError('');
  try{
   const content=await api.downloadFile(blob.id);
   const url=URL.createObjectURL(content);
   const anchor=document.createElement('a');anchor.href=url;anchor.download=blob.name;
   document.body.appendChild(anchor);anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(err){setError(err instanceof Error?err.message:'Unable to download.')}
 }
 async function sharing(doc:DocumentRow){
  setBusy(true);setError('');
  try{
   await api<DocumentRow>(`/documents/${doc.id}/sharing`,'PATCH',{shared_with_caregivers:!doc.shared_with_caregivers});
   setNotice(doc.shared_with_caregivers?'Caregiver access to this file is now off.':'Shared with currently accepted caregivers. Revoking a caregiver invitation will revoke their access.');
   await load();
  }catch(err){setError(err instanceof Error?err.message:'Sharing update failed.')}
  finally{setBusy(false)}
 }
 async function remove(doc:DocumentRow){
  if(!window.confirm('Delete this document from the patient record permanently?'))return;
  setBusy(true);setError('');
  try{await api('/documents/'+doc.id,'DELETE');setNotice('Document deleted.');await load()}
  catch(err){setError(err instanceof Error?err.message:'Delete failed.')}
  finally{setBusy(false)}
 }
 const accepted=relationships.filter(r=>r.status==='active');
 return <div className="docs-page">
  <div className="page-intro"><div className="eyebrow">SHARED RECOVERY FILES</div><h1>Documents</h1>
   <p>{role==='patient'?'Keep your recovery paperwork organized, and choose what trusted caregivers can see.':'View documents a patient shares with you, or contribute a file to an accepted patient account.'}</p></div>
  <div className="docs-notice"><Lock size={18}/> Fictional demo files only. Do not upload real medical or identifying documents. Files are stored in the configured demo database.</div>
  <section className="docs-panel">
   <h2><Upload size={21}/> Upload a document</h2>
   <p>Accepted: PDF, DOCX, PNG, JPG, and UTF-8 TXT · Maximum 3 MB per file.</p>
   <form onSubmit={submit} className="docs-form">
    {role==='caregiver'&&<label>Upload to patient
     <select required value={patientId} onChange={e=>setPatientId(e.target.value)}>
      <option value="">Select an accepted patient</option>
      {accepted.map(r=><option value={r.patient_id} key={r.id}>Patient {r.patient_id.slice(0,8)}</option>)}
     </select>
    </label>}
    <label>Choose a file<input ref={fileRef} type="file" required accept=".pdf,.docx,.png,.jpg,.jpeg,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,text/plain" onChange={choose}/></label>
    {file&&<small>Selected: {file.name} ({labelSize(file.size)})</small>}
    <button className="btn primary" disabled={busy||!file||(role==='caregiver'&&!patientId)} type="submit"><Upload size={17}/>{busy?'Saving…':'Upload document'}</button>
   </form>
   {role==='caregiver'&&!accepted.length&&<p>No accepted patient invitation is available yet. The patient must invite you and you must accept before uploading to their record.</p>}
  </section>
  <section className="docs-panel">
   <div className="docs-header"><h2><FileText size={21}/> Your documents</h2><button className="btn secondary" type="button" onClick={()=>void load()}><RefreshCw size={16}/> Refresh</button></div>
   {loading?<p>Loading documents…</p>:documents.length===0?<p>No documents are visible yet. Upload a fictional sample file to get started.</p>:
    <div className="docs-list">{documents.map(doc=><article className="docs-item" key={doc.id}>
     <div className="docs-icon"><FileText size={22}/></div>
     <div className="docs-detail"><strong>{doc.name}</strong>
      <span>{labelSize(doc.byte_size)} · {new Date(doc.created_at).toLocaleDateString()} · Uploaded by {doc.uploader_role}</span>
      {role==='patient'&&<span>{doc.shared_with_caregivers?'Available to accepted caregivers':'Private to patient (and the original caregiver uploader, if applicable)'}</span>}
     </div>
     <div className="docs-actions">
      <button type="button" className="btn secondary" onClick={()=>void save(doc)}><Download size={16}/> Download</button>
      {doc.can_manage&&<button type="button" disabled={busy} className="btn secondary" onClick={()=>void sharing(doc)}>{doc.shared_with_caregivers?<ShieldOff size={16}/>:<ShieldCheck size={16}/>} {doc.shared_with_caregivers?'Unshare':'Share with caregivers'}</button>}
      {doc.can_manage&&<button type="button" disabled={busy} className="btn secondary" onClick={()=>void remove(doc)}><Trash2 size={16}/> Delete</button>}
     </div>
    </article>)}</div>}
  </section>
  {role==='patient'&&<div className="docs-notice"><Users size={18}/> Only caregivers with accepted invitations can see documents you share. Files are not automatically sent by email or text.</div>}
  {notice&&<p className="docs-feedback" role="status">{notice}</p>}
  {error&&<p className="docs-feedback docs-error" role="alert">{error}</p>}
 </div>
}
