import {useEffect, useRef, type CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {mix, ramp, trialMarketFrame} from './market-history-model';
import {stageMarketFrame, type StageRow} from './market-history-stage';
import {paintStageBackdrop} from './market-history-stage-backdrop';
import './market-history-stage.css';

type TextPose = [x: number, y: number, size: number, weight: number, right: number];
type Pose = [rank: TextPose, name: TextPose, amount: TextPose];

const lineHeight = 29.4;
const cardNameTop = 185;
const hero: Pose = [[29, 127, 12, 560, 0], [29, 153, 48, 740, 0], [29, 207, 82, 630, 0]];
const fields = ['rank', 'name', 'cap'] as const;

function tablePose(row: StageRow): Pose {
  const offset = (row.rank - 1) * lineHeight;
  return [[29, 369 + offset, 10, 570, 0], [61, 365 + offset, 13.8, 475, 0], [363, 364 + offset, 15, 525, 1]];
}

function cardPose(row: StageRow, index: number, count: number): Pose {
  const width = (334 - (count - 1) * 11) / count;
  const x = 29 + index * (width + 11) + (count === 2 ? 14 : 10);
  const nameWidth = Array.from(row.name).reduce((total, c) => total + (c.charCodeAt(0) > 255 ? 1 : .64), 0);
  const nameSize = Math.min(count === 2 ? 30 : 24, (width - 23) / nameWidth);
  return [[x, 161, 11, 600, 0], [x, cardNameTop, nameSize, 720, 0], [x, 228, count === 2 ? 44 : 34, 650, 0]];
}

function blend(from: Pose, to: Pose, progress: number): Pose {
  return from.map((part, index) => part.map((value, field) => mix(value, to[index][field], progress))) as Pose;
}

function incoming(row: StageRow, card: Pose, progress: number): Pose {
  const table = tablePose(row);
  const shifted: Pose = [
    [card[0][0] - 8, ...table[0].slice(1)] as TextPose,
    [card[1][0] + 26, ...table[1].slice(1)] as TextPose,
    table[2],
  ];
  if (progress < .34) return blend(table, shifted, ramp(progress, 0, .34));
  const rise = ramp(progress, .34, 1);
  const pose = blend(shifted, card, rise);
  const separation = 4 * rise * (1 - rise);
  pose[0][1] -= 10 * separation;
  pose[2][1] += 22 * separation;
  return pose;
}

function StagePerson({row, pose, travelling}: {row: StageRow; pose: Pose; travelling: boolean}) {
  const rank = String(row.rank + 1).padStart(2, '0');
  const text = [row.rank === 0 && pose[2][2] >= 74 ? '01　全球第一' : rank, row.name, row.value.toFixed(3)];
  return <div className="stage-person" data-company={row.id} data-rank={row.rank + 1} data-lead={row.rank === 0} data-travelling={travelling}>
    {pose.map(([left, top, fontSize, fontWeight, right], index) => <span key={fields[index]}
      className={'person-' + fields[index]} data-copy={fields[index]}
      style={{left, top, fontSize, fontWeight, transform: 'translateX(' + (-right * 100) + '%)'}}>{text[index]}</span>)}
  </div>;
}

export default function MarketHistoryPortrait({width, height, props}: CodeSceneProps) {
  const {ready, globalFrame} = useSceneContext();
  const backdrop = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (backdrop.current) paintStageBackdrop(backdrop.current);
  }, [width, height]);
  useEffect(() => { ready(); }, [ready]);

  const sampleFrames = props.sampleFrames as number[] | undefined;
  const frame = sampleFrames?.[Math.floor(globalFrame)] ?? globalFrame;
  const resolved = stageMarketFrame(frame);
  // 独立试制参数仅用来重放登记过的试制时间轴；正式榜单以当前金额发名次。
  const data = props.timing === 'trial' ? {...resolved, ...trialMarketFrame(frame), handoff: undefined} : resolved;
  const {index, rows, year, month, handoff} = data;
  const active = new Map<string, Pose>();
  let duel = 0;
  let heroLight = 1;
  let cards: StageRow[] = [];

  if (!handoff) {
    active.set(rows[0].id, hero);
  } else {
    const {first, last, start, end, entrants, from, to, rowPath} = handoff;
    const openEnd = first - Math.min(6, (first - start) * .25);
    const closeStart = last + Math.min(5, (end - last) * .24);
    const opening = ramp(index, start, openEnd);
    const closeSplit = closeStart + (end - closeStart) * .52;
    const leave = ramp(index, closeStart, closeSplit);
    const arrive = ramp(index, closeSplit, end);
    duel = ramp(index, start + (openEnd - start) * .38, openEnd) * (1 - leave);
    heroLight = Math.max(1 - opening, arrive);
    cards = entrants.flatMap(id => rows.find(row => row.id === id) ?? []);
    for (const [column, row] of cards.entries()) {
      const card = cardPose(row, column, cards.length);
      if (index < openEnd) {
        if (row.id === from) active.set(row.id, blend(hero, card, ramp(opening, 0, .61)));
        else if (rowPath) active.set(row.id, incoming(row, card, opening));
        else if (opening >= .60) active.set(row.id, card);
      } else if (index < closeStart) {
        active.set(row.id, card);
      } else if (row.id === to) {
        active.set(row.id, blend(card, hero, arrive));
      } else if (rowPath) {
        active.set(row.id, blend(card, tablePose(row), leave));
      } else if (leave < .6) {
        active.set(row.id, card);
      }
    }
  }

  const board = rows.filter(row => !active.has(row.id));
  const rimTransform = 'rotate(' + (-28 + 5 * duel) + 'deg) translateX(' + (7 * duel) + 'px)';
  const columns = {gridTemplateColumns: 'repeat(' + cards.length + ', minmax(0, 1fr))', opacity: duel} satisfies CSSProperties;

  return <main style={{position: 'relative', width, height, overflow: 'hidden', background: '#090c13'}} data-source-frame={index}>
    <canvas ref={backdrop} width={width} height={height} aria-hidden="true" style={{position: 'absolute', inset: 0}} />
    <div className="release-stage" style={{transform: 'scale(' + width / 420 + ')'}}>
      <div className="rim-space" aria-hidden="true">
        <div className="rim-wrap" style={{transform: rimTransform, opacity: .86 * (1 - .52 * duel)}}>
          <div className="rim" /><div className="inner-track" />
        </div>
      </div>
      <header><h1>全球市值前十</h1><time>{year}.{month}</time></header>
      <p className="stage-metric">市值 · 万亿美元</p>
      {cards.length > 0 && <div className="stage-cards" aria-hidden="true" style={columns}>
        {cards.map(row => {
          const pose = active.get(row.id);
          const opacity = pose ? 1 - ramp(Math.abs(pose[1][1] - cardNameTop), 10, 62) : 0;
          return <div className="stage-card" key={row.id} data-lead={row.rank === 0} style={{opacity}} />;
        })}
      </div>}
      <p className="hero-unit" style={{opacity: heroLight}}>万亿美元</p>
      <section className="stage-board" aria-label="其余榜单">
        {board.map(row => <div className="stage-row" key={row.id} data-company={row.id} data-rank={row.rank + 1}
          style={{top: (row.rank - 1) * lineHeight}}>
          <span className="row-rank" data-copy="rank">{String(row.rank + 1).padStart(2, '0')}</span>
          <span className="row-name" data-copy="name">{row.name}</span>
          <span className="row-cap" data-copy="cap">{row.value.toFixed(3)}</span>
        </div>)}
      </section>
      {rows.map(row => {
        const pose = active.get(row.id);
        return pose && <StagePerson key={row.id} row={row} pose={pose} travelling={Boolean(handoff?.rowPath && pose[1][1] > cardNameTop)} />;
      })}
    </div>
  </main>;
}
