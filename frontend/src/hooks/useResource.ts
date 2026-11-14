import {useCallback,useEffect,useRef,useState} from 'react';

export function useResource<T>(load:()=>Promise<T>,deps:unknown[]=[]){
  const [data,setData]=useState<T>();
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const [version,setVersion]=useState(0);
  const generation=useRef(0);

  useEffect(()=>{
    let active=true;
    const id=++generation.current;
    const isCurrent=()=>active&&id===generation.current;

    setLoading(true);
    setError('');
    setData(undefined);
    Promise.resolve().then(load)
      .then(value=>{if(isCurrent())setData(value)})
      .catch(e=>{if(isCurrent())setError(e instanceof Error?e.message:'Unable to load data.')})
      .finally(()=>{if(isCurrent())setLoading(false)});

    return ()=>{active=false};
    // Callers provide the dependency list controlling when the resource reloads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[...deps,version]);

  const reload=useCallback(()=>setVersion(v=>v+1),[]);
  return {data,error,loading,reload};
}
