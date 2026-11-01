/** 金融作品的可选设计档案：题材色场、标题模式与运动人格。 */

export type FinancialProfile = 'ledger' | 'signal' | 'archive';
export type FinancialTitleMode = 'subject' | 'premise';
export type FinancialPersonality = 'premium' | 'corporate' | 'calm';

export type FinancialDesign = {
  profile?: FinancialProfile;
  accent?: string;
  titleMode?: FinancialTitleMode;
  personality?: FinancialPersonality;
};

export type ResolvedFinancialDesign = {
  profile: FinancialProfile;
  titleMode: FinancialTitleMode;
  personality: FinancialPersonality;
  accent: string | null;
  glow: string;
  tint: string;
};

const PROFILES: Record<FinancialProfile, {glow: string; tint: string}> = {
  signal: {glow: '#17171B', tint: '#A8B0BD'},
  ledger: {glow: '#1A1713', tint: '#C9A45C'},
  archive: {glow: '#10161D', tint: '#6F8CA8'},
};

const TITLE_MODES: FinancialTitleMode[] = ['subject', 'premise'];
const PERSONALITIES: FinancialPersonality[] = ['premium', 'corporate', 'calm'];
const ACCENT = /^#[0-9A-Fa-f]{6}$/;
const PROFIT = '#ff5a4e';
const LOSS = '#4bd39a';

/** 开场编排的帧数；人格只改变入场节奏，不改变数据时间。 */
export const OPENING_DURATIONS: Record<FinancialPersonality, {
  subject: number; premise: number; chart: number; value: number;
}> = {
  premium: {subject: 14, premise: 14, chart: 16, value: 12},
  corporate: {subject: 12, premise: 12, chart: 12, value: 10},
  calm: {subject: 18, premise: 18, chart: 20, value: 14},
};

/** 把 #RRGGBB 转成 rgba，用于极低透明度背景色场。 */
export function withAlpha(hex: string, alpha: number): string {
  if (!ACCENT.test(hex)) throw new RangeError(`accent 必须是 #RRGGBB：${hex}`);
  const value = hex.slice(1);
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

export function resolveDesign(design: FinancialDesign | undefined): ResolvedFinancialDesign {
  const profile = design?.profile ?? 'signal';
  if (!(profile in PROFILES)) throw new RangeError(`未知金融设计 profile：${profile}`);
  const titleMode = design?.titleMode ?? 'subject';
  if (!TITLE_MODES.includes(titleMode)) throw new RangeError(`未知金融标题模式：${titleMode}`);
  const personality = design?.personality ?? 'corporate';
  if (!PERSONALITIES.includes(personality)) throw new RangeError(`未知金融运动人格：${personality}`);
  const accent = design?.accent ?? null;
  if (accent !== null) {
    if (!ACCENT.test(accent)) throw new RangeError(`accent 必须是 #RRGGBB：${accent}`);
    if ([PROFIT, LOSS].includes(accent.toLowerCase())) {
      throw new RangeError('accent 不能与正收益或负收益颜色相同');
    }
  }
  return {profile, titleMode, personality, accent,
    glow: PROFILES[profile].glow, tint: accent ?? PROFILES[profile].tint};
}
