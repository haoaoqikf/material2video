/** 复利作品的表现层入口：使用作品内圆片与文字组件；丘、取出组与索引见 compoundLayout。 */
import {T as LedgerTokens} from './components/kit';
import Disc from './components/disc';
import NumberText, {type NumberTextProps} from './components/number-text';
import {column, row, shelf} from './components/disc-layout';
import {mixColor} from './components/kit';

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
/** 本片文字统一标记为 body，供检查点合同与字号量测识别；作品组件保持默认 number。 */
export const Text = (props: NumberTextProps) => <NumberText {...props}/>;
export const columnPositions = column;
export const rowPositions = row;
export const shelfPositions = shelf;
export {FIRST_DISC_INDEX, hillPositions, withdrawBlockPositions} from './compoundLayout';
