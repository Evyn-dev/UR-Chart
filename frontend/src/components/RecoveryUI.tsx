import {lazy,Suspense} from 'react';
import type {ReactNode} from 'react';
import {ShieldAlert} from 'lucide-react';
import {Loader} from '../components/UI';
import type {Checkin} from '../types/api';

export function Grid({children}:{children:ReactNode}){return <div className="card-grid">{children}</div>}
export function Notice({children}:{children:ReactNode}){return <div className="notice"><ShieldAlert size={17}/><span>{children}</span></div>}
const LazyTrendChart=lazy(()=>import('../components/TrendChart'));
export function TrendChart({records}:{records:Checkin[]}){return <Suspense fallback={<Loader/>}><LazyTrendChart records={records}/></Suspense>}
