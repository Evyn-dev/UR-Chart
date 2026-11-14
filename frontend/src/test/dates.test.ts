import {describe,expect,it} from 'vitest';
import {patientDay,rangeEnding} from '../services/dates';
describe('patient calendar calculations',()=>{
 it('uses patient timezone rather than server/browser clock date',()=>{
  const timestamp=new Date('2026-11-14T02:30:00Z');
  expect(patientDay('America/New_York',timestamp)).toBe('2026-11-13');
  expect(patientDay('Asia/Tokyo',timestamp)).toBe('2026-11-14');
 });
 it('counts calendar window endpoints inclusively',()=>{
  expect(rangeEnding('2026-11-14',7)).toEqual({start:'2026-11-08',end:'2026-11-14'});
 });
});
