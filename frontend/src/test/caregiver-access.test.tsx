import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,describe,expect,it,vi} from 'vitest';
import {SessionProvider} from '../hooks/session';
import {CaregiversPage} from '../pages/Pages';

const patient={id:'caregiver',display_name:'Synthetic caregiver',timezone:'UTC',created_at:'',updated_at:''};
const relationship={id:'shared-patient',caregiver_user_id:'caregiver',status:'active',permissions:['recovery_summary']};
const dashboard={relationship_id:relationship.id,patient_display_name:'Private summary content'};
const ok=(data:unknown)=>({ok:true,json:async()=>({data})});
const denied=(status:number)=>({ok:false,status,json:async()=>({error:{message:'Access no longer available'}})});
afterEach(()=>vi.unstubAllGlobals());

function mount(dashboardRequest:()=>Promise<unknown>){
 vi.stubGlobal('fetch',vi.fn((url:string)=>{
  if(url.includes('/dashboard?'))return dashboardRequest();
  if(url.includes('/caregiver/relationships?'))return Promise.resolve(ok([relationship]));
  return Promise.resolve(ok([]));
 }));
 render(<MemoryRouter><SessionProvider token="synthetic-token" initialPatient={patient} signOut={()=>{}}><CaregiversPage/></SessionProvider></MemoryRouter>);
}

describe('caregiver summary access',()=>{
 it.each([403,404])('clears previously viewed data when access returns %s',async status=>{
  const request=vi.fn().mockResolvedValueOnce(ok(dashboard)).mockResolvedValueOnce(denied(status));
  mount(request);const user=userEvent.setup();
  const view=await screen.findByRole('button',{name:"Open patient's chart"});
  await user.click(view);
  expect(await screen.findByRole('heading',{name:/Private summary content's shared patient chart/})).toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Close patient chart'}));
  await user.click(screen.getByRole('button',{name:"Open patient's chart"}));
  expect(await screen.findByText('Access no longer available')).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:/Private summary content's shared patient chart/})).not.toBeInTheDocument();
 });

 it('does not restore a late successful response after a newer access denial',async()=>{
  let resolveOld!:(value:unknown)=>void;
  const oldRequest=new Promise(resolve=>{resolveOld=resolve});
  const request=vi.fn().mockReturnValueOnce(oldRequest).mockResolvedValueOnce(denied(404));
  mount(request);const user=userEvent.setup();
  const view=await screen.findByRole('button',{name:"Open patient's chart"});
  await user.click(view);
  await user.click(screen.getByRole('button',{name:'Close patient chart'}));
  await user.click(screen.getByRole('button',{name:"Open patient's chart"}));
  await waitFor(()=>expect(request).toHaveBeenCalledTimes(2));
  expect(await screen.findByText('Access no longer available')).toBeInTheDocument();
  await act(async()=>resolveOld(ok(dashboard)));
  expect(screen.queryByRole('heading',{name:/Private summary content's shared patient chart/})).not.toBeInTheDocument();
 });
});
