import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,describe,expect,it,vi} from 'vitest';
import {DemoLogin} from '../App';

const patient={id:'patient',display_name:'Synthetic patient',timezone:'UTC'};
afterEach(()=>vi.unstubAllGlobals());

describe('login credentials',()=>{
 it.each([
  ['demo_token','patient','local-token'],
  ['demo_code','patient','local-token:patient'],
  ['demo_code','caregiver','local-token:caregiver'],
  ['supabase','patient','local-token'],
 ])('preserves credentials for %s / %s',async(mode,persona,expected)=>{
  const fetcher=vi.fn(async(url:string,options?:RequestInit)=>{
   if(url.endsWith('/health'))return {ok:true,json:async()=>({data:{login_mode:mode}})};
   const authorized=(options?.headers as Record<string,string>).Authorization===`Bearer ${expected}`;
   return {ok:authorized,status:authorized?200:401,json:async()=>authorized?{data:patient}:{error:{message:'Invalid credential'}}};
  });
  vi.stubGlobal('fetch',fetcher);
  const onLogin=vi.fn();const user=userEvent.setup();
  render(<MemoryRouter><DemoLogin onLogin={onLogin}/></MemoryRouter>);
  const submit=await screen.findByRole('button',{name:/Enter recovery dashboard/});
  await waitFor(()=>expect(submit).toBeEnabled());
  await user.type(screen.getByLabelText(mode==='demo_code'?'Demo access code':'Access token'),'local-token');
  if(mode==='demo_code')await user.selectOptions(screen.getByLabelText('Demo role'),persona);
  else expect(screen.queryByLabelText('Demo role')).not.toBeInTheDocument();
  await user.click(submit);
  await waitFor(()=>expect(onLogin).toHaveBeenCalledWith(expected,patient));
 });

 it('does not submit credentials when authentication is unconfigured',async()=>{
  const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({data:{login_mode:'unconfigured'}})});
  vi.stubGlobal('fetch',fetcher);
  render(<MemoryRouter><DemoLogin onLogin={vi.fn()}/></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in is not configured');
  expect(screen.getByRole('button',{name:/Enter recovery dashboard/})).toBeDisabled();
  expect(fetcher).toHaveBeenCalledTimes(1);
 });
});
