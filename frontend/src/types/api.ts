export interface RecordBase { id:string; created_at:string; updated_at:string }
export interface Patient extends RecordBase { display_name:string; timezone:string }
export interface Medication extends RecordBase { name:string; dosage:string; schedule:string; active:boolean; reminder_times:string[]; supply_remaining:number|null; refill_threshold:number|null }
export type MedicationInput = Pick<Medication,'name'|'dosage'|'schedule'|'reminder_times'|'supply_remaining'|'refill_threshold'> & {active?:boolean};
export interface Dose { medication_id:string; schedule_id:string; scheduled_for:string; local_day:string; local_time:string; timezone:string; status:'taken'|'skipped'|'missed'|'unrecorded'; due:boolean; overdue:boolean; log_id:string|null }
export interface DoseLog extends RecordBase { version:number; medication_id:string; status:string; recorded_at:string; scheduled_for:string|null; units_used:number|null }
export interface Adherence { expected_due:number; scheduled_taken:number; scheduled_skipped:number; confirmed_missed:number; unrecorded:number; overdue_unrecorded:number; scheduled_adherence_percent:number|null; schedule_issues:unknown[] }
export interface Refill { medication_id:string; supply_remaining:number|null; refill_threshold:number|null; estimated_days_remaining:number|null; refill_needed:boolean|null; status:string; message:string; actual_supply?:number|null }
export interface MedicationSummary { medications:Medication[]; today:string; today_doses:Dose[]; completed_records:DoseLog[]; unrecorded_doses:Dose[]; refill_warnings:Refill[]; adherence:Record<string,Adherence>; limit:number; offset:number; has_more:boolean; start:string; end:string }
export interface Symptom { code:string; present:boolean; severity?:'mild'|'moderate'|'severe'; description?:string }
export interface CheckinInput { day:string; wellbeing?:number|null; pain_level?:number|null; activity_minutes?:number|null; activity_type?:string|null; note?:string|null; symptoms?:string[]; symptom_reports?:Symptom[] }
export interface Checkin extends RecordBase,CheckinInput { version:number }
export interface Trends { days_recorded:number; expected_days:number; missing_days:number; consistency_percent:number|null; averages:Record<string,number|null>; metric_counts:Record<string,number>; first_to_last_change:Record<string,number|null>; latest_comparison:Record<string,unknown>; note:string }
export type Severity='routine'|'needs_clinical_review'|'urgent'|'emergency';
export interface SafetyAlert extends RecordBase { version:number; severity:Severity; category:string; message:string; status:string; prototype_only:boolean; notification_status:string; acknowledged_at:string|null; resolved_at?:string|null }
export interface Risk { status:string; prototype_only:boolean; alerts:SafetyAlert[]; guidance:string }
export interface Message extends RecordBase { role:string; content:string }
export interface Conversation extends RecordBase { title:string; messages?:Message[] }
export interface ChatReply { conversation_id:string; user_message:Message; assistant_message:Message }
export type Permission='recovery_summary'|'medication_adherence'|'checkin_summary'|'alerts';
export interface Relationship extends RecordBase { patient_id:string; caregiver_user_id:string; status:string; permissions:Permission[]; alert_severities:Severity[]; version:number }
export interface SharedDashboard { relationship_id:string; patient_display_name:string; permissions:Permission[]; recovery_summary?:Record<string,unknown>; medication_adherence?:Record<string,unknown>; checkin_summary?:Record<string,unknown>; alerts?:{id:string;severity:Severity;status:string;prototype_only:boolean;guidance:string;notification_status:string}[]; outstanding_tasks?:{type:string;description:string;count?:number}[]; alerts_has_more:boolean; notification_status:string }
