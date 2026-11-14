import {expect,it} from 'vitest';
import {localReminderTime,reminderInstant} from '../services/reminders';

it('converts the selected timezone rather than the browser timezone',()=>{
 expect(reminderInstant('2026-11-14T09:00','America/New_York')).toBe('2026-11-14T14:00:00.000Z');
 expect(localReminderTime('2026-11-14T14:00:00Z','America/New_York')).toBe('2026-11-14T09:00');
 expect(reminderInstant('2026-11-14T09:00','Asia/Kolkata')).toBe('2026-11-14T03:30:00.000Z');
});
it('rejects nonexistent local times and picks the first repeated hour',()=>{
 expect(()=>reminderInstant('2026-03-08T02:30','America/New_York')).toThrow('does not exist');
 expect(reminderInstant('2026-11-01T01:30','America/New_York')).toBe('2026-11-01T05:30:00.000Z');
 expect(()=>reminderInstant('2026-02-31T09:00','UTC')).toThrow('valid date');
});
