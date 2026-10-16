/**
 * 对照：继续推演与小步试验各解决什么问题。
 *
 * 两块牌由各自的旁白时间窗点亮。左边写着推演能排除什么，右边写着试验能发现什么，
 * 两边的落点不同：一块是条件清单，一块是观察到的偏差。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const LEFT = ['检查已知条件', '排除明显不可行', '不产生新的偏差信息'];
const RIGHT = ['发现实际偏差', '获得可观察的结果', '把损失限制在可承受范围'];

export default function Compare(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const pushing = clock.progress('darts-compare-0');
  const trying = clock.progress('darts-compare-1');
  const width = (props.width - 2 * INSET - 32) / 2;
  const top = 430;
  const height = 780;

  return (
    <Stage props={props} title="准备与试验，各解决什么" lead="两条路都必要，但解决的问题不同">
      <Column left={INSET} top={top} width={width} height={height} label="继续推演" items={LEFT}
        active={pushing} tone={COLOR.muted}/>
      <Column left={INSET + width + 32} top={top} width={width} height={height} label="小步试验" items={RIGHT}
        active={trying} tone={COLOR.accent}/>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.lead}}>
        低成本不是随便做，而是把一次失败的损失限制在事先接受的范围
      </div>
    </Stage>
  );
}

function Column({left, top, width, height, label, items, active, tone}: {
  left: number; top: number; width: number; height: number;
  label: string; items: string[]; active: number; tone: string;
}) {
  return (
    <Panel left={left} top={top} width={width} height={height}>
      <div style={{position: 'absolute', left: 30, top: 30, right: 30, height: height - 60,
        opacity: mix(0.45, 1, active)}}>
        <div style={{fontSize: SIZE.lead, fontWeight: 700, color: tone, marginBottom: 26}}>{label}</div>
        {items.map((item, index) => (
          <div key={item} style={{fontSize: SIZE.body, lineHeight: 1.5, padding: '18px 0',
            borderBottom: index === items.length - 1 ? 'none' : `2px solid ${COLOR.rule}`,
            color: index === items.length - 1 ? COLOR.muted : COLOR.ink}}>{item}</div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 30, right: 30, bottom: 26, height: 8, borderRadius: 4,
        background: COLOR.rule}}>
        <div style={{width: `${mix(0, 100, active)}%`, height: '100%', borderRadius: 4, background: tone}}/>
      </div>
    </Panel>
  );
}
