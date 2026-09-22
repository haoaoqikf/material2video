/**
 * 受控图标白名单：`icon` 与 `pictogram` 原语唯一的图标来源。
 *
 * 三条硬约束：
 *
 * 1. **静态**：图标是模块级具名导入，没有动态 `import()`、没有字符串查表到
 *    任意组件、没有运行时注册。分镜里的 `icon` 名字在校验阶段就被限定在
 *    白名单内（`ICON_NAMES` 由注册表生成），未知名字根本进不了渲染。
 * 2. **离线**：Lucide 组件自绘全部路径，不引用外部 `<use href>` 或 CDN URL，
 *    离线渲染不会静默空白。
 * 3. **帧驱动**：这里只提供图形，不提供时间。透明度与描边进度由调用方按
 *    当前帧算好传进来，组件本身不写 transition/animation。
 *
 * 白名单与注册表的对应关系由类型系统强制：`ICON_SET` 声明成
 * `Record<IconName, LucideIcon>`，注册表加了名字而这里没加组件就编译不过。
 */
import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight, Check, CircleDollarSign, Clock, Database, Link as LinkIcon, Lock,
  Sparkles, Target, TrendingDown, TrendingUp, TriangleAlert, Users, X,
} from 'lucide-react';
import type { IconName } from '@/schema/primitiveTypes';

/** 受控图标名 → Lucide 组件。键必须与注册表的 `icons` 完全一致。 */
export const ICON_SET: Readonly<Record<IconName, LucideIcon>> = {
  arrow: ArrowRight,
  check: Check,
  cross: X,
  spark: Sparkles,
  up: TrendingUp,
  down: TrendingDown,
  users: Users,
  clock: Clock,
  target: Target,
  alert: TriangleAlert,
  lock: Lock,
  link: LinkIcon,
  database: Database,
  coin: CircleDollarSign,
};

/** 默认图标：分镜没写 `icon` 时用它，取值固定，不随机。 */
export const DEFAULT_ICON: IconName = 'spark';

export interface IconGlyphProps {
  name?: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

/**
 * 白名单图标组件。未知名字退回默认图标而不是抛错——校验阶段已经拦过，
 * 这里只兜住旧分镜（`icon` 缺省）与代码场景的宽松调用。
 */
export function IconGlyph({ name, size = 48, strokeWidth = 1.75, className }: IconGlyphProps): React.ReactElement {
  const Icon = ICON_SET[name ?? DEFAULT_ICON] ?? ICON_SET[DEFAULT_ICON];
  return <Icon size={size} strokeWidth={strokeWidth} className={className} aria-hidden="true" />;
}
