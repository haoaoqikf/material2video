/**
 * 开场：先给一段真实的走走停停，再追问原因。
 *
 * 镜头跟随低速区域：车辆相对路面仍在前进，红色制动灯反复亮起。画面只呈现现象，
 * 不在这一幕解释机制；数字与车距都是示意。
 */
import {useLayoutEffect, useRef} from 'react';
import type {CodeSceneProps} from 'm2v/code-scene';
import {gsap} from 'm2v/code-scene';
import {COLOR, Conclusion, SIZE, Stage, mix, useNarration, useReady} from './stage';
import {CarMark, StraightRoad} from './parts';
import {sample, slowCenter, wrapDelta} from './traffic';

const ROAD = {y: 486, height: 430};
// SVG 放在 y=ROAD.y，内部坐标从 0 开始；车道中心是局部坐标。
const CENTER = ROAD.height / 2;

export default function Open(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  // 取传播中段：此时低速带仍在车队里，开场直接看到走走停停。
  const simStart = Number(props.props.simStart ?? 12.5);
  const simSeconds = simStart + clock.elapsedSeconds;
  const cars = sample('high', simSeconds);
  const camera = slowCenter(cars) ?? cars[0].s;
  const band = useRef<HTMLDivElement>(null);
  const progress = clock.progress('jam-open-0');

  // GSAP 只做一次入场强调；车辆位置与灯态仍由录制时钟和轨迹数据决定。
  useLayoutEffect(() => {
    if (!band.current) return;
    gsap.fromTo(band.current, {opacity: 0, y: 26}, {opacity: 1, y: 0, duration: 0.8, ease: 'power2.out'});
  }, []);

  return (
    <Stage props={props} title="没有事故，为什么也会堵车？"
      lead="晚高峰的一条车道，没有撞车，也没有封路">
      <div ref={band}>
        <svg width={props.width} height={ROAD.height} style={{position: 'absolute', left: 0, top: ROAD.y}}>
          <StraightRoad width={props.width} y={0} height={ROAD.height} cameraS={camera} center={540}/>
          {cars.map(car => {
            const dx = wrapDelta(car.s, camera) * 1.12;
            if (Math.abs(dx) > 500) return null;
            return <CarMark key={car.id} x={540 + dx} y={CENTER} heading={0} braking={car.brake}
              label={car.id} scale={1.5} opacity={mix(0, 1, (500 - Math.abs(dx)) / 120)}/>;
          })}
        </svg>
      </div>
      <div style={{position: 'absolute', left: 96, top: 970, right: 96, display: 'flex', gap: 18}}>
        {['没有事故', '没有封路', '没有红绿灯'].map((item, index) => (
          <div key={item} style={{fontSize: SIZE.body, color: COLOR.muted, border: `2px solid ${COLOR.rule}`,
            borderRadius: 999, padding: '10px 22px', background: COLOR.paper,
            opacity: mix(0.2, 1, progress * 3 - index * 0.55)}}>{item}</div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 96, top: 1082, right: 96, fontSize: 44, fontWeight: 700,
        lineHeight: 1.35, opacity: mix(0.25, 1, progress * 2)}}>
        车没有停，路也没有断；<span style={{color: COLOR.brake}}>慢，却在车流里传开。</span>
      </div>
      <Conclusion props={props} headline="先记住这个现象：车辆都还在向前"
        note="同一时刻，有的车在走，有的车刚踩下刹车——轨迹与图表都是示意，不是实测。"/>
    </Stage>
  );
}
