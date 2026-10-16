/**
 * 机制：一轮反馈链——做小试验 → 记录偏差 → 修正方法。
 *
 * 三个环节按旁白时间窗依次点亮，箭头同时出现；第三段旁白把「结果没改善」也接回链路，
 * 说明它同样是一条需要解释的信息，而不是试错失败的证据。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const STEPS = [
  {segment: 'darts-chain-0', title: '做小试验', body: '在可承受的成本内取得可观察的结果'},
  {segment: 'darts-chain-1', title: '记录偏差', body: '保留结果与目标的差别，不看结论看证据'},
  {segment: 'darts-chain-2', title: '修正方法', body: '下一轮重新观察，不把旧结论当成永远正确'},
];

export default function Chain(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const top = 460;
  const stepHeight = 252;
  const gap = 28;
  const width = props.width - 2 * INSET;
  const fallback = clock.spoken('darts-chain-2');

  return (
    <Stage props={props} title="从一次尝试走到下一次" lead="一轮结束就重新观察，而不是把结论固化">
      {STEPS.map((item, index) => {
        const progress = clock.progress(item.segment);
        const y = top + index * (stepHeight + gap);
        return (
          <div key={item.title}>
            <Panel left={INSET} top={y} width={width} height={stepHeight}>
              <div style={{position: 'absolute', left: 34, top: 40, right: 34, opacity: mix(0.4, 1, progress)}}>
                <div style={{fontSize: SIZE.note, color: COLOR.accent}}>{`0${index + 1}`}</div>
                <div style={{fontSize: SIZE.lead, fontWeight: 700, margin: '12px 0 14px'}}>{item.title}</div>
                <div style={{fontSize: SIZE.body, lineHeight: 1.55, color: COLOR.muted}}>{item.body}</div>
              </div>
              <div style={{position: 'absolute', left: 34, right: 34, bottom: 24, height: 8, borderRadius: 4,
                background: COLOR.rule}}>
                <div style={{width: `${mix(0, 100, progress)}%`, height: '100%', borderRadius: 4,
                  background: COLOR.accent}}/>
              </div>
            </Panel>
            {index < STEPS.length - 1 && (
              <div style={{position: 'absolute', left: INSET + width / 2 - 22, top: y + stepHeight - 4,
                width: 44, height: gap + 8, textAlign: 'center', fontSize: 30, color: COLOR.accent,
                opacity: mix(0.3, 1, clock.progress(STEPS[index + 1].segment))}}>↓</div>
            )}
          </div>
        );
      })}
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.body,
        color: fallback ? COLOR.danger : COLOR.muted}}>
        没有改善也是一条需要解释的信息：方向不对、指标太粗，或者这问题不适合这样试
      </div>
    </Stage>
  );
}
