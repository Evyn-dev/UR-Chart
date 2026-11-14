const beat='h60 q20 -22 40 0 h40 l10 12 l14 -120 l14 152 l10 -44 h70 q30 -34 60 0 h82';
const ecg=`M0 150 ${beat} ${beat} ${beat}`;
const pleth='M0 50 q50 -70 100 0'+' t100 0'.repeat(11);

/** Scrolling monitor grid, scanlines and vignette. Decorative only. */
export function MonitorBackdrop(){
  return <div className="monitor-bg" aria-hidden="true"><div className="monitor-grid"/><div className="monitor-scan"/></div>;
}

/** Animated ECG sweep (and optional pleth wave). Decorative only: sample waveform, not patient data. */
export function EcgTrace({pleth:showPleth=true}:{pleth?:boolean}){
  return <div className="ecg" aria-hidden="true">
    <svg className="ecg-main" viewBox="0 0 1200 300" preserveAspectRatio="xMidYMid slice" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path className="ecg-ghost" d={ecg} pathLength={1000}/>
      <path className="ecg-sweep" d={ecg} pathLength={1000}/>
    </svg>
    {showPleth&&<svg className="ecg-pleth" viewBox="0 0 1200 100" preserveAspectRatio="xMidYMid slice" fill="none" strokeLinecap="round">
      <path className="ecg-ghost" d={pleth} pathLength={1000}/>
      <path className="ecg-sweep2" d={pleth} pathLength={1000}/>
    </svg>}
  </div>;
}
