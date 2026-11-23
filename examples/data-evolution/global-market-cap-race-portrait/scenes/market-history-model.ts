// Time, value and pass calculations adapted from the approved landscape scene.
import data from './market-cap-history.json';

type Company = {name: string; flag: string};
type Snapshot = {date: string; frame: number; axis: number; ranks: string[]; values: Partial<Record<string, number>>};
type Move = {id: string; start: number; end: number; from: number; to: number};
export type Row = Move & {
  slot: number; opacity: number; value: number;
  /** 仅试制：近距离相邻行的文字基线像素偏移，行容器 top 不变。 */
  labelY?: number;
};
type Pass = {up: string; down: string; center: number};
type TimedPass = Pass & {radius: number};
export const companies: Record<string, Company> = data.companies;
const snapshots: Snapshot[] = data.snapshots;
export const lastSnapshotFrame = snapshots[snapshots.length - 1].frame;
const calendarMonth = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC', year: 'numeric', month: '2-digit',
});
export const clamp = (n: number) => Math.max(0, Math.min(1, n));
export const mix = (a: number, b: number, p: number) => a + (b - a) * p;
const smooth = (p: number) => p * p * (3 - 2 * p);
export const ramp = (x: number, a: number, b: number) => smooth(clamp((x - a) / (b - a)));
const tickerNames: Record<string, string> = {
  DCM: 'DoCoMo',
  AIG: '美国国际',
  NTT: '日本电信',
};

function companyName(id: string, date: string) {
  if (id === 'GOOG' && date < '2015-10') return '谷歌';
  if (id === 'META' && date < '2021-10') return 'Facebook';
  return tickerNames[id] ?? companies[id].name;
}

function capAt(snapshot: Snapshot, id: string, other?: number) {
  // The animation uses the edge of the observed board for gaps below its
  // source coverage. These companies are fully hidden at that endpoint.
  const threshold = snapshot.values[snapshot.ranks[9]]! * 0.96;
  return snapshot.values[id] ?? Math.min(other ?? threshold, threshold);
}

function onClock(progress: number) {
  let low = 0;
  let high = 1;
  for (let step = 0; step < 22; step++) {
    const middle = (low + high) / 2;
    if (smooth(middle) < progress) low = middle;
    else high = middle;
  }
  return (low + high) / 2;
}

function shareCompany(first: Pass, other: Pass) {
  return first.up === other.up || first.up === other.down ||
    first.down === other.up || first.down === other.down;
}

function planPasses(moves: Move[], frames: number): TimedPass[] {
  const minimumRadius = 2 / frames;
  const events: Pass[] = [];
  for (const down of moves) {
    for (const up of moves) {
      if (down.start >= up.start || down.end <= up.end) continue;
      const before = down.from - up.from;
      const after = down.to - up.to;
      const crossing = before / (before - after);
      const center = onClock(Number.isFinite(crossing) ? clamp(crossing) : 0.5);
      events.push({up: up.id, down: down.id,
        center: Math.max(minimumRadius, Math.min(1 - minimumRadius, center))});
    }
  }
  events.sort((a, b) => a.center - b.center);
  return events.map(event => {
    const competitor = events.filter(other => other !== event && shareCompany(event, other));
    const nearest = Math.min(...competitor.map(other => Math.abs(event.center - other.center) / 2));
    // Keep the original value-crossing time where possible and give clustered passes
    // enough frames to show a simultaneous motion on a phone.
    const radius = Math.min(0.31, event.center, 1 - event.center, Math.max(minimumRadius, nearest));
    return {...event, radius};
  });
}

