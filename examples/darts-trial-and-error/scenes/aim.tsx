/**
 * 核心演示：三次投掷的落点怎样逐步收敛。
 *
 * 每一次落点都由对应的旁白时间窗触发，GSAP 负责飞入，落点与靶心的连线给出偏差方向。
 * 落点是解释反馈的示意，不是实验数据——角标一直写着「示意」，第三段旁白也明说这一点。
 */
import {useLayoutEffect, useRef} from 'react';
import {gsap, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, useNarration, useReady} from './stage';

//: 相对靶心的落点与说明（单位为画布像素，负值向左/向上）。
const THROWS = [
  {segment: 'darts-demo-0', dx: -96, dy: -132, label: '第 1 次', note: '记录方向，先不解释原因'},
  {segment: 'darts-demo-1', dx: -44, dy: -62, label: '第 2 次', note: '只调整一个动作'},
  {segment: 'darts-demo-2', dx: -16, dy: -22, label: '第 3 次', note: '更接近目标，但一次变好可能是偶然'},
];

const BOARD = {size: 620, x: 230, y: 390};

export default function Aim(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const center = {x: BOARD.x + BOARD.size / 2, y: BOARD.y + BOARD.size / 2};
  const latest = THROWS.reduce((found, item, index) => clock.spoken(item.segment) ? index : found, -1);

  return (
    <Stage props={props} title="看见偏差，再调整方向" lead="每次只改一个动作，再看下一次落点">
      <Panel left={INSET - 40} top={BOARD.y - 60} width={props.width - 2 * (INSET - 40)} height={BOARD.size + 120}>
        <svg width="100%" height="100%" viewBox={`${INSET - 40} ${BOARD.y - 60} ${props.width - 2 * (INSET - 40)} ${BOARD.size + 120}`}>
          <g transform={`translate(${center.x} ${center.y})`}>
            {[310, 248, 186, 124, 62].map((radius, index) => (
              <circle key={radius} cx={0} cy={0} r={radius} fill={index % 2 ? COLOR.card : COLOR.rule} opacity={0.5}/>
            ))}
            <circle cx={0} cy={0} r={22} fill={COLOR.accent}/>
          </g>
          {THROWS.slice(0, latest + 1).map(item => (
            <Throw key={item.segment} center={center} dx={item.dx} dy={item.dy}
              active={clock.spoken(item.segment)}/>
          ))}
        </svg>
      </Panel>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 118, fontSize: SIZE.lead}}>
        {latest >= 0 ? THROWS[latest].label + '：' + THROWS[latest].note : '等待第一次落点'}
      </div>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.body,
        color: COLOR.muted}}>
        图上落点只是解释反馈的示意，不代表真实测量结果
      </div>
    </Stage>
  );
}

function Throw({center, dx, dy, active}: {
  center: {x: number; y: number}; dx: number; dy: number; active: boolean;
}) {
  const mark = useRef<SVGGElement>(null);
  // GSAP 写的是元素自身的 transform，所以外面那层固定位移必须与动画分开，
  // 否则飞入会把「平移到靶心」这一步覆盖掉。用 layout effect 是为了在可见的
  // 第一帧之前就把 from 状态写好，避免落点闪现在靶心。
  useLayoutEffect(() => {
    if (!active || !mark.current) return;
    gsap.fromTo(mark.current, {x: dx * 2.4, y: dy * 2.4 - 320, opacity: 0},
      {x: dx, y: dy, opacity: 1, duration: 0.9, ease: 'power3.out'});
  }, [active, dx, dy]);
  return (
    <g transform={`translate(${center.x} ${center.y})`}>
      <g ref={mark} opacity={active ? 1 : 0}>
        {/* 偏差方向：从靶心指向落点。 */}
        <line x1={0} y1={0} x2={dx} y2={dy} stroke={COLOR.danger} strokeWidth={3} strokeDasharray="10 8"/>
        <circle cx={dx} cy={dy} r={17} fill={COLOR.danger}/>
        <circle cx={dx} cy={dy} r={30} fill="none" stroke={COLOR.danger} strokeWidth={3} opacity={0.5}/>
      </g>
    </g>
  );
}
