// Derive calendar dates from the patient's IANA timezone, not the browser's timezone.
export function patientDay(timezone:string,now=new Date()){
  try{
    const parts=new Intl.DateTimeFormat('en-US',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
    const value=(kind:string)=>parts.find(part=>part.type===kind)?.value;
    return `${value('year')}-${value('month')}-${value('day')}`;
  }catch{return now.toISOString().slice(0,10)}
}
export function rangeEnding(end:string,days:number){const d=new Date(`${end}T12:00:00Z`);d.setUTCDate(d.getUTCDate()-days+1);return {start:d.toISOString().slice(0,10),end}}
export function dayLabel(day:string){return new Date(day+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'})}
