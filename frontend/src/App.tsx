import {useEffect,useState} from 'react';
import {Link,Navigate,Route,Routes,useLocation} from 'react-router-dom';
import {Activity,ArrowRight,HeartPulse,KeyRound,LockKeyhole,ShieldAlert} from 'lucide-react';
import {SessionProvider} from './hooks/session';
import {createClient} from './services/client';
import {refreshSession,signIn,signUp,supabaseConfigured} from './services/supabaseAuth';
import {patientsApi} from './services/patients';
import type {Patient} from './types/api';
import {Shell} from './components/Shell';
import {FeaturesPage} from './pages/FeaturesPage';
import {Dashboard,MedicationsPage,CheckinPage,ProgressPage,AlertsPage,AssistantPage,CaregiversPage,SettingsPage,UnavailablePage} from './pages/Pages';

const sessionKey='urchart-demo-session';
const refreshKey='urchart-supabase-refresh';
function DemoLogin({onLogin}:{onLogin:(token:string,patient:Patient,refreshToken?:string)=>void}){
  const [token,setToken]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [register,setRegister]=useState(false);
  const [notice,setNotice]=useState('');
  const [working,setWorking]=useState(false);
  const [error,setError]=useState('');
  async function submit(e:React.FormEvent){
    e.preventDefault();setWorking(true);setError('');setNotice('');
    try{
      if(supabaseConfigured){
        const session=register?await signUp(email.trim(),password):await signIn(email.trim(),password);
        if(!session){
          setNotice('Check your email to confirm your account, then return here to sign in.');
          setRegister(false);
          return;
        }
        const patient=await patientsApi(createClient(session.access_token)).me();
        onLogin(session.access_token,patient,session.refresh_token);
      }else{
        if(!token.trim())return;
        const patient=await patientsApi(createClient(token.trim())).me();
        onLogin(token.trim(),patient);
      }
    }catch(e){setError(e instanceof Error?e.message:'Unable to connect.')}
    finally{setWorking(false)}
  }
  return <div className="entry-screen"><div className="entry-pattern"/><main className="entry-card">
    <div className="entry-brand"><div className="brand-mark"><HeartPulse size={23}/></div><strong>UR<span>Chart</span></strong></div>
    <div className="entry-eyebrow"><span className="eyebrow-dot"/> YOUR RECOVERY COMPANION</div>
    <h1>Your recovery,<br/><em>made clearer.</em></h1>
    <p>Everything you need to feel informed, organized, and supported after cardiovascular surgery, in one thoughtful space.</p>
    <div className="entry-features"><span><Activity size={16}/> Daily recovery tracking</span><span><ShieldAlert size={16}/> Clear safety guidance</span></div>
    <form onSubmit={submit} className="entry-form">
      {supabaseConfigured?<><label htmlFor="demo-email">Fictional demo account email</label><input id="demo-email" value={email} onChange={e=>setEmail(e.target.value)} type="email" autoComplete="email" placeholder="you@example.com" required/>
        <label htmlFor="demo-password" style={{marginTop:12}}>Password</label><div className="field-with-icon"><KeyRound size={18}/><input id="demo-password" value={password} onChange={e=>setPassword(e.target.value)} type="password" minLength={6} autoComplete={register?'new-password':'current-password'} required placeholder="Enter your account password"/></div></>
      :<><label htmlFor="demo-token">Fictional demo access token</label><div className="field-with-icon"><KeyRound size={18}/><input id="demo-token" value={token} onChange={e=>setToken(e.target.value)} type="password" autoComplete="off" placeholder="Paste your configured demo token" required/></div></>}
      {notice&&<div role="status" className="feedback success">{notice}</div>}
      {error&&<div role="alert" className="feedback error">{error}</div>}
      <button className="btn primary wide" disabled={working} type="submit">{working?'Connecting…':register?'Create demo account':'Enter recovery dashboard'}<ArrowRight size={18}/></button>
    </form>
    {supabaseConfigured&&<button type="button" className="text-button" style={{marginTop:14}} onClick={()=>{setRegister(v=>!v);setError('');setNotice('')}}>{register?'Already have an account? Sign in':'Need a demo account? Sign up'}</button>}
    <Link to="/features" className="entry-explore">Explore all features <ArrowRight size={16}/></Link>
    <p className="entry-foot"><LockKeyhole size={14}/> Educational demonstration only. Use fictional records. Sign-in sessions are kept in this browser tab only. Use fictional records, never real health information.</p>
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
    async function verify(){
      try{
        const p=await patientsApi(createClient(token)).me();
        if(active)setPatient(p);
      }catch{
        const oldRefresh=supabaseConfigured?sessionStorage.getItem(refreshKey):null;
        if(oldRefresh){
          try{
            const session=await refreshSession(oldRefresh);
            const p=await patientsApi(createClient(session.access_token)).me();
            if(active){
              sessionStorage.setItem(refreshKey,session.refresh_token);
              sessionStorage.setItem(sessionKey,session.access_token);
              setPatient(p);setToken(session.access_token);
              return;
            }
          }catch{/* Expired or invalid sessions require a fresh sign-in. */}
        }
        if(active){
          setPatient(null);setToken('');
          try{sessionStorage.removeItem(sessionKey);sessionStorage.removeItem(refreshKey)}catch{/* optional */}
        }
      }finally{if(active)setChecking(false)}
    }
    void verify();
    return()=>{active=false};
  },[token]);
  useEffect(()=>{
    if(!supabaseConfigured||!token)return;
    const id=window.setInterval(async()=>{
      const rt=sessionStorage.getItem(refreshKey);
      if(!rt)return;
      try{
        const session=await refreshSession(rt);
        sessionStorage.setItem(refreshKey,session.refresh_token);
        sessionStorage.setItem(sessionKey,session.access_token);
        setToken(session.access_token);
      }catch{signOut()}
    },30*60*1000);
    return()=>window.clearInterval(id);
  },[token]);
  function login(nextToken:string,nextPatient:Patient,refreshToken?:string){
    try{
      sessionStorage.setItem(sessionKey,nextToken);
      if(refreshToken)sessionStorage.setItem(refreshKey,refreshToken);
    }catch{/* optional */}
    setPatient(nextPatient);setToken(nextToken);
  }
  function signOut(){
    try{sessionStorage.removeItem(sessionKey);sessionStorage.removeItem(refreshKey)}catch{/* optional */}
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
