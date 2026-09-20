/**
 * Adapted from Magic UI Shine Border at commit d7207e5692d14c00dceafa8488d6d01f197fa0e4.
 * Upstream: https://github.com/magicuidesign/magicui/blob/d7207e5692d14c00dceafa8488d6d01f197fa0e4/apps/www/registry/magicui/shine-border.tsx
 * License: MIT, full text in web/LICENSES/magicui-LICENSE.
 * Changes: removed Tailwind/cn, made tokens explicit, and wrapped the CSS animation in
 * FrameSyncedCssAnimation so Remotion owns time.
 */
import type { CSSProperties, HTMLAttributes } from 'react';
import { FrameSyncedCssAnimation } from './FrameSyncedCssAnimation';

export interface ShineBorderProps extends HTMLAttributes<HTMLDivElement> {
  borderWidth?: number;
  duration?: number;
  shineColor?: string | readonly string[];
}

export const ShineBorder: React.FC<ShineBorderProps> = ({
  borderWidth = 1,
  duration = 14,
  shineColor = 'var(--a2v-accent)',
  className,
  style,
  ...props
}) => {
  const colors = Array.isArray(shineColor) ? shineColor.join(',') : shineColor;
  return (
    <FrameSyncedCssAnimation className={className}>
      <div
        {...props}
        className="a2v-third-party-shine-border"
        style={{
          '--a2v-shine-border-width': `${borderWidth}px`,
          '--a2v-shine-duration': `${duration}s`,
          '--a2v-shine-colors': colors,
          ...style,
        } as CSSProperties}
      />
    </FrameSyncedCssAnimation>
  );
};
