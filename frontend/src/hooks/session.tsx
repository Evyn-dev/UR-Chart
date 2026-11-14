import {createContext,useContext,useMemo,useState} from 'react';
import type {ReactNode} from 'react';
import {createClient} from '../services/client';
import type {Client} from '../services/client';
import type {Patient} from '../types/api';
interface Session {api:Client;patient:Patient;setPatient:(p:Patient)=>void;signOut:()=>void}
const Context=createContext<Session|null>(null);
export function SessionProvider({token,initialPatient,signOut,children}:{token:string;initialPatient:Patient;signOut:()=>void;children:ReactNode}){
 const api=useMemo(()=>createClient(token),[token]); const [patient,setPatient]=useState(initialPatient);
 return <Context.Provider value={{api,patient,setPatient,signOut}}>{children}</Context.Provider>
}
export function useSession(){const session=useContext(Context);if(!session)throw new Error('Session required');return session}
