/**
 * 对照：不断排名，还是按需筛选。
 *
 * 左侧是一张反复被推翻的排名：每次比较都重排，顺序没有停下来的时候。
 * 右侧是先写清需要的筛选条件，方案按条件逐条排除，顺序不再变。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const OPTIONS = ['方案一', '方案二', '方案三', '方案四'];
const NEEDS = ['预算可承受', '路程合适', '参与者愿意'];

export default function Compare(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const ranking = clock.progress('choice-compare-0');
  const filtering = clock.progress('choice-compare-1');
  const width = 760;
  // 排名每次重排：用相位取模让顺序周期性颠倒，表示「刚排好的顺序又被推翻」。
  const shuffle = Math.floor(ranking * 7);
  const order = OPTIONS.slice().sort((left, right) =>
    ((OPTIONS.indexOf(left) + shuffle) % OPTIONS.length) - ((OPTIONS.indexOf(right) + shuffle) % OPTIONS.length));

  return (
    <Stage props={props} title="反复排名，还是按需筛选" note="同一批方案，两种处理方式">
      <div style={{position: 'absolute', left: 180, top: 290, width}}>
        <div style={{fontSize: SIZE.lead, color: COLOR.muted, marginBottom: 24, opacity: mix(0.5, 1, ranking)}}>
          不断排名：每次比较都重排
        </div>
        {order.map((label, index) => (
          <div key={label} style={{display: 'flex', alignItems: 'center', height: 74, padding: '0 22px',
            marginBottom: 14, borderRadius: 10, border: `2px solid ${COLOR.rule}`, background: COLOR.panel,
            opacity: mix(0.4, 1, ranking)}}>
            <span style={{width: 54, color: COLOR.muted, fontSize: SIZE.note}}>{`#${index + 1}`}</span>
            <span style={{fontSize: SIZE.body}}>{label}</span>
          </div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 1050, top: 290, width: 690}}>
        <div style={{fontSize: SIZE.lead, color: COLOR.alt, marginBottom: 24, opacity: mix(0.5, 1, filtering)}}>
          按需筛选：先写清条件
        </div>
        {NEEDS.map((label, index) => (
          <div key={label} style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            height: 74, padding: '0 22px', marginBottom: 14, borderRadius: 10,
            border: `2px solid ${mix(0, 1, filtering * 3 - index) > 0.5 ? COLOR.alt : COLOR.rule}`,
            background: COLOR.panel, opacity: mix(0.4, 1, filtering * 3 - index)}}>
            <span style={{fontSize: SIZE.body}}>{label}</span>
            <span style={{fontSize: SIZE.note, color: COLOR.alt}}>必须</span>
          </div>
        ))}
        <div style={{marginTop: 30, fontSize: SIZE.body, lineHeight: 1.7, color: COLOR.muted}}>
          没有对所有人都最好的选项，只有当前目标下更合适的选择。
        </div>
      </div>
      <div style={{position: 'absolute', left: 180, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        标准一直变化，刚排好的顺序很快就会被推翻
      </div>
    </Stage>
  );
}
