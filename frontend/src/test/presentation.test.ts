import {describe,expect,it} from 'vitest';
import {orderAlerts} from '../services/presentation';
import type {SafetyAlert} from '../types/api';

describe('shared safety alert presentation',()=>{
 it('puts emergency records first without mutating the API response or hiding resolved records',()=>{
  const alerts=[
   {id:'routine',severity:'routine',status:'active'},
   {id:'resolved-emergency',severity:'emergency',status:'resolved'},
   {id:'urgent',severity:'urgent',status:'active'},
   {id:'review',severity:'needs_clinical_review',status:'active'},
  ] as SafetyAlert[];
  const result=orderAlerts(alerts);
  expect(result.map(a=>a.id)).toEqual(['resolved-emergency','urgent','review','routine']);
  expect(alerts.map(a=>a.id)).toEqual(['routine','resolved-emergency','urgent','review']);
 });
});