const transitions = snapshots.slice(0, -1).map((from, index) => {
  const to = snapshots[index + 1];
  const ids = [...new Set([...from.ranks, ...to.ranks])];
  const ranksBefore = new Map(from.ranks.map((id, rank) => [id, rank]));
  const ranksAfter = new Map(to.ranks.map((id, rank) => [id, rank]));
  const order = (snapshot: Snapshot, other: Snapshot, visible: Map<string, number>) =>
    ids.filter(id => !visible.has(id)).sort((a, b) =>
      capAt(snapshot, b, other.values[b]) - capAt(snapshot, a, other.values[a]));
  const incoming = order(from, to, ranksBefore);
  const outgoing = order(to, from, ranksAfter);
  const moves: Move[] = ids.map(id => ({
    id,
    start: ranksBefore.get(id) ?? 10 + incoming.indexOf(id),
    end: ranksAfter.get(id) ?? 10 + outgoing.indexOf(id),
    from: capAt(from, id, to.values[id]),
    to: capAt(to, id, from.values[id]),
  }));
  return {from, to, moves, passes: planPasses(moves, to.frame - from.frame),
    fromTime: Date.parse(from.date), toTime: Date.parse(to.date)};
});

function pose(move: Move, progress: number, passes: TimedPass[]): Row {
  let slot = move.start;
  for (const event of passes) {
    if (event.up !== move.id && event.down !== move.id) continue;
    const shift = ramp(progress, event.center - event.radius, event.center + event.radius);
    slot += event.up === move.id ? -shift : shift;
  }
  return {
    ...move, slot,
    opacity: 1 - ramp(slot, 9.88, 10),
    value: mix(move.from, move.to, smooth(progress)),
  };
}

export function marketFrame(frame: number) {
  const nextIndex = snapshots.findIndex(({frame: at}) => frame < at);
  const index = nextIndex < 0 ? transitions.length - 1 : Math.max(0, nextIndex - 1);
  const {from, to, moves, passes, fromTime, toTime} = transitions[index];
  const progress = clamp((frame - from.frame) / (to.frame - from.frame));
  const travel = smooth(progress);
  const snapshotDate = travel < 0.5 ? from.date : to.date;
  const [month, year] = calendarMonth.format(mix(fromTime, toTime, progress)).split('/');
  const axis = mix(from.axis, to.axis, travel);
  const posed = moves.map(move => pose(move, progress, passes));
  const visible = posed.filter(row => row.opacity > 0);
  const ranks = new Map(posed.slice().sort((a, b) => b.value - a.value || a.slot - b.slot)
    .map(({id}, index) => [id, index]));
  const leader = visible.reduce((first, row) => row.slot < first.slot ? row : first).id;
  const source = snapshotDate === '2000-03-31' ? '联合国拉美经委会 / FT Global 500'
    : snapshotDate < '2023-01-01' ? 'CompaniesMarketCap · 历史年度榜单整理' : 'CompaniesMarketCap';
  return {
    date: `${year}-${month}`, year, month, axis, leader, source,
    rows: visible.map(row => ({...row, rank: ranks.get(row.id)!, name: companyName(row.id, snapshotDate)})),
  };
}

// ---------------------------------------------------------------------------
// 试制时间轴：2006-12-31 → 2007-12-31 → 2008-12-31 → 2009-12-31，共 300 帧。
// 仅 timing: "trial" 的场景读取这里；既有全片时间轴与让位绕行保持原样，
// 避免未批准前改动 outputs/video.mp4 的 3214 帧基线。
// ---------------------------------------------------------------------------
export const trialFps = 30;
const trialSegmentFrames = 100;
export const trialFrameCount = trialSegmentFrames * 3;
// 从片头到片尾一直在动：每段的移动窗口 = 整段长度，段与段之间不留静止。
const maxSwapSeconds = trialSegmentFrames / trialFps;
const trialDates = ['2006-12-31', '2007-12-31', '2008-12-31', '2009-12-31'];

type TrialStep = {a: string; b: string; slotA: number; slotB: number};
type TrialTransition = {
  from: Snapshot;
  to: Snapshot;
  moves: Move[];
  steps: TrialStep[];
  stepSeconds: number;
  windowSeconds: number;
  windowFrames: number;
};

