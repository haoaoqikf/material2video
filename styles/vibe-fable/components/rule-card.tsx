/**
 * 规则卡：居中的米色纸卡，略微倾斜，承载一句可读的结论或学名。
 * 卡片是「回到暗场」的时刻之一：周围场景压暗，卡片本身不发光。
 */
import {T, color} from './kit';

export type RuleCardProps = {
  title: string;
  body?: string;
  /** 拉丁学名或英文副题，斜体显示。 */
  latin?: string;
  frame?: number;
  startFrame?: number;
  opacity?: number;
  role?: string;
  state?: string;
};

export default function RuleCard({
  title, body, latin, frame, startFrame = 0, opacity = 1, role, state,
}: RuleCardProps) {
  const reveal = frame === undefined ? 1 : Math.min(1, Math.max(0, (frame - startFrame) / Math.max(1, T.motion.cardInFrames)));
  const eased = reveal * reveal * (3 - 2 * reveal);
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', left: '50%', top: '50%',
      transform: `translate(-50%, -50%) rotate(${T.type.cardTiltDegrees}deg) scale(${(0.94 + 0.06 * eased).toFixed(4)})`,
      opacity: opacity * eased, pointerEvents: 'none',
      width: 980, padding: '56px 64px 60px', borderRadius: 8,
      background: color('paper'), boxShadow: '0 22px 60px rgba(0,0,0,.35)',
      fontFamily: T.type.fontStack, color: color('paperInk'), textAlign: 'center',
    }}>
      {latin ? (
        <div style={{fontSize: 30, fontStyle: 'italic', color: '#6B5846', marginBottom: 14}}>{latin}</div>
      ) : null}
      <div style={{fontSize: T.type.cardTitle, fontWeight: 700, lineHeight: 1.3}}>{title}</div>
      {body ? (
        <div style={{fontSize: T.type.cardBody, lineHeight: 1.5, marginTop: 18, color: '#4A3A30'}}>{body}</div>
      ) : null}
    </div>
  );
}
