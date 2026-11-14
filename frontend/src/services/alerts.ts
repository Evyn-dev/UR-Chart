import type {Client} from './client';
import type {SafetyAlert} from '../types/api';
export const alertsApi=(api:Client)=>({list:(offset=0)=>api<SafetyAlert[]>(`/alerts?limit=100&offset=${offset}`),action:(alert:SafetyAlert,action:string,reason:string,emergencySeen=false)=>api<SafetyAlert>(`/alerts/${alert.id}/actions`,'POST',{expected_version:alert.version,action,reason,emergency_guidance_seen:emergencySeen})});
