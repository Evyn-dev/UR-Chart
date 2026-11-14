import {Heart, Activity} from 'lucide-react';

type Props = {thinking:boolean; speaking:boolean};

/** Animated status only; it does not display or simulate patient vitals. */
export function AssistantStatus({thinking,speaking}:Props){
 if(!thinking&&!speaking)return null;
 return <div className="assistant-activity" role="status" aria-live="polite" aria-label={thinking?'Chart is thinking': 'Chart is speaking'}>
   {thinking?<div className="assistant-ecg" aria-hidden="true">
      <svg className="assistant-ecg-svg" viewBox="0 0 240 56" preserveAspectRatio="none">
        <path d="M0 28 H24 L33 28 L41 19 L47 38 L56 4 L65 49 L74 28 H94 Q104 16 114 28 H120 M120 28 H144 L153 28 L161 19 L167 38 L176 4 L185 49 L194 28 H214 Q224 16 234 28 H240"/>
      </svg>
      <Activity className="assistant-ecg-icon" size={18}/>
    </div>:<div className="assistant-heart" aria-hidden="true"><Heart size={32} fill="currentColor" strokeWidth={1.5}/></div>}
   <div>
     <strong>{thinking?'Chart is thinking…':'Chart is speaking…'}</strong>
     <p>{thinking?'Preparing your response':'Reading the answer aloud'}</p>
   </div>
 </div>;
}
