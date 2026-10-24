import {smooth01} from './lifeMath';

const PAPER = '#FFF9EE';
const WARM = '#F4EDDF';
const INK = '#26272D';
const MID = '#C9C1B4';
const ACCENT = '#E66A3B';

function figure(x: number, foot: number, scale = 1) {
  return <g transform={`translate(${x} ${foot - 101 * scale}) scale(${scale})`} fill={INK} stroke={INK}
    strokeWidth={12} strokeLinecap="round" strokeLinejoin="round">
    <circle cy="0" r="18" stroke="none"/>
    <path d="M-3 22Q-9 20-14 30L-21 57Q-24 66-15 70L0 74L16 67L14 34Q12 24 4 23Z" stroke="none"/>
    <path d="M-1 59L-20 96M1 59L22 92M-3 29L-23 48M2 30L27 17" fill="none"/>
    <path d="M-27 101h22M13 97h22" fill="none" strokeWidth="10"/>
  </g>;
}

export default function LearningWindow({time}: {time: number}) {
  const t = Math.max(0, Math.min(4, time));
  const page = smooth01((t - 0.42) / 0.88);
  const stairReveal = smooth01((t - 0.7) / 0.86);
  const climb = Math.max(0, Math.min(5, ((t - 1.8) / 1.0) * 5));
  const step = Math.min(4, Math.floor(climb));
  const stepPhase = climb >= 5 ? 1 : climb - step;
  const stairX = [700, 880, 1040, 1200, 1360, 1520];
  const stairFoot = [850, 810, 770, 730, 690, 650];
  const stepEase = smooth01(stepPhase);
  const x = t < 1.42 ? 430 + 120 * smooth01(t / 0.55)
    : t < 1.8 ? 550 + 150 * smooth01((t - 1.42) / 0.38)
      : climb >= 5 ? stairX[5] : stairX[step] + (stairX[step + 1] - stairX[step]) * stepEase;
  const foot = t < 1.8 ? 850
    : climb >= 5 ? stairFoot[5] : stairFoot[step] + (stairFoot[step + 1] - stairFoot[step]) * stepEase;
  const stairs = 'M600 850H800V810H960V770H1120V730H1280V690H1440V650H1600V850H600Z';

  return <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: WARM}}>
    <svg viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid meet" aria-hidden="true"
      style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <clipPath id="learning-stair-reveal"><rect x="600" y="620" width={1000 * stairReveal} height="340"/></clipPath>
      </defs>
      <path d="M0 850Q500 830 960 850T1920 842V1080H0Z" fill="#EAE1D3"/>
      <path d="M0 850Q500 830 960 850T1920 842" fill="none" stroke="#D8CEBE" strokeWidth="5"/>
      <ellipse cx="980" cy="862" rx="620" ry="34" fill="#342D27" opacity=".08"/>

      {/* A simple raised block makes the obstacle visible before the page opens. */}
      <g opacity={1 - smooth01((t - 0.25) / 0.35)}>
        <path d="M1018 725H1168V850H1018Z" fill="#D8CEBF" stroke="#B9AD9B" strokeWidth="7"/>
        <path d="M1168 725L1202 704V829L1168 850Z" fill="#C8BDAE" stroke="#AFA392" strokeWidth="7"/>
        <path d="M1018 725L1052 704H1202L1168 725Z" fill="#FFF9EE" stroke="#B9AD9B" strokeWidth="7"/>
      </g>

      {/* The cover stays grounded while its right page opens from the spine. */}
      <path d="M100 786Q180 750 250 787V850Q180 819 100 854Z" fill="#D8CEBF" stroke="#B8AC9A" strokeWidth="7"/>
      <path d="M250 787Q335 750 470 770V832Q360 811 250 850Z" fill="#D8CEBF" stroke="#B8AC9A" strokeWidth="7"
        transform={`translate(250 0) scale(${Math.max(.02, page)} 1) translate(-250 0)`}/>
      <path d="M112 773Q180 741 250 776V828Q180 798 112 831Z" fill={PAPER} stroke="#CFC4B4" strokeWidth="6"/>
      <path d="M250 776Q335 742 460 758V812Q360 796 250 828Z" fill="#F7EFE2" stroke="#CFC4B4" strokeWidth="6"
        transform={`translate(250 0) scale(${Math.max(.02, page)} 1) translate(-250 0)`}/>
      <path d="M250 778V828" stroke={ACCENT} strokeWidth="9"/>

      <g clipPath="url(#learning-stair-reveal)">
        <path d={stairs} fill="#E7DDCE" stroke="#B8AC9A" strokeWidth="7" strokeLinejoin="round"/>
      </g>
      {t >= 1.8 && <g aria-hidden="true">
        <path d={`M${x - 48} ${foot}H${x + 48}`} stroke="#E7DDCE" strokeWidth="13"/>
        <ellipse cx={x} cy={foot + 8} rx="42" ry="8" fill="#342D27" opacity=".12"/>
      </g>}
      {figure(x, foot, 1.05)}
    </svg>
  </div>;
}
