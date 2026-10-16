/**
 * 开场：十个方案铺在桌上，注意力却在它们之间来回跳。
 *
 * 每个方案卡片按旁白进度依次出现，卡片之间的连线表示「又被比较了一次」。
 * 选项数量没变，被消耗的是注意力——这正是「还没有决定用什么标准选」的代价。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
const GRID = {left: 180, top: 300, cell: 190, gap: 26, rows: 2};

export default function Opening(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const progress = clock.progress('choice-point-0');
  const cards = OPTIONS.map((label, index) => {
    const row = Math.floor(index / 5);
    const column = index % 5;
    return {label, x: GRID.left + column * (GRID.cell + GRID.gap), y: GRID.top + row * (GRID.cell + GRID.gap)};
  });
  // 注意力在方案之间跳：跳动的速度随旁白推进加快，表示反复比较的消耗。
  const focus = cards[Math.floor(clock.elapsedSeconds * 2.4) % cards.length];
  const switched = Math.floor(mix(0, 26, progress));

  return (
    <Stage props={props} title="选项越多，注意力越容易被切碎"
      note="十个方案都还没比较完，标准也还没定下来">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        {cards.slice(1).map((card, index) => (
          <line key={card.label} x1={cards[index].x + GRID.cell / 2} y1={cards[index].y + GRID.cell / 2}
            x2={card.x + GRID.cell / 2} y2={card.y + GRID.cell / 2}
            stroke={COLOR.rule} strokeWidth={2} strokeDasharray="8 8"
            opacity={index < switched ? 0.8 : 0}/>
        ))}
      </svg>
      {cards.map((card, index) => (
        <div key={card.label} style={{position: 'absolute', left: card.x, top: card.y, width: GRID.cell,
          height: GRID.cell, borderRadius: 14, background: COLOR.panel,
          border: `3px solid ${focus.label === card.label ? COLOR.accent : COLOR.rule}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 54, fontWeight: 300, color: focus.label === card.label ? COLOR.accent : COLOR.ink,
          opacity: mix(0.15, 1, progress * 12 - index)}}>{card.label}</div>
      ))}
      <div style={{position: 'absolute', right: 180, top: 300, width: 380, fontSize: SIZE.body,
        lineHeight: 1.7, color: COLOR.muted}}>
        <div style={{fontSize: SIZE.lead, color: COLOR.ink, marginBottom: 18}}>被消耗的不是选项</div>
        每次重新比较，都要把已经看过的信息再取回来一次。标准越晚确定，重复的次数越多。
      </div>
      <div style={{position: 'absolute', left: 180, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        问题不一定是选项太多，而是还没决定用什么标准选
      </div>
    </Stage>
  );
}