/** 与全片相同的前后榜单位置合并，单独实现以免改动现有时间轴。 */
function trialMoves(from: Snapshot, to: Snapshot): Move[] {
  const ids = [...new Set([...from.ranks, ...to.ranks])];
  const ranksBefore = new Map(from.ranks.map((id, rank) => [id, rank]));
  const ranksAfter = new Map(to.ranks.map((id, rank) => [id, rank]));
  const order = (snapshot: Snapshot, other: Snapshot, visible: Map<string, number>) =>
    ids.filter(id => !visible.has(id)).sort((a, b) =>
      capAt(snapshot, b, other.values[b]) - capAt(snapshot, a, other.values[a]));
  const incoming = order(from, to, ranksBefore);
  const outgoing = order(to, from, ranksAfter);
  return ids.map(id => ({
    id,
    start: ranksBefore.get(id) ?? 10 + incoming.indexOf(id),
    end: ranksAfter.get(id) ?? 10 + outgoing.indexOf(id),
    from: capAt(from, id, to.values[id]),
    to: capAt(to, id, from.values[id]),
  }));
}

/** 冒泡排序把起始次序变成目标次序，记录每一次相邻两行互换。 */
function trialSteps(moves: Move[]): TrialStep[] {
  const order = moves.slice().sort((a, b) => a.start - b.start);
  const steps: TrialStep[] = [];
  for (let pass = 0; pass < order.length; pass++) {
    let swapped = false;
    for (let i = 0; i < order.length - 1; i++) {
      if (order[i].end > order[i + 1].end) {
        steps.push({a: order[i].id, b: order[i + 1].id, slotA: i, slotB: i + 1});
        [order[i], order[i + 1]] = [order[i + 1], order[i]];
        swapped = true;
      }
    }
    if (!swapped) break;
  }
  return steps;
}

function trialSnapshot(date: string): Snapshot {
  const snapshot = snapshots.find(item => item.date === date);
  if (!snapshot) throw new Error(`试制快照缺失：${date}`);
  return snapshot;
}

const trialTransitions: TrialTransition[] = trialDates.slice(0, -1).map((date, index) => {
  const from = trialSnapshot(date);
  const to = trialSnapshot(trialDates[index + 1]);
  const moves = trialMoves(from, to);
  const steps = trialSteps(moves);
  const windowSeconds = maxSwapSeconds;
  const stepSeconds = windowSeconds / Math.max(steps.length, 1);
  const windowFrames = Math.round(windowSeconds * trialFps);
  return {from, to, moves, steps, stepSeconds, windowSeconds, windowFrames};
});

function trialClock(frame: number) {
  const at = Math.max(0, Math.min(frame, trialFrameCount - 1));
  const segmentIndex = Math.min(Math.floor(at / trialSegmentFrames), trialTransitions.length - 1);
  const localFrame = at - segmentIndex * trialSegmentFrames;
  return {segmentIndex, localFrame, seconds: localFrame / trialFps,
    swap: trialTransitions[segmentIndex]};
}

/** 所有换位行同时按同一缓动从起始 slot 走到目标 slot；数字与月份用同一进度。 */
function trialSlots(swap: TrialTransition, seconds: number) {
  const slots = new Map<string, number>();
  // 匀速：段内不减速，段与段接续时也不停顿。
  const progress = swap.windowSeconds > 0
    ? clamp(seconds / swap.windowSeconds) : 1;
  for (const move of swap.moves) slots.set(move.id, mix(move.start, move.end, progress));
  return slots;
}

/** 供验收读取全部候选（含未进榜行）的 slot 与起止名次。 */
export function trialCandidates(frame: number) {
  const {seconds, swap} = trialClock(frame);
  const slots = trialSlots(swap, seconds);
  return swap.moves.map(move => ({
    id: move.id, start: move.start, end: move.end, slot: slots.get(move.id)!,
  }));
}

/** 供测试读取每段的转置序列与窗口长度。 */
export function trialWindowInfo() {
  return trialTransitions.map((swap, index) => ({
    index, steps: swap.steps.map(step => ({...step})),
    stepSeconds: swap.stepSeconds, windowFrames: swap.windowFrames,
  }));
}

/** 可见性只看当前 slot：9.85 以下全显，9.85–10 线性淡出，10 以下折叠不可见。 */
function trialRowOpacity(slot: number) {
  if (slot >= 10) return 0;
  if (slot <= 9.85) return 1;
  return 1 - (slot - 9.85) / 0.15;
}


