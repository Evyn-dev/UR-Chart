import {useEffect,useState} from 'react';
import {Link,Navigate,Route,Routes,useLocation} from 'react-router-dom';
import {Activity,ArrowRight,HeartPulse,KeyRound,ShieldAlert,Users,UserRound} from 'lucide-react';
import {SessionProvider} from './hooks/session';
import {createClient} from './services/client';
import {patientsApi} from './services/patients';
import type {Patient} from './types/api';
import {Shell} from './components/Shell';
import {MonitorBackdrop,EcgTrace} from './components/MonitorBackdrop';
import {ClaraAssistant} from './components/ClaraAssistant';
import {OperationProvider,OperationSetup} from './components/OperationTemplates';
import {FeaturesPage} from './pages/FeaturesPage';
import {DocumentsPage} from './pages/DocumentsPage';
import {Dashboard,MedicationsPage,CheckinPage,ProgressPage,AlertsPage,CaregiversPage,SettingsPage,UnavailablePage} from './pages/Pages';

const sessionKey='urchart-demo-session';
function DemoLogin({onLogin}:{onLogin:(token:string,patient:Patient)=>void}){
 const [token,setToken]=useState('');
 const [persona,setPersona]=useState<'patient'|'caregiver'>('patient');
 const [working,setWorking]=useState(false);
 const [error,setError]=useState('');
 const [manual,setManual]=useState(false);
 async function enterDemo(role:'patient'|'caregiver'){
  setWorking(true);setError('');
  try{
   const base=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/$/,'');
   const response=await fetch(`${base}/api/demo/session`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role}),cache:'no-store'});
   const result=await response.json().catch(()=>null);
   if(!response.ok||typeof result?.data?.token!=='string')throw new Error('One-click demo is not enabled on this server. Use the existing demo access code or ask the host to enable PUBLIC_DEMO_ENABLED=true.');
   const credential=result.data.token;
   const patient=await patientsApi(createClient(credential)).me();
   onLogin(credential,patient);
  }catch(e){setError(e instanceof Error?e.message:'Unable to enter the demo.');setManual(true)}
  finally{setWorking(false)}
 }
 async function submit(e:React.FormEvent){
  e.preventDefault();if(!token.trim())return;
  setWorking(true);setError('');
  try{
   // Hosted shared demo accepts a role suffix; local DEMO_TOKENS expects the raw token.
   // Try the hosted form first, then the original token if and only if auth rejects it.
   const hostedCredential=token.trim()+':'+persona;
   let credential=hostedCredential;
   let patient:Patient;
   try{patient=await patientsApi(createClient(hostedCredential)).me()}
   catch(e){
    if(!(e instanceof Error) || !('status' in e) || e.status!==401)throw e;
    credential=token.trim();
    patient=await patientsApi(createClient(credential)).me();
   }
   onLogin(credential,patient);
  }
  catch(e){setError(e instanceof Error?e.message:'Unable to connect.')}
  finally{setWorking(false)}
 }
 return <div className="mon-screen"><MonitorBackdrop/>
  <header className="mon-nav"><div className="mon-brand"><HeartPulse size={26}/><strong>UR<span>Chart</span></strong></div><Link to="/features" className="mon-link">Explore all features <ArrowRight size={16}/></Link></header>
  <main className="mon-main">
   <section className="mon-hero">
    <div className="mon-eyebrow"><span className="mon-dot"/> YOUR RECOVERY COMPANION</div>
    <h1>Your recovery,<br/><em>made clearer.</em></h1>
    <p>Explore medication tracking, check-ins, progress and caregiver tools in one recovery space.</p>
    <div className="mon-features"><span><Activity size={16}/> Daily recovery tracking</span><span><ShieldAlert size={16}/> Clear safety guidance</span></div>
   </section>
   <section className="mon-card" aria-label="Enter fictional demo">
    <h2 style={{margin:'0 0 8px',color:'#17304A'}}>Explore the demo</h2>
    <p style={{color:'#526C80',fontSize:13,marginBottom:18}}>Choose a role. No access code needed when public demo mode is enabled.</p>
    <button className="btn primary wide" type="button" disabled={working} onClick={()=>{void enterDemo('patient')}}><UserRound size={19}/> {working?'Connecting…':'Enter as Patient'} <ArrowRight size={16}/></button>
    <button className="btn wide" style={{marginTop:10,background:'#EAF3FA',border:'1px solid #BFD9E8',color:'#173F61'}} type="button" disabled={working} onClick={()=>{void enterDemo('caregiver')}}><Users size={19}/> Enter as Caregiver <ArrowRight size={16}/></button>
    <p className="entry-foot" style={{marginTop:16}}>Fictional shared data only. Caregivers see patient information only after an invitation is accepted. No real medical monitoring.</p>
    {error&&<div role="alert" className="feedback error">{error}</div>}
    <button type="button" className="mon-link" onClick={()=>setManual(v=>!v)} style={{background:'none',border:0,cursor:'pointer',margin:'12px auto 0',display:'flex'}}>{manual?'Hide code login':'Use an existing demo code instead'}</button>
    {manual&&<form onSubmit={submit} className="entry-form">
     <label htmlFor="demo-token">Demo access code</label>
     <div className="field-with-icon"><KeyRound size={18}/><input id="demo-token" value={token} onChange={e=>setToken(e.target.value)} type="password" autoComplete="off" placeholder="Enter your demo code" required/></div>
     <label htmlFor="demo-persona" style={{marginTop:12}}>Demo role</label>
     <select id="demo-persona" value={persona} onChange={e=>setPersona(e.target.value as 'patient'|'caregiver')}>
      <option value="patient">Patient</option><option value="caregiver">Caregiver (test sharing)</option>
     </select>
      <button className="btn primary wide" disabled={working} type="submit">{working?'Connecting…':'Enter recovery dashboard'}<ArrowRight size={18}/></button>
    </form>}
   </section>
  </main>
  <div className="mon-trace"><EcgTrace/><div className="mon-readout"><HeartPulse size={34}/><b>72</b><span>BPM · SAMPLE DISPLAY</span></div></div>
  <footer className="mon-steps"><div><b>01</b><span>Check in</span></div><div><b>02</b><span>Stay on track</span></div><div><b>03</b><span>Feel supported</span></div></footer>
 </div>
}
export default function App(){
  const {pathname}=useLocation();
  const [token,setToken]=useState(()=>{try{return sessionStorage.getItem(sessionKey)||''}catch{return ''}});
  const [patient,setPatient]=useState<Patient|null>(null);const [checking,setChecking]=useState(Boolean(token));
  useEffect(()=>{
    let active=true;
    if(!token){setChecking(false);setPatient(null);return}
    setChecking(true);
    patientsApi(createClient(token)).me()
      .then(p=>{if(active)setPatient(p)})
      .catch(()=>{if(active){setPatient(null);setToken('');try{sessionStorage.removeItem(sessionKey)}catch{/* optional */}}})
      .finally(()=>{if(active)setChecking(false)});
    return()=>{active=false};
  },[token]);
  function login(nextToken:string,nextPatient:Patient){
    try{sessionStorage.setItem(sessionKey,nextToken)}catch{/* optional */}
    setPatient(nextPatient);setToken(nextToken);
  }
  function signOut(){
    try{sessionStorage.removeItem(sessionKey)}catch{/* optional */}
    setPatient(null);setToken('');
  }
  if(checking)return <div className="startup"><HeartPulse size={36}/><p>Opening your recovery space…</p></div>;
  if(!token||!patient)return pathname==='/features'?<FeaturesPage guest/>:<DemoLogin onLogin={login}/>;
  return <SessionProvider token={token} initialPatient={patient} role={token.endsWith(":caregiver")||token.startsWith("public-demo.caregiver.")?"caregiver":"patient"} signOut={signOut}>
    <OperationProvider key={patient.id} patientId={patient.id} enabled={!(token.endsWith(':caregiver')||token.startsWith("public-demo.caregiver."))}>
    <Routes><Route element={<Shell/>}>
      <Route path="/" element={(token.endsWith(":caregiver")||token.startsWith("public-demo.caregiver."))?<Navigate to="/caregivers" replace/>:<Dashboard/>}/><Route path="/features" element={<FeaturesPage/>}/><Route path="/medications" element={<MedicationsPage/>}/><Route path="/check-in" element={<CheckinPage/>}/><Route path="/progress" element={<ProgressPage/>}/><Route path="/assistant" element={<Dashboard/>}/><Route path="/alerts" element={<AlertsPage/>}/><Route path="/caregivers" element={<CaregiversPage/>}/><Route path="/settings" element={<SettingsPage/>}/><Route path="/documents" element={<DocumentsPage/>}/>
      <Route path="/appointments" element={<UnavailablePage title="Appointments" reason="Appointments are not connected to a backend service yet."/>}/>
      <Route path="/messages" element={<UnavailablePage title="Care team messages" reason="Secure care team messaging is not connected yet. Use your discharge paperwork to contact your clinical team."/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Route></Routes>
    <ClaraAssistant/>
    <OperationSetup/>
    </OperationProvider>
  </SessionProvider>
}
