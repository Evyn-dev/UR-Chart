import {useCallback,useEffect,useRef,useState} from 'react';
export function useResource<T>(load:()=>Promise<T>,deps:unknown[]=[]){
 const [data,setData]=useState<T>();const [error,setError]=useState('');const [loading,setLoading]=useState(true);const [version,setVersion]=useState(0);const generation=useRef(0);
 useEffect(()=>{let active=true;const id=++generation.current;setLoading(true);setError('');setData(undefined);load().then(value=>{if(active&&id===generation.current)setData(value)}).catch(e=>{if(active)setError(e.message||'Unable to load data.')}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[...deps,version]);
 return {data,error,loading,reload:useCallback(()=>setVersion(v=>v+1),[])};
}
