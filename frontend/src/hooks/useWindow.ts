import {useMemo} from 'react';
import {useSession} from '../hooks/session';
import {patientDay,rangeEnding} from '../services/dates';

export function useWindow(days=14){const {patient}=useSession();const today=patientDay(patient.timezone);return useMemo(()=>rangeEnding(today,days),[today,days])}
