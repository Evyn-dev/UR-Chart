import {ResponsiveContainer,CartesianGrid,XAxis,YAxis,Tooltip,LineChart,Line} from 'recharts';
import type {Checkin} from '../types/api';
import {dayLabel} from '../services/dates';
import {Empty} from './UI';

export default function TrendChart({records}:{records:Checkin[]}){const rows=records.filter(r=>r.pain_level!==null&&r.pain_level!==undefined).slice().sort((a,b)=>a.day.localeCompare(b.day)).map(r=>({day:dayLabel(r.day),pain:r.pain_level}));return rows.length?<div className="chart-wrap" role="img" aria-label="Line chart of recorded pain levels by day"><ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{top:15,right:20,left:-22,bottom:0}}><CartesianGrid stroke="#e8edf5" strokeDasharray="4 5"/><XAxis dataKey="day" fontSize={11}/><YAxis domain={[0,10]} fontSize={11}/><Tooltip/><Line type="monotone" dataKey="pain" stroke="#6552b9" strokeWidth={3} dot={{r:4}} connectNulls={false}/></LineChart></ResponsiveContainer></div>:<Empty message="Your progress starts here" detail="Complete check-ins to see your recorded pain levels over time."/>}
