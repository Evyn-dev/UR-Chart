import {useState} from 'react';
import {Activity,ArrowLeft,HeartPulse,Pill,ShieldAlert} from 'lucide-react';

const days=[
 {day:'Monday',pain:3,mood:'Okay',walking:10,meds:2},
 {day:'Tuesday',pain:3,mood:'Okay',walking:12,meds:2},
 {day:'Wednesday',pain:2,mood:'Good',walking:14,meds:2},
 {day:'Thursday',pain:2,mood:'Good',walking:15,meds:2},
 {day:'Friday',pain:2,mood:'Good',walking:17,meds:2},
 {day:'Saturday',pain:1,mood:'Good',walking:18,meds:2},
 {day:'Sunday',pain:1,mood:'Good',walking:20,meds:2},
];
const sections=['Overview','My recovery','Medications','Daily check-in','Recovery assistant','Safety & alerts'] as const;
type Section=typeof sections[number];

export function PatientSampleDemo({onExit}:{onExit:()=>void}){
 const [section,setSection]=useState<Section>('Overview');
 return <div style={{minHeight:'100vh',padding:'24px',maxWidth:1100,margin:'auto'}}>
  <header style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:16,flexWrap:'wrap'}}>
   <h1><HeartPulse size={26} aria-hidden="true"/> URChart Patient Demo</h1>
   <button type="button" className="btn" onClick={onExit}><ArrowLeft size={16}/> Exit demo</button>
  </header>
  <p role="status"><strong>Fictional sample data · Read-only preview.</strong> No account is required. No changes are saved or sent to the server. This is not medical advice.</p>
  <nav aria-label="Demo navigation" style={{display:'flex',flexWrap:'wrap',gap:8,margin:'24px 0'}}>
   {sections.map(s=><button key={s} type="button" className={'btn '+(section===s?'primary':'')} aria-current={section===s?'page':undefined} onClick={()=>setSection(s)}>{s}</button>)}
  </nav>
  <main>
   <h2>{section==='Overview'?'Hello, Alex.':section}</h2>
   {section==='Overview'&&<><p>Welcome to Alex Morgan's sample cardiovascular surgery recovery chart.</p>
    <div style={{display:'flex',flexWrap:'wrap',gap:16}}>
     <article className="mon-card" style={{padding:20,flex:'1 1 200px'}}><Activity/> <h3>7 check-ins</h3><p>One fictional entry each day</p></article>
     <article className="mon-card" style={{padding:20,flex:'1 1 200px'}}><Pill/> <h3>100% sample adherence</h3><p>14 of 14 scheduled sample doses recorded</p></article>
     <article className="mon-card" style={{padding:20,flex:'1 1 200px'}}><ShieldAlert/> <h3>Sample alerts</h3><p>One educational reminder, no active emergency</p></article>
    </div>
   </>}
   {section==='My recovery'&&<><p>Seven days of sample walking, discomfort and mood entries.</p><div style={{overflowX:'auto'}}><table style={{width:'100%',borderCollapse:'collapse'}}><thead><tr><th scope="col">Day</th><th scope="col">Walk (min)</th><th scope="col">Discomfort (0–10)</th><th scope="col">Mood</th></tr></thead><tbody>{days.map(d=><tr key={d.day}><th scope="row">{d.day}</th><td>{d.walking}</td><td>{d.pain}</td><td>{d.mood}</td></tr>)}</tbody></table></div></>}
   {section==='Medications'&&<><p>Illustrative medication schedule only; names and doses are placeholders, not prescriptions.</p><ul><li>Sample medication A — morning dose recorded on all seven days</li><li>Sample medication B — evening dose recorded on all seven days</li></ul><p>Sample adherence: 14/14 (100%).</p></>}
   {section==='Daily check-in'&&<><p>Completed sample check-ins: 7/7 days.</p><ul>{days.map(d=><li key={d.day}>{d.day}: walking {d.walking} minutes, discomfort {d.pain}/10, mood {d.mood}</li>)}</ul></>}
   {section==='Recovery assistant'&&<><h3>Understanding this sample chart</h3><p>This preview illustrates how a patient might review recovery trends and medication history. The assistant does not send messages in demo mode.</p><p>For urgent symptoms, contact emergency services or follow your clinical team's instructions; do not rely on this sample.</p></>}
   {section==='Safety & alerts'&&<><p><strong>Educational sample reminder:</strong> Review discharge instructions and contact your care team with questions.</p><p>No live symptom screening is performed in this demo. A fictional record cannot determine medical safety.</p></>}
  </main>
 </div>
}
