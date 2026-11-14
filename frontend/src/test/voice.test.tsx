import {act,render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import {ChartVoice} from '../components/ChartVoice';

afterEach(()=>vi.unstubAllGlobals());
class Recognition {
 static last:Recognition;
 continuous=false;interimResults=false;lang='';
 onresult:((e:{resultIndex:number;results:{transcript:string}[][]})=>void)|null=null;
 onerror:((e:{error:string})=>void)|null=null;onend:(()=>void)|null=null;
 start=vi.fn();stop=vi.fn();
 constructor(){Recognition.last=this}
}
it('fails gracefully without browser recognition',async()=>{
 vi.stubGlobal('SpeechRecognition',undefined);vi.stubGlobal('webkitSpeechRecognition',undefined);
 render(<ChartVoice onQuestion={vi.fn()} latestReply=""/>);
 await userEvent.click(screen.getByRole('button',{name:'Enable voice'}));
 expect(screen.getByRole('status')).toHaveTextContent('unavailable');
});
it('sends wake-phrase questions, opens guidance, and stops on permission denial',async()=>{
 vi.stubGlobal('SpeechRecognition',Recognition);const send=vi.fn();
 render(<ChartVoice onQuestion={send} latestReply=""/>);
 await userEvent.click(screen.getByRole('button',{name:'Enable voice'}));
 const recognition=Recognition.last;
 act(()=>recognition.onresult?.({resultIndex:0,results:[[{transcript:'Chart Chart show my instructions'}]]}));
 expect(send).toHaveBeenCalledWith('show my instructions');
 act(()=>recognition.onresult?.({resultIndex:0,results:[[{transcript:'Chart Emergency'}]]}));
 expect(screen.getByRole('alert')).toHaveTextContent('No call is placed');
 expect(send).toHaveBeenCalledTimes(1);
 act(()=>recognition.onerror?.({error:'not-allowed'}));
 expect(screen.getByRole('status')).toHaveTextContent('permission was denied');
 expect(recognition.stop).toHaveBeenCalledOnce();
});
it('reads only new replies after explicit speech opt-in',async()=>{
 const speak=vi.fn();vi.stubGlobal('speechSynthesis',{speak,cancel:vi.fn()});
 vi.stubGlobal('SpeechSynthesisUtterance',class {constructor(public text:string){}});
 const {rerender}=render(<ChartVoice onQuestion={vi.fn()} latestReply="Old history"/>);
 expect(speak).not.toHaveBeenCalled();
 await userEvent.click(screen.getByRole('checkbox',{name:'Read new replies aloud'}));
 expect(speak).not.toHaveBeenCalled();
 rerender(<ChartVoice onQuestion={vi.fn()} latestReply="New reply"/>);
 expect(speak).toHaveBeenCalledOnce();
});
