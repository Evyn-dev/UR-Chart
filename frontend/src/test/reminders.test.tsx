import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import {SessionProvider} from '../hooks/session';
import {ReminderNotificationsProvider} from '../hooks/reminderNotifications';
import {RemindersPage} from '../pages/RemindersPage';
import type {Reminder} from '../services/reminders';

const patient={id:'patient',display_name:'Synthetic',timezone:'America/New_York',created_at:'',updated_at:''};
const item:Reminder={id:'task',version:1,title:'Fictional task',notes:'Demo',due_at:'2026-01-01T14:00:00Z',timezone:'America/New_York',repeat:'once',active:true,last_action:null,last_action_at:null};
const ok=(data:unknown)=>({ok:true,json:async()=>({data})});
function mount(){return render(<SessionProvider token="test" initialPatient={patient} signOut={()=>{}}><ReminderNotificationsProvider><RemindersPage/></ReminderNotificationsProvider></SessionProvider>)}
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();vi.useRealTimers()});

it('creates, reloads, edits and completes a reminder through the shared API client',async()=>{
 let records:Reminder[]=[];
 const fetcher=vi.fn(async(url:string,options:RequestInit)=>{
  const body=options.body?JSON.parse(String(options.body)):null;
  if(options.method==='POST'&&url.endsWith('/reminders')){records=[{...item,...body}];return ok(records[0])}
  if(options.method==='PATCH'){expect(body.expected_version).toBe(1);records=[{...records[0],...body,version:2}];return ok(records[0])}
  if(url.endsWith('/action')){expect(body).toEqual({action:'complete',expected_version:2});records=[{...records[0],active:false,last_action:'complete',version:3}];return ok(records[0])}
  return ok(records);
 });
 vi.stubGlobal('fetch',fetcher);const user=userEvent.setup();const first=mount();
 await user.type(screen.getByLabelText('Reminder title'),'Fictional task');
 fireEvent.change(screen.getByLabelText('Date and time'),{target:{value:'2026-11-14T09:00'}});
 await user.click(screen.getByRole('button',{name:'Create reminder'}));
 expect(await screen.findByRole('article',{name:'Fictional task'})).toHaveTextContent('2026-11-14 09:00');
 expect(records[0].due_at).toBe('2026-11-14T14:00:00.000Z');
 first.unmount();mount();
 const card=await screen.findByRole('article',{name:'Fictional task'});
 await user.click(within(card).getByRole('button',{name:'Edit'}));
 await user.clear(screen.getByLabelText('Reminder title'));await user.type(screen.getByLabelText('Reminder title'),'Edited task');
 await user.click(screen.getByRole('button',{name:'Save changes'}));
 const updated=await screen.findByRole('article',{name:'Edited task'});
 await user.click(within(updated).getByRole('button',{name:'Complete'}));
 await waitFor(()=>expect(screen.getByRole('article',{name:'Edited task'})).toHaveTextContent('Inactive'));
});

it('requests notifications only after opt-in and notifies each occurrence once',async()=>{
 vi.useFakeTimers();const delivered=vi.fn();const close=vi.fn();
 class NotificationMock {
  static permission='default';static requestPermission=vi.fn(async()=>{NotificationMock.permission='granted';return 'granted'});
  onclose=null;close=close;constructor(title:string,options:unknown){delivered(title,options)}
 }
 vi.stubGlobal('Notification',NotificationMock);vi.stubGlobal('fetch',vi.fn(async()=>ok([item])));
 mount();expect(delivered).not.toHaveBeenCalled();expect(NotificationMock.requestPermission).not.toHaveBeenCalled();
 await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Enable notifications'}))});
 expect(NotificationMock.requestPermission).toHaveBeenCalledOnce();expect(delivered).toHaveBeenCalledOnce();
 expect(JSON.stringify(delivered.mock.calls)).not.toContain('Fictional task');
 await act(async()=>{await vi.advanceTimersByTimeAsync(30000)});
 expect(delivered).toHaveBeenCalledOnce();
 fireEvent.click(screen.getByRole('button',{name:'Disable notifications'}));expect(close).toHaveBeenCalled();
});

it('keeps reminders usable after notification permission is denied',async()=>{
 vi.stubGlobal('Notification',class {static permission='denied';static requestPermission=vi.fn()});
 vi.stubGlobal('fetch',vi.fn(async()=>ok([])));mount();
 await userEvent.click(screen.getByRole('button',{name:'Enable notifications'}));
 expect(await screen.findByText(/permission was not granted/)).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Create reminder'})).toBeEnabled();
});