/** 用整数月份序号做插值，避免构造 Date（纯时间管线禁止真实时钟）。 */
function monthTick(from: string, to: string, progress: number) {
  const fromIndex = Number(from.slice(0, 4)) * 12 + (Number(from.slice(5, 7)) - 1);
  const toIndex = Number(to.slice(0, 4)) * 12 + (Number(to.slice(5, 7)) - 1);
  const at = Math.floor(fromIndex + (toIndex - fromIndex) * progress);
  return {year: String(Math.floor(at / 12)), month: String((at % 12) + 1).padStart(2, '0')};
}

export function trialMarketFrame(frame: number) {
  const {seconds, swap} = trialClock(frame);
  const {from, to, moves, windowSeconds} = swap;
  const snapshot = seconds >= windowSeconds ? to : from;
  const progress = clamp(seconds / (trialSegmentFrames / trialFps));
  const axis = mix(from.axis, to.axis, progress);
  const movement = windowSeconds > 0 ? clamp(seconds / windowSeconds) : 1;
  // 年月与柱形、数字用同一个进度：逐个月份跳一次，跟着数字一起走。
  const {year, month} = monthTick(from.date, to.date, movement);
  const slots = trialSlots(swap, seconds);
  const posed: Row[] = moves.map(move => {
    const slot = slots.get(move.id)!;
    return {
      ...move,
      slot,
      opacity: trialRowOpacity(slot),
      value: mix(move.from, move.to, movement),
    };
  });
  // 每帧把全部候选按当前 slot 升序排，前 10 即榜单行；编号就按这个顺序发 0–9。
  const board = posed
    .sort((a, b) => a.slot - b.slot || b.value - a.value || a.id.localeCompare(b.id))
    .slice(0, 10);
  const ranks = new Map(board.map(({id}, index) => [id, index]));
  const leader = board[0]?.id ?? posed[0].id;
  const source = snapshot.date < '2023-01-01'
    ? 'CompaniesMarketCap · 历史年度榜单整理' : 'CompaniesMarketCap';
  return {
    date: snapshot.date, year, month, axis, leader, source,
    rows: board.map(row => ({...row, rank: ranks.get(row.id)!, name: companyName(row.id, snapshot.date)})),
  };
}

/**
 * 全片版：与试制同样的连续运动规则——每段之内所有换位行同时匀速直线移动，
 * 段与段首尾相接不停顿；年月按同一进度逐月跳；交叉时按位置压栈并在版面上处理。
 */
export function filmMarketFrame(frame: number, order: 'slots' | 'value' = 'slots') {
  const at = Math.max(0, frame);
  const next = transitions.findIndex(item => at < item.to.frame);
  const index = next < 0 ? transitions.length - 1 : Math.max(0, next);
  const {from, to, moves} = transitions[index];
  // 首段从第 0 帧起、末段一直走到片尾，保证全片首尾衔接、没有静止段。
  const start = index === 0 ? 0 : from.frame;
  const end = index === transitions.length - 1 ? 3213 : to.frame;
  const span = Math.max(1, end - start);
  const progress = clamp((at - start) / span);
  const snapshot = progress < 0.5 ? from : to;
  const axis = mix(from.axis, to.axis, progress);
  const {year, month} = monthTick(from.date, to.date, progress);
  const posed: Row[] = moves.map(move => {
    const slot = mix(move.start, move.end, progress);
    return {...move, slot, opacity: trialRowOpacity(slot), value: mix(move.from, move.to, progress)};
  });
  const board = posed
    .sort((a, b) => (order === 'value' ? b.value - a.value : a.slot - b.slot)
      || b.value - a.value || a.slot - b.slot || a.id.localeCompare(b.id))
    .slice(0, 10);
  const ranks = new Map(board.map(({id}, rank) => [id, rank]));
  const leader = board[0]?.id ?? posed[0].id;
  const source = snapshot.date === '2000-03-31' ? '联合国拉美经委会 / FT Global 500'
    : snapshot.date < '2023-01-01' ? 'CompaniesMarketCap · 历史年度榜单整理' : 'CompaniesMarketCap';
  return {
    date: snapshot.date, year, month, axis, leader, source,
    rows: board.map(row => ({...row, rank: ranks.get(row.id)!, name: companyName(row.id, snapshot.date)})),
  };
}
