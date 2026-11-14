import {useEffect,useState} from 'react';
import {Link,Navigate,Route,Routes,useLocation} from 'react-router-dom';
import {Activity,ArrowRight,HeartPulse,KeyRound,LockKeyhole,ShieldAlert} from 'lucide-react';
import {SessionProvider} from './hooks/session';
import {createClient} from './services/client';
import {patientsApi} from './services/patients';
import type {Patient} from './types/api';
import {Shell} from './components/Shell';
import {FeaturesPage} from './pages/FeaturesPage';
import {Dashboard,MedicationsPage,CheckinPage,ProgressPage,AlertsPage,AssistantPage,CaregiversPage,SettingsPage,UnavailablePage} from './pages/Pages';

const sessionKey='urchart-demo-session';
function DemoLogin({onLogin}:{onLogin:(token:string,patient:Patient)=>void}){
 const [token,setToken]=useState('');
 const [persona,setPersona]=useState<'patient'|'caregiver'>('patient');
 const [working,setWorking]=useState(false);
 const [error,setError]=useState('');
 async function submit(e:React.FormEvent){
  e.preventDefault();if(!token.trim())return;
  setWorking(true);setError('');
  try{const credential=token.trim()+':'+persona;const patient=await patientsApi(createClient(credential)).me();onLogin(credential,patient)}
  catch(e){setError(e instanceof Error?e.message:'Unable to connect.')}
  finally{setWorking(false)}
 }
 return <div className="entry-screen"><div className="entry-pattern"/><main className="entry-card">
  <div className="entry-brand"><div className="brand-mark"><HeartPulse size={23}/></div><strong>UR<span>Chart</span></strong></div>
  <div className="entry-eyebrow"><span className="eyebrow-dot"/> YOUR RECOVERY COMPANION</div>
  <h1>Your recovery,<br/><em>made clearer.</em></h1>
  <p>Explore medication tracking, check-ins, progress and caregiver tools in one recovery space.</p>
  <div className="entry-features"><span><Activity size={16}/> Daily recovery tracking</span><span><ShieldAlert size={16}/> Clear safety guidance</span></div>
  <form onSubmit={submit} className="entry-form">
   <label htmlFor="demo-token">Demo access code</label>
   <div className="field-with-icon"><KeyRound size={18}/><input id="demo-token" value={token} onChange={e=>setToken(e.target.value)} type="password" autoComplete="off" placeholder="Enter your demo code" required/></div>
   <label htmlFor="demo-persona" style={{marginTop:12}}>Demo role</label>
   <select id="demo-persona" value={persona} onChange={e=>setPersona(e.target.value as 'patient'|'caregiver')}>
     <option value="patient">Patient</option>
     <option value="caregiver">Caregiver (test sharing)</option>
   </select>
   {error&&<div role="alert" className="feedback error">{error}</div>}
   <button className="btn primary wide" disabled={working} type="submit">{working?'Connecting…':'Enter recovery dashboard'}<ArrowRight size={18}/></button>
  </form>
  <Link to="/features" className="entry-explore">Explore all features <ArrowRight size={16}/></Link>
  <p className="entry-foot"><LockKeyhole size={14}/> No email required. Shared fictional patient for demonstration only. Anyone holding the code can access its records. Never enter real health data.</p>
 </main><aside className="entry-aside"><div className="aside-heart"><HeartPulse size={72} strokeWidth={1.3}/></div><span className="eyebrow">ONE DAY AT A TIME</span><h2>Good care should<br/>feel less complicated.</h2><p>Understand what's next. Keep up with your routine. Have your support system close by.</p><div className="aside-stats"><div><b>01</b><span>Check in</span></div><div><b>02</b><span>Stay on track</span></div><div><b>03</b><span>Feel supported</span></div></div></aside></div>
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
  return <SessionProvider token={token} initialPatient={patient} signOut={signOut}>
    <Routes><Route element={<Shell/>}>
      <Route path="/" element={<Dashboard/>}/><Route path="/features" element={<FeaturesPage/>}/><Route path="/medications" element={<MedicationsPage/>}/><Route path="/check-in" element={<CheckinPage/>}/><Route path="/progress" element={<ProgressPage/>}/><Route path="/assistant" element={<AssistantPage/>}/><Route path="/alerts" element={<AlertsPage/>}/><Route path="/caregivers" element={<CaregiversPage/>}/><Route path="/settings" element={<SettingsPage/>}/>
      <Route path="/appointments" element={<UnavailablePage title="Appointments" reason="Appointments are not connected to a backend service yet."/>}/>
      <Route path="/messages" element={<UnavailablePage title="Care team messages" reason="Secure care team messaging is not connected yet. Use your discharge paperwork to contact your clinical team."/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Route></Routes>
  </SessionProvider>
}
