/**
 * 回放：把镜头推近，只看一次减速。
 *
 * 上半屏保留环路位置，下半屏跟随 1 号车展开局部车距。镜头跟着 1 号车移动，
 * 路面虚线因此后退；后车与它的间距、速度条与制动灯都来自同一帧轨迹。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';
import {CarMark, LoopRoad, StraightRoad} from './parts';
import {TRAFFIC, gapToAhead, gapUnits, sample, speedRatio} from './traffic';

const LOOP = {x: 540, y: 620, scale: 0.52};
const BAND = {y: 970, height: 300};
// 直路 SVG 以 BAND.y 定位，内部使用局部坐标。
const CENTER = BAND.height / 2;
// 1 号车略偏右，后方的车距标注才有足够空间。
const ZOOM_X = 650;

export default function Brake(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  // 从扰动前两秒入场：旁白说到「轻点刹车」时，减速正好发生在画面里。
  const simStart = Number(props.props.simStart ?? TRAFFIC.disturbance.start - 2);
  const cars = sample('high', simStart + clock.elapsedSeconds);
  const leader = cars[0];
  const camera = leader.s;
  const visible = cars.filter(car => {
    const dx = car.s - camera;
    return dx > -580 && dx < 90;
  });
  const braking = leader.brake;
  const ratio = speedRatio(leader.speed);

  return (
    <Stage props={props} title="回放到起点：只看 1 号车的一次刹车"
      lead="速度降下来，又很快恢复——先看一次扰动本身">
      <div style={{position: 'absolute', left: 96, top: 330, fontSize: SIZE.note, color: COLOR.muted,
        border: `2px solid ${COLOR.rule}`, borderRadius: 999, padding: '6px 18px', background: COLOR.paper}}>
        回放 · 从初始状态开始
      </div>
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${LOOP.x} ${LOOP.y}) scale(${LOOP.scale}) translate(${-LOOP.x} ${-LOOP.y})`}>
          <LoopRoad cx={LOOP.x} cy={LOOP.y} width={96}/>
          {cars.map(car => <CarMark key={car.id} x={LOOP.x + car.x} y={LOOP.y + car.y}
            heading={car.heading} braking={car.brake} focus={car.id === 1} label={car.id} scale={1.35}/>)}
        </g>
      </svg>

      <div style={{position: 'absolute', left: 96, top: 940, right: 96, fontSize: SIZE.note,
        color: COLOR.muted}}>跟随 1 号车，放大后车车距</div>
      <svg width={props.width} height={BAND.height} style={{position: 'absolute', left: 0, top: BAND.y}}>
        <StraightRoad width={props.width} y={0} height={BAND.height} cameraS={camera} center={540}/>
        {visible.map(car => {
          const dx = car.s - camera;
          return <CarMark key={car.id} x={ZOOM_X + dx} y={CENTER} heading={0} braking={car.brake}
            focus={car.id === 1} label={car.id} scale={1.3}
            opacity={mix(0.2, 1, (580 - Math.abs(dx)) / 120)}/>;
        })}
        {visible.filter(car => car.id > 1 && car.id <= 5).map(car => {
          const gap = gapToAhead(cars, car.id - 1);
          const x1 = ZOOM_X + (cars[car.id - 2].s - camera);
          const x2 = ZOOM_X + (car.s - camera);
          const y = CENTER + 66;
          return <g key={`gap-${car.id}`}>
            <line x1={x1} x2={x2} y1={y} y2={y} stroke={COLOR.muted} strokeWidth={2}/>
            <line x1={x1} x2={x1} y1={y - 8} y2={y + 8} stroke={COLOR.muted} strokeWidth={2}/>
            <line x1={x2} x2={x2} y1={y - 8} y2={y + 8} stroke={COLOR.muted} strokeWidth={2}/>
            <text x={(x1 + x2) / 2} y={y + 30} textAnchor="middle" fontSize={SIZE.note}
              fill={COLOR.muted}>{`${gapUnits(gap).toFixed(1)} 车位`}</text>
          </g>;
        })}
        {braking && <g>
          <circle cx={ZOOM_X} cy={CENTER - 62} r={30} fill={COLOR.brake} opacity={0.16}/>
          <text x={ZOOM_X} y={CENTER - 86} textAnchor="middle" fontSize={SIZE.note} fontWeight={700}
            fill={COLOR.brake}>制动</text>
        </g>}
      </svg>

      <div style={{position: 'absolute', left: 96, top: 1352, right: 96}}>
        <div style={{display: 'flex', justifyContent: 'space-between', fontSize: SIZE.note,
          color: COLOR.muted, marginBottom: 10}}>
          <span>1 号车速度</span><span>{`${Math.round(ratio * 100)}%`}</span>
        </div>
        <div style={{height: 16, borderRadius: 8, background: COLOR.rule, overflow: 'hidden'}}>
          <div style={{width: `${Math.round(ratio * 100)}%`, height: '100%', borderRadius: 8,
            background: braking ? COLOR.brake : COLOR.accent}}/>
        </div>
        <div style={{fontSize: SIZE.note, color: COLOR.muted, marginTop: 12}}>
          右侧后视：{visible.some(car => car.id > 1 && car.brake) ? '后车已经开始响应' : '后车仍保持巡航'}
        </div>
      </div>
      <div style={{position: 'absolute', left: 96, top: contentBottom(props) - 4, fontSize: SIZE.note,
        color: COLOR.muted}}>车距按车身长度折算，只用于比较相对变化</div>
    </Stage>
  );
}
