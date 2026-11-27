import {filmMarketFrame} from './market-history-model';

export const stageFrames = 3214;
const stage = Array.from({length: stageFrames}, (_, frame) => filmMarketFrame(frame, 'value'));
export type StageRow = (typeof stage)[number]['rows'][number];

type LeadChange = {frame: number; from: string; to: string};
const changes: LeadChange[] = stage.flatMap((item, frame) => {
  const previous = stage[frame - 1];
  return previous && previous.leader !== item.leader
    ? [{frame, from: previous.leader, to: item.leader}] : [];
});

const groups: LeadChange[][] = [];
for (const change of changes) {
  const lastGroup = groups.at(-1);
  if (lastGroup && change.frame - lastGroup.at(-1)!.frame <= 16) lastGroup.push(change);
  else groups.push([change]);
}

export const handoffs = groups.map((group, index) => {
  const first = group[0], last = group.at(-1)!;
  const previous = groups[index - 1]?.at(-1);
  const next = groups[index + 1]?.[0];
  const leftLimit = previous ? Math.ceil((previous.frame + first.frame) / 2) : 0;
  const rightLimit = next ? Math.ceil((last.frame + next.frame) / 2) : stageFrames;
  const start = Math.max(leftLimit, first.frame - 28);
  const end = Math.min(rightLimit, last.frame + 29);
  const entrants = [...new Set([first.from, ...group.map(change => change.to)])];
  // 只有双方全程留在前二，第二行才是可安全使用的升降路径。
  const rowPath = entrants.length === 2 && stage.slice(start, end)
    .every(item => item.rows.slice(0, 2).every(row => entrants.includes(row.id)));
  return {
    start, end, rowPath, entrants,
    first: first.frame,
    last: last.frame,
    from: first.from,
    to: last.to,
  };
});
export type Handoff = (typeof handoffs)[number];

// 位次、选择比较对象和时点使用同一份逐帧排名。纯时间采集时可直接定位。
export function stageMarketFrame(frame: number) {
  const index = Math.min(stageFrames - 1, Math.max(0, Math.round(frame)));
  return {...stage[index], index, handoff: handoffs.find(({start, end}) => start <= index && index < end)};
}
