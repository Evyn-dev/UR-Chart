import type {SafetyAlert} from '../types/api';


export const severityOrder:Record<string,number>={emergency:0,urgent:1,needs_clinical_review:2,routine:3};
export function friendlyTime(value:string){const d=new Date(value);return Number.isNaN(d.valueOf())?value:d.toLocaleTimeString([],{hour:'numeric',minute:'2-digit'})}
export function friendlyDate(value:string){const d=new Date(value);return Number.isNaN(d.valueOf())?value:d.toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'})}
export function messageOf(e:unknown){return e instanceof Error?e.message:'Something went wrong. Please retry.'}

// Copy before sorting so cached API responses are never mutated.
export function orderAlerts(items:SafetyAlert[]){
 return items.slice().sort((a,b)=>(severityOrder[a.severity]??9)-(severityOrder[b.severity]??9));
}
