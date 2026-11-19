const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;

export const principal = 10_000;
export const rate = 0.10;
export const half = 20;
export const yearly = Array.from({length: half * 2}, (_, index) => principal * rate * (1 + rate) ** index);
export const halfTotals = [0, half].map(start => yearly.slice(start, start + half).reduce((sum, value) => sum + value, 0));
export const ratio = halfTotals[1] / halfTotals[0];
export const share = halfTotals[0] / (halfTotals[0] + halfTotals[1]);
export const contribution = yearly[0] * rate;

export const beats = {
  reinvest: [0.5, 1.65],
  reveal: [1.72, 2.52],
  chart: 4.65,
  yearStep: 0.095,
  assemble: 9.70,
  duration: 15.2,
} as const;

export type Layout = 'offset' | 'center';
export type Glass = 'ink' | 'amber' | 'honey' | 'glint' | 'etched';
export type Block = {
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
  z?: number;
  pitch?: number;
  yaw?: number;
  glass: Glass;
};

export const baseY = 814;
export const macroOffsetX = -159;
export const macroGlance = .37;
export const chartX = (index: number) => 179 + index * 40;
export const chartScale = 493 / yearly[yearly.length - 1];
export const towerScale = 573 / halfTotals[1];
export const towerCenters = (layout: Layout) => layout === 'offset' ? [1033, 1447] : [743, 1227];

export const fade = (start: number, end: number, seconds: number) => {
  const progress = clamp01((seconds - start) / (end - start));
  return progress * progress * (3 - 2 * progress);
};

const lowerAmounts = yearly.map((_, index) => {
  const start = index < half ? 0 : half;
  return yearly.slice(start, index).reduce((sum, value) => sum + value, 0);
});

export function annualState(seconds: number, layout: Layout, sequenceGroups = false) {
  const pullback = fade(beats.assemble, beats.assemble + 2.65, seconds);
  const release = fade(beats.assemble + .28, beats.assemble + .85, seconds);
  const gather = [0, 1].map(group => fade(beats.assemble + (sequenceGroups ? [.73, 1.18][group] : .96),
    beats.assemble + (sequenceGroups ? [1.91, 2.41][group] : 2.41), seconds));
  const stack = fade(beats.assemble + 1.24, beats.assemble + 2.41, seconds);
  const widen = fade(beats.assemble + 1.40, beats.assemble + 2.41, seconds);
  // Shrink the shared mapping with the added stack height so the tail stays in the frame.
  const scale = chartScale / (1 + (chartScale / towerScale - 1) * stack);
  const baseline = lerp(baseY, 833, pullback);
  const centers = towerCenters(layout);
  const shifts = [-58, 32].map((shift, group) => shift * release * (1 - gather[group]));
  const groupCenters = centers.map((center, group) =>
    lerp(chartX(group * half + (half - 1) / 2), center, gather[group]) + shifts[group]
  );

  const blocks: Block[] = yearly.map((amount, index) => {
    const group = index < half ? 0 : 1;
    const sequence = index % half;
    const etched = sequence % 5 === 4;
    const appearingAt = beats.chart + index * beats.yearStep;
    const growth = fade(appearingAt, appearingAt + 0.31, seconds);
    const height = amount * scale * growth;
    const turn = sequenceGroups ? Math.sin(Math.PI * gather[group]) : 0;
    const topPiece = sequenceGroups && index === yearly.length - 1
      ? 54 * fade(beats.assemble + 1.18, beats.assemble + 1.68, seconds)
        * (1 - fade(beats.assemble + 2.30, beats.assemble + 2.65, seconds)) : 0;

    return {
      x: lerp(chartX(index), centers[group], gather[group]) + shifts[group],
      y: baseline - (lowerAmounts[index] * scale * stack + height / 2) - topPiece,
      width: lerp(27 - 6 * release * (1 - gather[group]), etched ? 188 : 176, widen),
      height,
      depth: lerp(18, etched ? 78 : 68, widen) + 14 * release * (1 - gather[group]),
      ...(sequenceGroups ? {yaw: (group === 0 ? -.24 : .24) * turn, z: -(sequence / half) * 30 * turn} : {}),
      glass: etched ? 'etched' : group === 0 ? 'honey' : 'amber',
    };
  });

  return {blocks, baseline, scale, pullback, groupCenters};
}

export function annualBarDuration(index: number) {
  if (index === yearly.length - 1) return .57;
  if (index < 3 || index === half) return .38;
  return .25;
}

export function growAnnualBars(plot: ReturnType<typeof annualState>, starts: readonly number[], seconds: number) {
  const progress = plot.blocks.map((_, index) => {
    const start = starts[index];
    return fade(start, start + annualBarDuration(index), seconds);
  });
  const blocks = plot.blocks.map((block, index) => {
    const height = block.height * progress[index];
    return {...block, height, y: plot.baseline - height / 2};
  });
  return {blocks, progress};
}

export function macroState(seconds: number, secondGain?: number) {
  const reinvest = fade(...beats.reinvest, seconds);
  const reveal = fade(...beats.reveal, seconds);
  const x = 1246 + macroOffsetX;
  const width = 504;
  const depth = 192;
  const modelScale = 0.021;
  const bottom = 790;
  const principalHeight = principal * modelScale;
  const interestHeight = yearly[0] * modelScale;
  const extraWidth = width * .40;
  const extraDepth = depth * .44;
  const extraHeight = contribution * modelScale * width * depth / (extraWidth * extraDepth);

  const baseCount = 10;
  const baseLayerHeight = principalHeight / baseCount;
  const capital: Block[] = Array.from({length: baseCount}, (_, layer) => ({
    x, y: bottom - baseLayerHeight * (layer + .5), width, height: baseLayerHeight, depth, glass: 'ink',
  }));
  const first: Block = {
    x, y: bottom - principalHeight - interestHeight / 2 - lerp(191, 0, reinvest),
    width, height: interestHeight, depth, pitch: .28 * (1 - reinvest), glass: 'honey',
  };
  const secondProgress = secondGain ?? reveal;
  const second: Block = {
    x, y: bottom - principalHeight - interestHeight - interestHeight * secondProgress / 2,
    width, height: interestHeight * secondProgress, depth, glass: 'honey',
  };
  const extra: Block = {
    x: x + reveal * 8,
    y: bottom - principalHeight - interestHeight - (secondGain === undefined ? interestHeight * reveal : 0)
      - extraHeight * reveal / 2 - 108 * reveal,
    z: secondGain === undefined ? undefined : 64 * reveal,
    width: extraWidth, height: extraHeight * reveal, depth: extraDepth,
    pitch: .23 * reveal, glass: 'glint',
  };
  return {blocks: [...capital, first, second, extra], first, second, extra, reveal};
}
