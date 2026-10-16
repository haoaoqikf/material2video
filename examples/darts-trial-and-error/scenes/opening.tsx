/**
 * 开场：一张靶面，一支还没出手的箭。
 *
 * 「继续推演」那一侧始终只有靶心，没有落点——推演能排除明显错误，却不会产生关于
 * 自己偏差的信息。落点要等第一支箭真的飞出去才有。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const BOARD = {size: 660, x: 210, y: 420};

export default function Opening(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const approached = mix(0, 1, clock.progress('darts-point-0'));
  const center = {x: BOARD.x + BOARD.size / 2, y: BOARD.y + BOARD.size / 2};
  const dart = {x: center.x + 300 - approached * 150, y: center.y - 380 + approached * 140};

  return (
    <Stage props={props} title="把可承受的行动变成信息" lead="准备能减少明显错误，反馈才给出偏差">
      <Panel left={INSET - 40} top={BOARD.y - 60} width={props.width - 2 * (INSET - 40)} height={BOARD.size + 120}>
        <svg width="100%" height="100%" viewBox={`${INSET - 40} ${BOARD.y - 60} ${props.width - 2 * (INSET - 40)} ${BOARD.size + 120}`}>
          <g transform={`translate(${center.x} ${center.y})`}>
            {[330, 264, 198, 132, 66].map((radius, index) => (
              <circle key={radius} cx={0} cy={0} r={radius} fill={index % 2 ? COLOR.card : COLOR.rule} opacity={0.55}/>
            ))}
            <circle cx={0} cy={0} r={26} fill={COLOR.accent}/>
            <line x1={-330} x2={330} y1={0} y2={0} stroke={COLOR.muted} strokeWidth={2} opacity={0.35}/>
            <line x1={0} x2={0} y1={-330} y2={330} stroke={COLOR.muted} strokeWidth={2} opacity={0.35}/>
          </g>
          {/* 悬停的箭：只有在真的出手之后，它才会变成一条可以读的偏差。 */}
          <g transform={`translate(${dart.x} ${dart.y}) rotate(38)`} opacity={0.9}>
            <rect x={-6} y={0} width={12} height={150} rx={6} fill={COLOR.ink}/>
            <path d="M0,0 L-16,34 L0,26 L16,34 Z" fill={COLOR.accent}/>
            <path d="M-6,150 L0,178 L6,150 Z" fill={COLOR.danger}/>
          </g>
        </svg>
      </Panel>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 118, fontSize: SIZE.lead}}>
        还没有落点，就没有可读的偏差
      </div>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.body,
        color: COLOR.muted}}>
        小步尝试是获得信息的一种办法，不是把准备全部丢掉
      </div>
    </Stage>
  );
}
