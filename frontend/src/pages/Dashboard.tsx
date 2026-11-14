import {Link} from 'react-router-dom';
import {Activity,ArrowRight,CalendarCheck,HeartHandshake,HeartPulse,MessageCircle,Pill,ShieldAlert} from 'lucide-react';
import {useSession} from '../hooks/session';
import {useResource} from '../hooks/useResource';
import {medicationsApi} from '../services/medications';
import {checkinsApi} from '../services/checkins';
import {alertsApi} from '../services/alerts';
import {ActionLink,Empty,ErrorState,Loader,Panel,SeverityPill,Stat} from '../components/UI';
import type {SafetyAlert} from '../types/api';
import {Grid} from '../components/RecoveryUI';
import {useWindow} from '../hooks/useWindow';
import {DaySummary} from '../components/DaySummary';
import {orderAlerts} from '../services/presentation';
import {TrendChart} from '../components/RecoveryUI';
import {Notice} from '../components/RecoveryUI';
import {EcgTrace,MonitorBackdrop} from '../components/MonitorBackdrop';

function AlertPreview({items}:{items:SafetyAlert[]}){const active=orderAlerts(items.filter(a=>a.status!=='resolved'));return <div className="alert-preview">{active.slice(0,3).map(a=><div className={'alert-item alert-'+a.severity} key={a.id}><SeverityPill severity={a.severity}/><div><b>{a.category}</b><p>{a.message}</p></div></div>)}{!active.length&&<Empty message="No active alerts" detail="This is not a medical clearance. Always follow your care team's instructions."/>}</div>}
export function Dashboard(){const {api,patient}=useSession();const {start,end}=useWindow(14);const summaries=useResource(()=>medicationsApi(api).summary(start,end),[api,start,end]);const alerts=useResource(()=>alertsApi(api).list(),[api]);const checkins=useResource(()=>checkinsApi(api).list(start,end),[api,start,end]);const firstName=patient.display_name.split(' ')[0];
 const completed=checkins.data?.some(c=>c.day===end)||false;const nextDoses=summaries.data?.today_doses.filter(d=>d.status==='unrecorded').length||0;const activeAlerts=alerts.data?.filter(a=>a.status!=='resolved')||[];
 return <><div className="welcome-band"><MonitorBackdrop/><EcgTrace pleth={false}/><div><div className="eyebrow">YOUR DAILY RECOVERY SPACE</div><h1>Hello, {firstName}<span className="hello-dot">.</span></h1><p>Focus on what matters today. Your information, daily steps, and support are all right here.</p><Link to="/check-in" className="btn primary">{completed?'View check-in':'Start today’s check-in'}<ArrowRight size={17}/></Link></div><div className="welcome-art"><div className="heart-orbit"><HeartPulse size={75}/></div><span>One day at a time</span></div></div>
 <Grid><Stat label="Today's check-in" value={completed?'Completed':'Not recorded'} detail="A few minutes to reflect on how you feel" icon={<CalendarCheck size={22}/>}/><Stat label="Scheduled doses" value={summaries.data?String(summaries.data.today_doses.length):'—'} detail={`${nextDoses} without a recorded status`} icon={<Pill size={22}/>}/><Stat label="Active safety alerts" value={alerts.data?String(activeAlerts.length):'—'} detail="Prototype alerts, not emergency monitoring" icon={<ShieldAlert size={22}/>}/></Grid>
 <div className="content-columns"><div className="content-main"><Panel title="Today's medication schedule" subtitle="Record each dose according to your prescribed instructions" action={<ActionLink to="/medications">Manage medications</ActionLink>}>{summaries.loading?<Loader/>:summaries.error?<ErrorState message={summaries.error} onRetry={summaries.reload}/>:summaries.data?<DaySummary summary={summaries.data} onChanged={summaries.reload}/>:null}</Panel>
 <Panel title="Your recovery check-ins" subtitle="Your own observations over the past 14 days" action={<ActionLink to="/progress">Explore trends</ActionLink>}>{checkins.loading?<Loader/>:checkins.error?<ErrorState message={checkins.error} onRetry={checkins.reload}/>:<TrendChart records={checkins.data||[]}/>}</Panel></div><div className="content-side"><Panel title="Safety center" subtitle="Important guidance and alerts" action={<ActionLink to="/alerts">All alerts</ActionLink>}>{alerts.loading?<Loader/>:alerts.error?<ErrorState message={alerts.error} onRetry={alerts.reload}/>:<AlertPreview items={alerts.data||[]}/>}<Notice>For serious or life-threatening symptoms in the US, call 911. UR Chart does not notify emergency services.</Notice></Panel><Panel title="Quick support" subtitle="Tools whenever you need them"><div className="shortcut-list"><Link to="/assistant"><MessageCircle size={19}/>Ask the recovery assistant<ArrowRight size={16}/></Link><Link to="/caregivers"><HeartHandshake size={19}/>Manage caregiver access<ArrowRight size={16}/></Link><Link to="/check-in"><Activity size={19}/>Log how you feel<ArrowRight size={16}/></Link></div></Panel></div></div>
 </>}
