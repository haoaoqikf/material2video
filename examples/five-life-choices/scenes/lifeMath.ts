export const DURATION = 30;

export const ACTS = [
  {id: 'opening', start: 0, end: 3},
  {id: 'city', start: 3, end: 8},
  {id: 'industry', start: 8, end: 13},
  {id: 'partner', start: 13, end: 18},
  {id: 'investment', start: 18, end: 23},
  {id: 'learning', start: 23, end: 27},
  {id: 'finale', start: 27, end: 30},
] as const;

export type ActId = (typeof ACTS)[number]['id'];

export function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function smooth01(value: number): number {
  const x = clamp01(value);
  return x * x * (3 - 2 * x);
}

export function actAt(t: number): ActId {
  const time = Math.max(0, Math.min(DURATION, t));
  return ACTS.find((act) => time >= act.start && time < act.end)?.id ?? 'finale';
}
