import {act,renderHook,waitFor} from '@testing-library/react';
import {describe,expect,it} from 'vitest';
import {useResource} from '../hooks/useResource';

describe('useResource',()=>{
  it('ignores stale results and stale errors after dependencies change',async()=>{
    let resolveFirst!:(value:string)=>void;
    let rejectFirst!:(reason:Error)=>void;
    const first=new Promise<string>((resolve,reject)=>{resolveFirst=resolve;rejectFirst=reject});
    let resolveSecond!:(value:string)=>void;
    const second=new Promise<string>(resolve=>{resolveSecond=resolve});
    const {result,rerender}=renderHook(({step})=>useResource(()=>step===1?first:second,[step]),{initialProps:{step:1}});
    rerender({step:2});
    await act(async()=>{rejectFirst(new Error('Old request failed'));resolveSecond('fresh')});
    await waitFor(()=>expect(result.current.data).toBe('fresh'));
    expect(result.current.error).toBe('');
    expect(result.current.loading).toBe(false);
    void resolveFirst;
  });
});
