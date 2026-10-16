/**
 * 边界：并非所有选择都该只剩一个。
 *
 * 左侧是「可以收敛」的一类：代价可承受、还能调整，达到足够好就可以动。
 * 右侧是「必须保留多个」的一类：信息不足或难以撤回，备选不是犹豫而是保险。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const CASES = [
  {title: '可逆、代价可承受', body: '达到足够好的条件就行动，新信息来了再调整。', keep: false},
  {title: '信息不足', body: '保留备选，等关键信息出现再比较。', keep: true},
  {title: '重大且难以撤回', body: '需要更充分的比较，宁可多留一个方案。', keep: true},
];

export default function Boundary(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const progress = clock.progress('choice-boundary-0');
  const top = 320;
  const height = 380;
  const width = (props.width - 260 - 2 * 28) / 3;

  return (
    <Stage props={props} title="并非所有选择都该只剩一个" note="减少比较是为了腾出注意力，不是省掉判断">
      {CASES.map((item, index) => {
        const reached = Math.min(1, Math.max(0, progress * 3 - index * 0.6));
        return (
          <div key={item.title} style={{position: 'absolute', left: 130 + index * (width + 28), top,
            width, height, borderRadius: 16, background: COLOR.panel,
            border: `3px solid ${item.keep ? COLOR.alt : COLOR.accent}`, opacity: mix(0.35, 1, reached)}}>
            <div style={{padding: 32}}>
              <div style={{fontSize: SIZE.note, color: item.keep ? COLOR.alt : COLOR.accent, marginBottom: 16}}>
                {item.keep ? '保留多个方案' : '可以收敛到一个'}
              </div>
              <div style={{fontSize: SIZE.lead, lineHeight: 1.35, marginBottom: 22}}>{item.title}</div>
              <div style={{fontSize: SIZE.body, lineHeight: 1.7, color: COLOR.muted}}>{item.body}</div>
            </div>
            <div style={{position: 'absolute', left: 32, right: 32, bottom: 28, display: 'flex', gap: 12}}>
              {(item.keep ? ['主选', '备选'] : ['主选']).map(label => (
                <div key={label} style={{padding: '8px 20px', borderRadius: 999, fontSize: SIZE.note,
                  border: `2px solid ${item.keep ? COLOR.alt : COLOR.accent}`}}>{label}</div>
              ))}
            </div>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: 130, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        少一个选项不是通用答案；减少比较，是为了腾出注意力
      </div>
    </Stage>
  );
}
