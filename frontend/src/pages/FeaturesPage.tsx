import {Link} from 'react-router-dom';
import {
  Activity, ArrowRight, CalendarDays, ChartNoAxesCombined, HeartHandshake,
  House, LockKeyhole, MessageCircle, Pill, Settings, ShieldAlert, Stethoscope
} from 'lucide-react';
import type {LucideIcon} from 'lucide-react';

type Feature = {
  title:string;
  description:string;
  destination:string;
  icon:LucideIcon;
  available:boolean;
  category:'Track recovery'|'Care and support'|'Your account';
};

export const featureDirectory:Feature[] = [
  {title:'Recovery overview',description:'A daily dashboard for your check-ins, scheduled doses, trends and active demo alerts.',destination:'/',icon:House,available:true,category:'Track recovery'},
  {title:'Medication management',description:'Record prescribed medications, daily schedules, doses, corrections and refill awareness.',destination:'/medications',icon:Pill,available:true,category:'Track recovery'},
  {title:'Daily check-ins',description:'Log your own wellbeing, pain, symptoms and activity, then correct earlier entries.',destination:'/check-in',icon:Activity,available:true,category:'Track recovery'},
  {title:'Recovery trends',description:'See charts based on your own recorded check-in observations.',destination:'/progress',icon:ChartNoAxesCombined,available:true,category:'Track recovery'},
  {title:'Safety and alerts',description:'Review prototype alerts and safety guidance; no emergency monitoring or clinician notification.',destination:'/alerts',icon:ShieldAlert,available:true,category:'Care and support'},
  {title:'Recovery assistant',description:'Chat about approved demo instructions. Generative AI and voice are not yet connected.',destination:'/assistant',icon:MessageCircle,available:true,category:'Care and support'},
  {title:'Caregiver access',description:'Invite fictional caregivers, choose sharing permissions and revoke consent.',destination:'/caregivers',icon:HeartHandshake,available:true,category:'Care and support'},
  {title:'Appointments',description:'Appointment booking and scheduling are not connected to a service yet.',destination:'/appointments',icon:CalendarDays,available:false,category:'Care and support'},
  {title:'Care-team messages',description:'Secure care-team messaging is not connected to a service yet.',destination:'/messages',icon:Stethoscope,available:false,category:'Care and support'},
  {title:'Account settings',description:'Update the fictional patient profile and time zone, or sign out.',destination:'/settings',icon:Settings,available:true,category:'Your account'}
];

export function FeaturesPage({guest=false}:{guest?:boolean}){
  return <div className={'feature-hub'+(guest?' feature-hub-guest':'')}>
    {guest&&<header className="feature-guest-nav"><Link to="/" className="feature-brand"><span className="brand-mark"><Activity size={21}/></span>UR<span>Chart</span></Link><Link to="/" className="btn ghost">Sign in <ArrowRight size={16}/></Link></header>}
    <div className="feature-heading">
      <div className="eyebrow dark">EXPLORE UR CHART</div>
      <h1>All your recovery tools, <span>in one place.</span></h1>
      <p>Explore what's built for our synthetic cardiovascular recovery demonstration. Enter the shared demo code to explore connected tools. Appointments and direct care-team messaging remain unavailable.</p>
    </div>
    <div className="feature-important" role="note"><LockKeyhole size={20}/><div><strong>Educational demonstration only.</strong> Not for actual patient information, real clinical decisions, or emergency monitoring. Enter the shared demo code and choose Patient or Caregiver. No email is required. This is not clinical software.</div></div>
    {(['Track recovery','Care and support','Your account'] as const).map(category=><section key={category} className="feature-group" aria-label={category}>
      <h2>{category}</h2>
      <div className="feature-grid">
        {featureDirectory.filter(feature=>feature.category===category).map(feature=>{
          const Icon=feature.icon;
          return <article className="feature-tile" key={feature.title}>
            <div className="feature-tile-top"><span className="feature-tile-icon"><Icon size={22}/></span><span className={'feature-status'+(feature.available?'':' feature-status-planned')}>{feature.available?'Built · Sign-in required':'Not connected'}</span></div>
            <h3>{feature.title}</h3><p>{feature.description}</p>
            <Link to={feature.destination} className="feature-tile-link">{feature.available?'Open feature':'View status'} <ArrowRight size={16}/></Link>
          </article>;
        })}
      </div>
    </section>)}
    {guest&&<div className="feature-start"><strong>Ready to explore the dashboard?</strong><Link to="/" className="btn primary">Return to sign in <ArrowRight size={16}/></Link></div>}
  </div>;
}
