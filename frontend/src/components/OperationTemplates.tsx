import {createContext, useContext, useState} from 'react';
import type {ReactNode} from 'react';
import {ClipboardList, HeartPulse, ShieldCheck, X} from 'lucide-react';

type OperationId = 'bypass' | 'valve' | 'joint' | 'abdominal' | 'other';
interface RecoveryTemplate {
 id:OperationId;
 title:string;
 category:string;
 focus:string[];
 questions:string[];
}
export const operationTemplates:RecoveryTemplate[] = [
 {id:'bypass',title:'Coronary bypass (CABG)',category:'Heart surgery',focus:['Record how you feel each day, including discomfort, energy and any changes around the incision.','Keep your medication list and care-team contact information easy to find.','Review your own written activity and follow-up instructions.'],questions:['What activity or lifting restrictions apply to my discharge plan?','Which changes should prompt a call to my surgical team?']},
 {id:'valve',title:'Heart valve procedure',category:'Heart surgery',focus:['Track energy, discomfort and any new symptoms using daily check-ins.','Keep a record of prescribed medications and follow-up appointments.','Refer to the discharge plan for any procedure-specific restrictions.'],questions:['Do I need any particular follow-up tests or medication monitoring?','Which symptoms should prompt an urgent call to my care team?']},
 {id:'joint',title:'Hip or knee replacement',category:'Orthopedic surgery',focus:['Record discomfort and daily activity as permitted by your care team.','Keep rehabilitation appointments and mobility instructions available.','Track any questions or changes you want to discuss at follow-up.'],questions:['What are my current movement and weight-bearing restrictions?','What changes around the incision should I report?']},
 {id:'abdominal',title:'Abdominal surgery',category:'General surgery',focus:['Track discomfort, energy and any symptoms you notice.','Review your own incision-care, food and activity instructions.','Write down any concerns for your scheduled follow-up.'],questions:['What eating and activity instructions apply to my procedure?','Which symptoms mean I should contact the surgical team?']},
 {id:'other',title:'Another procedure',category:'General recovery',focus:['Use daily check-ins to record how you feel and any new symptoms.','Keep your written discharge instructions and prescribed medication schedule close by.','Write down questions and planned follow-up visits.'],questions:['What recovery milestones should I track for my particular operation?','Who should I contact if I notice new or worsening symptoms?']}
];
type ContextValue = {selected:RecoveryTemplate|null;setOperation:(id:OperationId)=>void;promptOpen:boolean;closePrompt:()=>void};
const OperationContext=createContext<ContextValue|null>(null);
const isOperationId=(value:string|null):value is OperationId=>operationTemplates.some(item=>item.id===value);
function readSelection(key:string):OperationId|null{
 try{const value=sessionStorage.getItem(key);return isOperationId(value)?value:null}catch{return null}
}
/** Fictional demo preference only: not persisted to the medical API or shared with Clara. */
export function OperationProvider({patientId,enabled,children}:{patientId:string;enabled:boolean;children:ReactNode}){
 const key='urchart-demo-operation-'+patientId;
 const [operation,setSelected]=useState<OperationId|null>(()=>enabled?readSelection(key):null);
 const [dismissed,setDismissed]=useState(false);
 const selected=operationTemplates.find(item=>item.id===operation)||null;
 const setOperation=(id:OperationId)=>{setSelected(id);setDismissed(false);try{sessionStorage.setItem(key,id)}catch{/* demo preference optional */}};
 return <OperationContext.Provider value={{selected,setOperation,promptOpen:enabled&&!selected&&!dismissed,closePrompt:()=>setDismissed(true)}}>{children}</OperationContext.Provider>;
}
export function useOperation(){const value=useContext(OperationContext);if(!value)throw new Error('OperationProvider required');return value}

export function OperationPicker({compact=false}:{compact?:boolean}){
 const {selected,setOperation}=useOperation();
 return <div className={'operation-picker'+(compact?' compact':'')}>
   <label htmlFor={compact?'operation-setting':'operation-onboarding'}>Type of operation</label>
   <select id={compact?'operation-setting':'operation-onboarding'} value={selected?.id||''} onChange={e=>{if(isOperationId(e.target.value))setOperation(e.target.value)}}>
     <option value="" disabled>Select a procedure</option>
     {operationTemplates.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}
   </select>
 </div>;
}
export function OperationSetup(){
 const {promptOpen,closePrompt,selected}=useOperation();
 if(!promptOpen||selected)return null;
 return <div className="operation-setup-backdrop">
   <section className="operation-setup" role="dialog" aria-modal="true" aria-labelledby="operation-setup-title" aria-describedby="operation-setup-description">
     <div className="operation-setup-top"><span className="operation-setup-icon"><ClipboardList size={22}/></span><button aria-label="Skip operation selection" className="operation-skip" onClick={closePrompt}><X size={21}/></button></div>
     <p className="operation-eyebrow">PERSONALIZE YOUR DEMO</p>
     <h2 id="operation-setup-title">What type of operation did you have?</h2>
     <p id="operation-setup-description">Choose a fictional procedure to preview a matching recovery template. You can change your selection in Settings.</p>
     <OperationPicker/>
     <div className="operation-setup-note"><ShieldCheck size={18}/><span>Educational demo only. Templates are not medical orders and do not replace your own discharge instructions.</span></div>
     <button type="button" className="operation-later" onClick={closePrompt}>I'll choose later</button>
   </section>
 </div>;
}
export function OperationOverview(){
 const {selected}=useOperation();
 return <section className="operation-overview" aria-label="Recovery template">
   <div className="operation-overview-heading"><span className="operation-overview-icon"><HeartPulse size={20}/></span><div><span className="operation-eyebrow">YOUR RECOVERY TEMPLATE</span><h2>{selected?.title||'Choose your operation'}</h2></div></div>
   {selected?<><p className="operation-category">{selected.category} · Fictional template</p>
     <h3>Things to track</h3><ul>{selected.focus.map(item=><li key={item}>{item}</li>)}</ul>
     <h3>Questions for your care team</h3><ul>{selected.questions.map(item=><li key={item}>{item}</li>)}</ul>
   </>:<p>Choose a procedure in Settings to preview recovery tracking prompts.</p>}
   <p className="operation-disclaimer">This selection is saved only in this browser session. Existing medical records, alerts, and Clara answers are not changed.</p>
 </section>;
}
