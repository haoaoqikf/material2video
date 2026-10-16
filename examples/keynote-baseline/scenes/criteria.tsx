/**
 * 方法：把需要变成筛选标准。
 *
 * 三列从左到右依次亮起，每列由它自己的旁白时间窗驱动：「底线与偏好」用颜色区分，
 * 「比较重要差异」列出权重，「比较截止点」画出一条终点线。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const BASELINE = ['预算上限', '路程上限'];
const PREFERENCE = ['某种风格', '额外功能'];

export default function Criteria(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const first = clock.progress('choice-criteria-0');
  const second = clock.progress('choice-criteria-1');
  const third = clock.progress('choice-criteria-2');
  const column = {top: 300, width: 460, height: 480};

  return (
    <Stage props={props} title="把需要变成筛选标准" note="三步都把判断依据写在纸面上">
      <Column left={180} top={column.top} width={column.width} height={column.height}
        label="01 写下必须条件" active={first}>
        <Group title="底线（先排除）" items={BASELINE} tone={COLOR.accent}/>
        <Group title="偏好（可让步）" items={PREFERENCE} tone={COLOR.muted}/>
      </Column>
      <Column left={730} top={column.top} width={column.width} height={column.height}
        label="02 只比较重要差异" active={second}>
        <Weight label="价格" value={0.42} active={second}/>
        <Weight label="时间" value={0.34} active={second}/>
        <Weight label="风格" value={0.12} active={second}/>
        <div style={{marginTop: 22, fontSize: SIZE.note, color: COLOR.muted}}>
          标准可以修正，但要说明是什么新信息让它改变。
        </div>
      </Column>
      <Column left={1280} top={column.top} width={column.width} height={column.height}
        label="03 确定比较截止点" active={third}>
        {/* 三条候选都从同一条基准线开始，长度可比；右侧虚线是比较的截止点。 */}
        <svg width={column.width - 60} height={300} style={{position: 'absolute', left: 30, top: 130}}>
          {['方案一', '方案二', '方案三'].map((label, index) => {
            const reached = Math.min(1, Math.max(0, third * 3 - index));
            const length = mix(0.14, 1, mix(0.15, 0.92, reached)) * 250;
            return (
              <g key={label}>
                <text x={108} y={26 + index * 66} fill={COLOR.muted} fontSize={SIZE.note} textAnchor="end">{label}</text>
                <rect x={124} y={8 + index * 66} width={length} height={16} rx={8}
                  fill={index === 0 ? COLOR.accent : COLOR.rule}/>
              </g>
            );
          })}
          <line x1={124 + 250 * 0.72} x2={124 + 250 * 0.72} y1={-6} y2={196}
            stroke={COLOR.accent} strokeWidth={3} strokeDasharray="10 8" opacity={third}/>
          <text x={124 + 250 * 0.72 - 8} y={216} fill={COLOR.accent} fontSize={SIZE.note} textAnchor="end"
            opacity={third}>足够好就停</text>
        </svg>
      </Column>
      <div style={{position: 'absolute', left: 180, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        达到足够好的条件后，就可以把精力转向行动
      </div>
    </Stage>
  );
}

function Column({left, top, width, height, label, active, children}: {
  left: number; top: number; width: number; height: number; label: string; active: number;
  children: React.ReactNode;
}) {
  return (
    <div style={{position: 'absolute', left, top, width, height, borderRadius: 16, background: COLOR.panel,
      border: `2px solid ${mix(0, 1, active) > 0.5 ? COLOR.rule : COLOR.bg}`, opacity: mix(0.4, 1, active)}}>
      <div style={{position: 'absolute', left: 30, top: 30, fontSize: SIZE.body, color: COLOR.accent}}>{label}</div>
      <div style={{position: 'absolute', left: 30, right: 30, top: 90, bottom: 30}}>{children}</div>
    </div>
  );
}

function Group({title, items, tone}: {title: string; items: string[]; tone: string}) {
  return (
    <div style={{marginBottom: 22}}>
      <div style={{fontSize: SIZE.note, color: tone, marginBottom: 10}}>{title}</div>
      {items.map(item => (
        <div key={item} style={{fontSize: SIZE.body, padding: '10px 0', borderBottom: `2px solid ${COLOR.rule}`}}>
          {item}
        </div>
      ))}
    </div>
  );
}

function Weight({label, value, active}: {label: string; value: number; active: number}) {
  return (
    <div style={{marginBottom: 18}}>
      <div style={{fontSize: SIZE.note, color: COLOR.muted, marginBottom: 8}}>{label}</div>
      <div style={{height: 16, borderRadius: 8, background: COLOR.rule}}>
        <div style={{width: `${mix(0, value * 100, active)}%`, height: '100%', borderRadius: 8,
          background: COLOR.alt}}/>
      </div>
    </div>
  );
}
