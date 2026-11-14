import {createContext,useContext,useEffect,useRef,useState} from 'react';
import type {ReactNode} from 'react';
import {useSession} from './session';
import {remindersApi} from '../services/reminders';

interface Controls {enabled:boolean;status:string;toggle:()=>Promise<void>}
const Context=createContext<Controls|null>(null);

export function ReminderNotificationsProvider({children}:{children:ReactNode}){
 const {api}=useSession();const [enabled,setEnabled]=useState(false);const [status,setStatus]=useState('Browser notifications are off.');
 const seen=useRef(new Set<string>());
 const permissionRequest=useRef(0);
 useEffect(()=>()=>{permissionRequest.current++},[]);
 async function toggle(){
  if(enabled){setEnabled(false);setStatus('Browser notifications are off.');return}
  if(!('Notification' in window)){setStatus('Browser notifications are unavailable here.');return}
  const request=++permissionRequest.current;
  try{
   const permission=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;
   if(request!==permissionRequest.current)return;
   if(permission!=='granted'){setStatus('Notification permission was not granted. Your reminders still appear here.');return}
   setEnabled(true);setStatus('Notifications enabled while this app is open.');
  }catch{if(request===permissionRequest.current)setStatus('Notifications could not be enabled. Your reminders still appear here.')}
 }
 useEffect(()=>{
  if(!enabled)return;
  let active=true;let timer:ReturnType<typeof setTimeout>|undefined;
  const open=new Set<Notification>();
  async function check(){
   try{
    if(Notification.permission!=='granted'){setEnabled(false);setStatus('Notification permission is no longer granted.');return}
    for(let offset=0;active;offset+=50){
     const reminders=await remindersApi(api).list(offset,true);
     if(!active)return;
     for(const reminder of reminders){
      const key=`${reminder.id}:${reminder.version}:${reminder.due_at}`;
      if(!reminder.active||Date.parse(reminder.due_at)>Date.now()||seen.current.has(key))continue;
      const notification=new Notification('UR Chart reminder',{body:'A personal reminder is due. Open UR Chart to review it.',tag:key});
      seen.current.add(key);open.add(notification);notification.onclose=()=>open.delete(notification);
     }
     if(reminders.length<50)break;
    }
    if(active)setStatus('Notifications enabled while this app is open.');
   }catch{if(active)setStatus('Unable to check reminders. Retrying while this app is open.')}
   finally{if(active)timer=setTimeout(check,30000)}
  }
  void check();
  return()=>{active=false;clearTimeout(timer);for(const notification of open)notification.close()};
 },[api,enabled]);
 return <Context.Provider value={{enabled,status,toggle}}>{children}</Context.Provider>;
}

export function useReminderNotifications(){
 const value=useContext(Context);
 if(!value)throw new Error('Reminder notification provider required');
 return value;
}
