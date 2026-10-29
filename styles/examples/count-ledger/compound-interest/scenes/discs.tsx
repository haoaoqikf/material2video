/** 复利作品的表现层入口：从风格包复用圆片、文字与通用布局；丘、取出组与索引见 compoundLayout。 */
import {T as LedgerTokens} from 'm2v/style/components/kit';
import Disc from 'm2v/style/components/disc';
import NumberText from 'm2v/style/components/number-text';
import {column, row, shelf} from 'm2v/style/components/disc-layout';
import {mixColor} from 'm2v/style/components/kit';

export const BG = LedgerTokens.canvas.background;
export const OFF_WHITE = LedgerTokens.colors.offWhite;
export const GOLD = LedgerTokens.colors.gold;
export const DARK_GOLD = LedgerTokens.colors.darkGold;
export const MUTED = LedgerTokens.colors.muted;
export const LINE = LedgerTokens.canvas.line;
export const FONT = LedgerTokens.type.fontStack;
export const RADIUS = LedgerTokens.disc.radius;

export type DiscState = 'white' | 'gold' | 'dark';
export type {Point} from './compoundLayout';

export {Disc, mixColor};
export const Text = NumberText;
export const columnPositions = column;
export const rowPositions = row;
export const shelfPositions = shelf;
export {FIRST_DISC_INDEX, hillPositions, withdrawBlockPositions} from './compoundLayout';
