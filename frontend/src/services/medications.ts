import type {Client} from './client';
import type {Medication,MedicationInput,MedicationSummary,Dose,DoseLog,Adherence,Refill} from '../types/api';
export const medicationsApi=(api:Client)=>({
 list:(offset=0)=>api<Medication[]>(`/medications?limit=50&offset=${offset}`),
 summary:(start:string,end:string,offset=0)=>api<MedicationSummary>(`/medications/summary?start=${start}&end=${end}&limit=50&offset=${offset}`),
 create:(body:MedicationInput)=>api<Medication>('/medications','POST',body),
 update:(id:string,body:Partial<MedicationInput>)=>api<Medication>(`/medications/${id}`,'PATCH',body),
 log:(dose:Dose,status:'taken'|'skipped'|'missed',units?:number)=>api<DoseLog>(`/medications/${dose.medication_id}/log`,'POST',{schedule_id:dose.schedule_id,scheduled_for:dose.scheduled_for,recorded_at:new Date().toISOString(),status,...(units!==undefined?{units_used:units}:{})}),
 logs:(id:string,offset=0)=>api<DoseLog[]>(`/medications/${id}/logs?limit=50&offset=${offset}`),
 adherence:(id:string,start:string,end:string)=>api<Adherence>(`/medications/${id}/adherence?start=${start}&end=${end}`),
 refill:(id:string)=>api<Refill>(`/medications/${id}/refill`),
 reverse:(medicationId:string,log:DoseLog,reason:string)=>api<DoseLog>(`/medications/${medicationId}/logs/${log.id}`,'PATCH',{expected_version:log.version,status:'voided',reason,inventory_action:'adjust'})
});
