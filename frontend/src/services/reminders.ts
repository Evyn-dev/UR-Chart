import type {Client} from './client';

export type Repeat='once'|'daily'|'weekdays'|'weekly'|'monthly';
export interface ReminderInput {title:string;notes:string;due_at:string;timezone:string;repeat:Repeat}
export interface Reminder extends ReminderInput {id:string;version:number;active:boolean;last_action:string|null;last_action_at:string|null}
export type ReminderAction='complete'|'dismiss'|'snooze'|'toggle'|'delete';
export const remindersApi=(api:Client)=>({
 list:(offset=0,active?:boolean)=>api<Reminder[]>(`/reminders?limit=50&offset=${offset}${active===undefined?'':`&active=${active}`}`),
 create:(body:ReminderInput)=>api<Reminder>('/reminders','POST',body),
 edit:(reminder:Reminder,body:ReminderInput)=>api<Reminder>(`/reminders/${reminder.id}`,'PATCH',{...body,expected_version:reminder.version}),
 action:(reminder:Reminder,action:ReminderAction)=>api<Reminder|null>(`/reminders/${reminder.id}/action`,'POST',{action,expected_version:reminder.version}),
});

export function localReminderTime(instant:string,zone:string){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(instant));
 const value=(type:string)=>parts.find(p=>p.type===type)?.value;
 return `${value('year')}-${value('month')}-${value('day')}T${value('hour')}:${value('minute')}`;
}

/** Convert an IANA wall time, independent of the browser's own time zone. */
export function reminderInstant(local:string,zone:string){
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(local))throw new Error('Enter a valid date and time.');
 const guess=Date.parse(local+'Z');
 if(!Number.isFinite(guess)||new Date(guess).toISOString().slice(0,16)!==local)throw new Error('Enter a valid date and time.');
 const offsets=new Set<number>();
 for(let hours=-36;hours<=36;hours+=6){
  const sample=guess+hours*3600000;
  offsets.add(Date.parse(localReminderTime(new Date(sample).toISOString(),zone)+'Z')-sample);
 }
 const candidates=[...offsets].map(offset=>guess-offset).filter(value=>localReminderTime(new Date(value).toISOString(),zone)===local).sort((a,b)=>a-b);
 if(!candidates.length)throw new Error('This local time does not exist because of daylight saving. Choose another time.');
 // Repeated fall-back hours select the earlier occurrence, matching the backend.
 return new Date(candidates[0]).toISOString();
}
