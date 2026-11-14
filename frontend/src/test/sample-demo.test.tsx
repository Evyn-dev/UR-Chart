import {describe,expect,it,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {PatientSampleDemo} from '../components/PatientSampleDemo';

describe('read-only patient sample',()=>{
 it('shows seven days of fictional data and allows exit',()=>{
  const exit=vi.fn();
  render(<PatientSampleDemo onExit={exit}/>);
  expect(screen.getByText(/Fictional sample data/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'My recovery'}));
  expect(screen.getAllByRole('row')).toHaveLength(8);
  fireEvent.click(screen.getByRole('button',{name:'Medications'}));
  expect(screen.getByText(/14\/14/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:/Exit demo/}));
  expect(exit).toHaveBeenCalledOnce();
 });
});
