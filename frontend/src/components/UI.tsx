import type {ReactNode} from 'react';
import {AlertCircle,ArrowRight,CheckCircle2,RefreshCw} from 'lucide-react';
import {Link} from 'react-router-dom';
export function PageIntro({eyebrow,title,subtitle,action}:{eyebrow:string;title:string;subtitle?:string;action?:ReactNode}){return <div className="page-intro"><div><div className="eyebrow dark">{eyebrow}</div><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</div>{action&&<div className="page-action">{action}</div>}</div>}
export function Panel({title,subtitle,action,children,className=''}:{title:string;subtitle?:string;action?:ReactNode;children:ReactNode;className?:string}){return <section className={'panel '+className}><div className="panel-top"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div>{action}</div>{children}</section>}
export function Empty({message,detail,action}:{message:string;detail?:string;action?:ReactNode}){return <div className="empty-state"><div className="empty-symbol"><CheckCircle2 size={22}/></div><b>{message}</b>{detail&&<p>{detail}</p>}{action}</div>}
export function Loader({label='Loading your information…'}:{label?:string}){return <div className="loading-state" role="status"><span className="spinner"/>{label}</div>}
export function ErrorState({message,onRetry}:{message:string;onRetry?:()=>void}){return <div className="feedback error" role="alert"><AlertCircle size={18}/><span>{message}</span>{onRetry&&<button onClick={onRetry} className="text-button"><RefreshCw size={14}/> Retry</button>}</div>}
export function Success({message}:{message:string}){return <div className="feedback success" role="status"><CheckCircle2 size={17}/>{message}</div>}
export function ActionLink({to,children}:{to:string;children:ReactNode}){return <Link className="link-more" to={to}>{children}<ArrowRight size={16}/></Link>}
export function SeverityPill({severity}:{severity:string}){return <span className={'severity-pill '+severity.replace(/[^a-z_]/g,'')}>{severity==='needs_clinical_review'?'Review needed':severity.charAt(0).toUpperCase()+severity.slice(1)}</span>}
export function Stat({label,value,detail,icon}:{label:string;value:ReactNode;detail:string;icon:ReactNode}){return <div className="stat-card"><div className="stat-card-head"><span>{label}</span><div className="stat-icon">{icon}</div></div><div className="stat-value">{value}</div><p>{detail}</p></div>}
