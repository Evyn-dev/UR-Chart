import {render,screen,fireEvent} from '@testing-library/react';
import {afterEach,beforeEach,describe,expect,it} from 'vitest';
import {OperationProvider,OperationPicker,OperationOverview,OperationCheckinGuide} from '../components/OperationTemplates';

describe('procedure-aware rehabilitation examples',()=>{
 beforeEach(()=>sessionStorage.clear());
 afterEach(()=>sessionStorage.clear());
 function View(){return <OperationProvider patientId="synthetic-1" enabled><OperationPicker/><OperationOverview/><OperationCheckinGuide/></OperationProvider>}
 it('shows distinct knee and cardiac recovery phases',()=>{
  render(<View/>);
  fireEvent.change(screen.getByLabelText('Type of operation'),{target:{value:'knee'}});
  expect(screen.getByText('Days 0–7 · Early mobility')).toBeInTheDocument();
  expect(screen.getByText(/knee bending, straightening/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Type of operation'),{target:{value:'bypass'}});
  expect(screen.getByText('Weeks 2–6 · Gradual activity')).toBeInTheDocument();
  expect(screen.getByText(/sternum if sternotomy/)).toBeInTheDocument();
  expect(screen.queryByText('Days 0–7 · Early mobility')).not.toBeInTheDocument();
 });
 it('uses surgery date to highlight the applicable educational stage',()=>{
  render(<View/>);
  fireEvent.change(screen.getByLabelText('Type of operation'),{target:{value:'valve'}});
  const daysAgo=new Date(Date.now()-15*86400000).toISOString().slice(0,10);
  fireEvent.change(screen.getByLabelText('Surgery date (optional)'),{target:{value:daysAgo}});
  expect(screen.getByText('Weeks 2–4 · Home recovery')).toBeInTheDocument();
  expect(screen.getByText('Current stage')).toBeInTheDocument();
 });
 it('does not invent a timeline for an unspecified operation',()=>{
  render(<View/>);
  fireEvent.change(screen.getByLabelText('Type of operation'),{target:{value:'other'}});
  expect(screen.getByText(/This generic demo has no procedure-specific rehabilitation schedule/)).toBeInTheDocument();
 });
});
