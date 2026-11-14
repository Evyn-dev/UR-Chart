import {afterEach,describe,expect,it,vi} from 'vitest';
import {ApiError,createClient} from '../services/client';

describe('shared FastAPI client',()=>{
 afterEach(()=>vi.unstubAllGlobals());
 it('unwraps data and includes demo bearer token at request time',async()=>{
  const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({data:{display_name:'Synthetic patient'}})});
  vi.stubGlobal('fetch',fetcher);
  const patient=await createClient('a-test-token','https://test.example')<{display_name:string}>('/patients/me');
  expect(patient.display_name).toBe('Synthetic patient');
  expect(fetcher).toHaveBeenCalledWith('https://test.example/api/patients/me',expect.objectContaining({headers:expect.objectContaining({Authorization:'Bearer a-test-token'})}));
 });
 it('shows validation errors without dumping server internals',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422,json:async()=>({detail:[{loc:['body','day'],msg:'Invalid'}]})}));
  await expect(createClient('token')('/checkins','POST',{})).rejects.toMatchObject({name:'ApiError',status:422,message:'Some fields were invalid. Please check the form.'});
 });
 it('reports connection failures as retryable service issues',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('socket closed')));
  await expect(createClient('token')('/alerts')).rejects.toBeInstanceOf(ApiError);
 });
});
