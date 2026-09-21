import { Lightbulb } from 'lucide-react';
import { FrameIcon, frameStyle, probe, type A2VCodeScene } from '@a2v/scene';

/**
 * Tailwind + Lucide 示例：完整类名进构建 CSS，图标只由帧号驱动。
 *
 * 类名纪律（见 web/README.md）：`className` 里的类名必须是完整字符串；
 * 需要按状态切换时写进映射对象，运行时拼接不保证生成。
 */
const cardTone = {
  highlight: 'rounded-2xl border-2 shadow-xl',
  body: 'font-medium leading-relaxed',
} as const;

const LucideCard: A2VCodeScene<{ kicker: string; text: string; tip: string }> = ({
  scene,
  progress,
  theme,
}) => {
  return (
    <div
      className={`flex flex-col items-start gap-6 ${cardTone.highlight}`}
      style={{
        position: 'absolute',
        left: 96,
        top: 640,
        width: 888,
        padding: 48,
        backgroundColor: theme.theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
        borderColor: 'var(--a2v-accent)',
        ...frameStyle(Math.min(1, progress * 4), { opacity: true, rise: 36 }),
      }}
      {...probe({ node: 'card', role: 'body' })}
    >
      <FrameIcon icon={Lightbulb} size={96} color="var(--a2v-accent)" progress={Math.min(1, progress * 3)} aria-label="提示" />
      <div
        style={{ fontFamily: 'var(--a2v-font)', color: 'var(--a2v-accent)', fontSize: 44, letterSpacing: '0.14em' }}
        {...probe({ node: 'card-kicker', role: 'label' })}
      >
        {scene.data.kicker}
      </div>
      <div
        className={cardTone.body}
        style={{ fontFamily: 'var(--a2v-font)', color: 'var(--a2v-text-1)', fontSize: 72 }}
        {...probe({ node: 'card-text', role: 'headline' })}
      >
        {scene.data.text}
      </div>
      <div
        style={{ fontFamily: 'var(--a2v-font)', color: 'var(--a2v-line)', fontSize: 48 }}
        {...probe({ node: 'card-tip', role: 'caption' })}
      >
        {scene.data.tip}
      </div>
    </div>
  );
};

export default LucideCard;
