import type {Client} from './client';
import type {Patient} from '../types/api';
export const patientsApi=(api:Client)=>({me:()=>api<Patient>('/patients/me'),update:(body:{display_name?:string;timezone?:string})=>api<Patient>('/patients/me','PATCH',body)});
