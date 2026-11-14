import {createContext,useContext,useState} from 'react';
import type {ReactNode} from 'react';
import {ClipboardList,HeartPulse,ShieldCheck,X} from 'lucide-react';

export type OperationId='bypass'|'valve'|'hip'|'knee'|'joint'|'abdominal'|'other';
type Phase={from:number;to:number|null;title:string;focus:string[]};
type RecoveryTemplate={id:OperationId;title:string;category:string;focus:string[];questions:string[];precautions:string[];phases:Phase[];sources:{label:string;url:string}[]};
export const operationTemplates:RecoveryTemplate[]=[
 {id:'bypass',title:'Coronary bypass (CABG)',category:'Heart surgery',focus:['Walking tolerance and energy','Incision changes and discomfort','Cardiac rehabilitation referral and follow-up'],precautions:['Chest-bone and upper-body precautions depend on how surgery was performed; follow your surgeon’s limits.','New chest pain, serious breathing trouble, or collapse require emergency assessment.'],questions:['When should I start supervised cardiac rehabilitation?','What are my exact lifting, driving, and wound-care restrictions?'],phases:[
 {from:0,to:13,title:'Days 0–13 · Immediate recovery',focus:['Review the hospital breathing-exercise and incision instructions.','Short, easy walking and frequent rest are typical after discharge, if cleared.','Plan for home support and report concerning changes to the surgical team.']},
 {from:14,to:41,title:'Weeks 2–6 · Gradual activity',focus:['Continue walking at a comfortable pace and record tolerance.','Protect a healing sternum if sternotomy was performed; confirm restrictions with the surgeon.','Ask about follow-up and starting a cardiac rehab program.']},
 {from:42,to:83,title:'Weeks 6–12 · Rebuilding endurance',focus:['Discuss gradual increases in activity and return-to-work or driving clearance.','Participate in cardiac rehabilitation when referred and cleared.','Review symptoms, medications and wound healing with the care team.']},
 {from:84,to:null,title:'After 12 weeks · Longer-term heart health',focus:['Continue your clinician-approved cardiac activity plan.','Follow secondary prevention and follow-up recommendations.','Record any new or worsening symptoms rather than assuming recovery is complete.']}
 ],sources:[{label:'MedlinePlus: bypass discharge',url:'https://www.medlineplus.gov/ency/patientinstructions/000102.htm'}]},
 {id:'valve',title:'Heart valve surgery',category:'Heart surgery',focus:['Energy and walking tolerance','Incision, breathing and symptom changes','Cardiology follow-up and medication monitoring'],precautions:['Open surgery and minimally invasive valve procedures have different restrictions.','Anticoagulant monitoring, when prescribed, is individualized; do not change doses from a template.'],questions:['Was my valve procedure open or minimally invasive, and what restrictions apply?','Do I need cardiac rehabilitation, follow-up imaging, or anticoagulant checks?'],phases:[
 {from:0,to:6,title:'First week · Early movement',focus:['Follow your team’s breathing, movement and incision-care instructions.','Begin gentle movement and walking as cleared during hospital recovery.','Confirm your specific medication and symptom-monitoring plan.']},
 {from:7,to:27,title:'Weeks 2–4 · Home recovery',focus:['Track energy and daily activity without treating milestones as requirements.','Increase ordinary activity gradually within written restrictions.','Confirm a cardiac rehab referral and cardiology follow-up.']},
 {from:28,to:55,title:'Weeks 4–8 · Typical recovery window',focus:['Many people regain function during this period, but timelines vary.','Review return to driving, work, and exercise with your surgeon.','Ask about valve follow-up and any ongoing medication monitoring.']},
 {from:56,to:null,title:'After 8 weeks · Follow-up and conditioning',focus:['Continue clinician-approved activity and cardiac rehabilitation where recommended.','Keep follow-up imaging or appointments on schedule.','Track new symptoms and discuss them with the care team.']}
 ],sources:[{label:'AHA: heart valve surgery recovery',url:'https://www.heart.org/en/health-topics/heart-valve-problems-and-disease/recovery-and-healthy-living-goals-for-heart-valve-patients/heart-valve-surgery-recovery-and-follow-up'}]},
 {id:'hip',title:'Hip replacement',category:'Orthopedic surgery',focus:['Walking aid and weight-bearing instructions','Pain, swelling and incision changes','Physical therapy and mobility'],precautions:['Weight-bearing and hip position precautions vary by surgical approach and surgeon.','Do not stop using a walker or cane based on a generic timeline.'],questions:['What is my allowed weight-bearing level and are hip precautions required?','Which exercises and mobility goals should my therapist supervise?'],phases:[
 {from:0,to:6,title:'Days 0–7 · Supported mobility',focus:['Walk with the assistive device and weight-bearing instructions given by the team.','Begin only assigned physical-therapy or home exercises.','Monitor pain, swelling and the incision.']},
 {from:7,to:20,title:'Weeks 2–3 · Walking practice',focus:['Build walking distance and safe daily activities with therapist guidance.','Continue the specific strengthening and range-of-motion program prescribed.','Ask when wound checks or follow-up are planned.']},
 {from:21,to:41,title:'Weeks 4–6 · Everyday function',focus:['Many patients regain more light daily activity around weeks 3–6.','Progress balance, mobility aids and strength only with clearance.','Review driving and any hip precautions with your team.']},
 {from:42,to:83,title:'Weeks 6–12 · Strength and stability',focus:['Continue prescribed rehab and gradual low-impact activity.','Check readiness for work and usual routines with your team.','Keep reviewing pain, mobility and incision concerns.']},
 {from:84,to:null,title:'After 12 weeks · Ongoing progress',focus:['Functional improvements can continue for months.','Maintain approved low-impact activity and follow-up.']}
 ],sources:[{label:'AAOS: total hip replacement',url:'https://www.orthoinfo.org/bodypart/hip-thigh/total-hip-replacement/'},{label:'AAOS: activities after hip replacement',url:'https://www.orthoinfo.org/bodypart/hip-thigh/activities-after-hip-replacement/'}]},
 {id:'knee',title:'Knee replacement',category:'Orthopedic surgery',focus:['Knee motion and stiffness','Walking aid, swelling and pain','Physical therapy adherence'],precautions:['Rehabilitation exercises, gait aids and activity progression should follow your PT program.','Unexpected severe symptoms, new marked swelling or wound changes need assessment.'],questions:['Which range-of-motion and strengthening exercises are prescribed?','When can I transition mobility aids or resume driving?'],phases:[
 {from:0,to:6,title:'Days 0–7 · Early mobility',focus:['Begin supervised walking with an approved mobility aid.','Follow the prescribed early knee movement and circulation exercises.','Track swelling, pain and incision concerns.']},
 {from:7,to:20,title:'Weeks 2–3 · Motion and walking',focus:['Continue PT-directed knee bending, straightening and strengthening.','Improve safe daily walking and transfers at your approved pace.','Ask the therapist about progress and mobility aids.']},
 {from:21,to:41,title:'Weeks 4–6 · Functional gains',focus:['Many people return to more light daily activities around weeks 3–6.','Continue range-of-motion, strength and balance rehabilitation.','Get individualized clearance before driving or returning to work.']},
 {from:42,to:83,title:'Weeks 6–12 · Continued rehabilitation',focus:['Progress low-impact conditioning and usual activities with your team.','Continue assigned exercises to improve motion and function.','Review persistent swelling or stiffness concerns with PT.']},
 {from:84,to:null,title:'After 12 weeks · Long-term function',focus:['Keep improving strength, movement and everyday function.','Continue recommended low-impact activities and follow-up.']}
 ],sources:[{label:'AAOS: total knee replacement',url:'https://www.orthoinfo.org/bodypart/kneelower-leg/total-knee-replacement/'},{label:'AAOS: knee exercise guide',url:'https://www.orthoinfo.org/bodypart/kneelower-leg/total-knee-replacement-exercise-guide/'}]},
 {id:'abdominal',title:'Abdominal surgery (open)',category:'General surgery',focus:['Walking and fatigue','Abdominal incision and activity tolerance','Bowel symptoms, nutrition and follow-up'],precautions:['This illustrative timeline is for major/open abdominal surgery, not every laparoscopic procedure.','Avoid heavy lifting until cleared; exact restrictions vary with incision and procedure.'],questions:['Which lifting restrictions and wound-care steps apply to my operation?','When is it safe to return to work, driving or higher-intensity exercise?'],phases:[
 {from:0,to:13,title:'Weeks 1–2 · Rest and gentle movement',focus:['Take short, comfortable walks as your team allows.','Alternate light activity and rest; fatigue is common.','Review your exact wound-care and lifting instructions.']},
 {from:14,to:27,title:'Weeks 2–4 · Light routines',focus:['Gradually increase walking and simple everyday tasks.','Avoid strenuous pushing, lifting and abdominal strain until cleared.','Track appetite, bowel symptoms and energy to discuss at review.']},
 {from:28,to:41,title:'Weeks 4–6 · Building stamina',focus:['Continue gently extending walks and light household activity.','Check with your team about driving and activity progression.','Do not assume an exercise or lifting restriction has expired.']},
 {from:42,to:83,title:'Weeks 6–12 · Gradual return',focus:['Many programs progressively reintroduce more activities with clearance.','Review heavier tasks, work and exercise with your surgeon.','Continue monitoring wound healing and symptoms.']},
 {from:84,to:null,title:'After 12 weeks · Individual follow-up',focus:['Return to normal activities according to your particular operation and care team.','Continue follow-up for any lasting limitations or symptoms.']}
 ],sources:[{label:'Cambridge University Hospitals: abdominal surgery',url:'https://www.cuh.nhs.uk/patient-information/advice-following-abdominal-surgery/'},{label:'Royal Free NHS: physiotherapy after abdominal surgery',url:'https://www.royalfree.nhs.uk/patients-and-visitors/patient-information-leaflets/physiotherapy-advice-and-exercises-after-abdominal-surgery/submit/43795'}]},
 {id:'other',title:'Another procedure',category:'General recovery',focus:['Symptoms and daily activity','Medication schedule as prescribed','Follow-up and care team questions'],precautions:['This generic demo has no procedure-specific rehabilitation schedule.','Your care team should provide your individual instructions.'],questions:['What is the expected recovery timeline for my procedure?','What movement restrictions and warning signs apply to me?'],phases:[],sources:[]},
 {id:'joint',title:'Hip or knee replacement (legacy selection)',category:'Orthopedic surgery',focus:['Mobility and physical therapy','Pain, swelling and recovery'],precautions:['Choose hip or knee to see the more specific rehab stages.'],questions:['Was the operation a hip or knee replacement?'],phases:[],sources:[]}
];
type ContextValue={selected:RecoveryTemplate|null;setOperation:(id:OperationId)=>void;date:string;setDate:(day:string)=>void;daysSince:number|null;currentPhase:Phase|null;promptOpen:boolean;closePrompt:()=>void};
const OperationContext=createContext<ContextValue|null>(null);
const isOperationId=(value:string|null):value is OperationId=>operationTemplates.some(item=>item.id===value);
const validDate=(value:string|null)=>!!value&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&!Number.isNaN(Date.parse(value+'T12:00:00Z'));
function read(key:string){try{return sessionStorage.getItem(key)}catch{return null}}
function save(key:string,value:string){try{sessionStorage.setItem(key,value)}catch{/* browser storage optional */}}
/** Session-only demo data: never a diagnosis, medical order, or shared patient record. */
export function OperationProvider({patientId,enabled,children}:{patientId:string;enabled:boolean;children:ReactNode}){
 const key='urchart-demo-operation-'+patientId;
 const [operation,setSelected]=useState<OperationId|null>(()=>enabled&&isOperationId(read(key))?read(key) as OperationId:null);
 const [date,setChosenDate]=useState(()=>{const value=read(key+'-date');return enabled&&validDate(value)?value!:''});
 const [dismissed,setDismissed]=useState(false);
 const selected=operationTemplates.find(item=>item.id===operation)||null;
 const setOperation=(id:OperationId)=>{setSelected(id);setDismissed(false);save(key,id)};
 const setDate=(day:string)=>{if(day&&!validDate(day))return;setChosenDate(day);save(key+'-date',day)};
 const daysSince=date?Math.floor((Date.now()-Date.parse(date+'T12:00:00Z'))/86400000):null;
 const elapsed=daysSince!==null&&daysSince>=0?daysSince:null;
 const currentPhase=selected&&elapsed!==null?selected.phases.find(p=>elapsed>=p.from&&(p.to===null||elapsed<=p.to))||null:null;
 return <OperationContext.Provider value={{selected,setOperation,date,setDate,daysSince:elapsed,currentPhase,promptOpen:enabled&&!selected&&!dismissed,closePrompt:()=>setDismissed(true)}}>{children}</OperationContext.Provider>
}
export function useOperation(){const value=useContext(OperationContext);if(!value)throw new Error('OperationProvider required');return value}
export function OperationPicker({compact=false}:{compact?:boolean}){
 const {selected,setOperation,date,setDate}=useOperation();
 return <div className={'operation-picker'+(compact?' compact':'')}>
  <label htmlFor={compact?'operation-setting':'operation-onboarding'}>Type of operation</label>
  <select id={compact?'operation-setting':'operation-onboarding'} value={selected?.id||''} onChange={e=>{if(isOperationId(e.target.value))setOperation(e.target.value)}}>
   <option value="" disabled>Select a procedure</option>{operationTemplates.filter(t=>t.id!=='joint').map(t=><option key={t.id} value={t.id}>{t.title}</option>)}
   {selected?.id==='joint'&&<option value="joint">Hip or knee — choose a specific joint</option>}
  </select>
  <label htmlFor={compact?'operation-date-setting':'operation-date-onboarding'}>Surgery date (optional)</label>
  <input id={compact?'operation-date-setting':'operation-date-onboarding'} type="date" value={date} max={new Date().toISOString().slice(0,10)} onChange={e=>setDate(e.target.value)}/>
  <p className="operation-date-help">Used only to show the matching education phase. Not sent to your medical record.</p>
 </div>
}
export function OperationSetup(){
 const {promptOpen,closePrompt,selected}=useOperation();
 if(!promptOpen||selected)return null;
 return <div className="operation-setup-backdrop"><section className="operation-setup" role="dialog" aria-modal="true" aria-labelledby="operation-setup-title" aria-describedby="operation-setup-description">
  <div className="operation-setup-top"><span className="operation-setup-icon"><ClipboardList size={22}/></span><button type="button" aria-label="Skip operation selection" className="operation-skip" onClick={closePrompt}><X size={21}/></button></div>
  <p className="operation-eyebrow">PERSONALIZE YOUR DEMO</p><h2 id="operation-setup-title">What type of operation did you have?</h2>
  <p id="operation-setup-description">Choose a fictional procedure and optionally its date. This changes the sample rehabilitation stages shown in the dashboard, not your clinical plan.</p>
  <OperationPicker/>
  <div className="operation-setup-note"><ShieldCheck size={18}/><span>Timelines are examples based on published guidance, not a prescription. Your surgeon's or therapist's restrictions always take priority.</span></div>
  <button type="button" className="operation-later" onClick={closePrompt}>I'll choose later</button>
 </section></div>
}
export function OperationOverview(){
 const {selected,daysSince,currentPhase,date}=useOperation();
 const focus=currentPhase?.focus||selected?.focus||[];
 return <section className="operation-overview" aria-label="Recovery template">
  <div className="operation-overview-heading"><span className="operation-overview-icon"><HeartPulse size={20}/></span><div><span className="operation-eyebrow">PROCEDURE-SPECIFIC RECOVERY</span><h2>{selected?.title||'Choose your operation'}</h2></div></div>
  {selected?<><p className="operation-category">{selected.category} · Educational example{date&&daysSince!==null?' · Day '+(daysSince+1):''}</p>
    {selected.phases.length>0?<><h3>Typical rehabilitation stages</h3><div className="operation-phases">{selected.phases.map(p=><div key={p.from} className={'operation-phase'+(currentPhase===p?' current':'')}><strong>{p.title}</strong>{currentPhase===p&&<span>Current stage</span>}</div>)}</div>
    <h3>{currentPhase?'Focus during this stage':'General recovery focus'}</h3><ul>{focus.map(item=><li key={item}>{item}</li>)}</ul>
    {!date&&<p className="operation-phase-hint">Add the surgery date in Settings to highlight the relevant stage.</p>}</>:<><h3>Recovery focus</h3><ul>{focus.map(item=><li key={item}>{item}</li>)}</ul></>}
    <h3>Procedure-specific precautions</h3><ul>{selected.precautions.map(item=><li key={item}>{item}</li>)}</ul>
    <h3>Questions for your care team</h3><ul>{selected.questions.map(item=><li key={item}>{item}</li>)}</ul>
    {selected.sources.length>0&&<div className="operation-sources"><strong>Clinical references</strong>{selected.sources.map(src=><a key={src.url} href={src.url} target="_blank" rel="noopener noreferrer">{src.label} ↗</a>)}</div>}
  </>:<p>Choose a procedure in Settings to preview a procedure-specific recovery schedule.</p>}
  <p className="operation-disclaimer">This is an educational timeline, not an exercise prescription or clearance to advance. Actual rehabilitation differs by procedure, complications and clinician instructions. Your selection is local to this browser session.</p>
 </section>
}

/** Contextual journaling prompts only; the underlying check-in fields remain unchanged. */
export function OperationCheckinGuide(){
 const {selected,currentPhase}=useOperation();
 if(!selected)return null;
 const items=(currentPhase?.focus||selected.focus).slice(0,3);
 return <aside className="operation-checkin-guide" aria-label="Procedure-specific check-in prompts">
   <strong>{selected.title}: things you may want to record</strong>
   {currentPhase&&<span className="operation-checkin-stage">{currentPhase.title}</span>}
   <ul>{items.map(item=><li key={item}>{item}</li>)}</ul>
   <small>Only record observations you actually experienced. Your care team's plan determines activities and restrictions.</small>
 </aside>;
}
