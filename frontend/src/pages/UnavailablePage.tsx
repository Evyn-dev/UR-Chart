import {Link} from 'react-router-dom';
import {ArrowRight} from 'lucide-react';
import {Empty,PageIntro,Panel} from '../components/UI';

export function UnavailablePage({title,reason}:{title:string;reason:string}){return <><PageIntro eyebrow="COMING SOON" title={title} subtitle={reason}/><Panel title="Not connected yet"><Empty message="Feature not yet available" detail="This page does not send messages or create appointments. Use the care-team information from your actual discharge instructions." action={<Link className="btn primary" to="/">Back to overview <ArrowRight size={16}/></Link>}/></Panel></>}
