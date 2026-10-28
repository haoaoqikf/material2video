import {useEffect, useMemo, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {cameraAt, keyframeAt, Painter, project} from '../code-scene/painter';
import {createMonteCarlo} from './simulation';
import './style.css';

if (import.meta.env.PROD) throw new Error('Painter 能力货架仅供开发服务器使用');

type Demo = {id: string; title: string; description: string; source: string;
  paint: (p: Painter, t: number) => void};

const simulation = createMonteCarlo(20261028, 1200);

const demos: Demo[] = [
  {id: 'layer', title: '离屏分组合成', description: '两个重叠圆先在缓冲层合成，再一起淡入、旋转和缩放。',
    source: `p.layer({alpha: t, at: [480, 270], rotate: t * .35, scale: .8 + t * .2}, layer => {\n  layer.circle(420, 270, 130, {fill: '#55D8FF'});\n  layer.circle(540, 270, 130, {fill: '#FF8B70'});\n});`,
    paint(p, t) {
      p.clear('#10151D');
      p.text('整组透明度', 480, 70, {size: 28, color: '#A9B5C4'});
      p.layer({alpha: t, at: [480, 270], rotate: (t - .5) * .45, scale: .82 + t * .18}, layer => {
        layer.circle(420, 270, 130, {fill: '#55D8FF'});
        layer.circle(540, 270, 130, {fill: '#FF8B70'});
      });
    }},
  {id: 'track', title: '数值关键帧', description: '不等间距关键帧驱动位置与尺度；拖动进度可检查任意时刻。',
    source: `const x = keyframeAt([{at: 0, value: 120}, {at: .3, value: 760}, {at: 1, value: 480}], t, 'smooth');\nconst r = keyframeAt([{at: 0, value: 24}, {at: .6, value: 70}], t, 'linear');\np.circle(x, 270, r, {fill: '#C6F36B'});`,
    paint(p, t) {
      p.clear('#10151D');
      const x = keyframeAt([{at: 0, value: 120}, {at: .3, value: 760}, {at: 1, value: 480}], t, 'smooth');
      const radius = keyframeAt([{at: 0, value: 24}, {at: .6, value: 70}], t);
      p.line(100, 270, 860, 270, {color: '#364250', width: 2});
      p.circle(x, 270, radius, {fill: '#C6F36B'});
      p.text(`x=${Math.round(x)}  r=${Math.round(radius)}`, 480, 400, {size: 24, color: '#E9F1FA'});
    }},
  {id: 'camera', title: '相机推拉', description: '相机状态由显式关键帧求值，再将世界坐标投影到画布。',
    source: `const camera = cameraAt([{at: 0, scale: 1, focusX: 480, focusY: 270},\n  {at: 1, scale: 1.9, focusX: 650, focusY: 330}], t);\nconst [x, y] = project(camera, [650, 330], 480, 270);`,
    paint(p, t) {
      p.clear('#10151D');
      const camera = cameraAt([{at: 0, scale: 1, focusX: 480, focusY: 270},
        {at: 1, scale: 1.9, focusX: 650, focusY: 330}], t);
      for (let i = 0; i < 8; i++) {
        const world: [number, number] = [180 + i * 85, 160 + Math.sin(i * 1.4) * 90];
        const [x, y] = project(camera, world, 480, 270);
        p.circle(x, y, Math.max(4, 14 * camera.scale), {fill: i === 5 ? '#F9D36B' : '#6E9BFF'});
      }
      p.text(`scale ${camera.scale.toFixed(2)}`, 480, 440, {size: 23, color: '#A9B5C4'});
    }},
  {id: 'simulation', title: '可回放模拟：蒙特卡洛估算 π', description: '固定种子预计算点集；任意进度都从同一批样本重建计数和曲线。',
    source: `const simulation = createMonteCarlo(20261028, 1200); // 固定种子，预计算一次\nconst {n, estimate} = simulation.at(t);\nconst curve = simulation.curve(t);\n// 计数和曲线读取同一份预计算前缀`,
    paint(p, t) {
      p.clear('#10151D');
      const {n, estimate} = simulation.at(t);
      const points = simulation.points;
      for (let i = 0; i < n; i++) {
        const [x, y] = points[i]!;
        const hit = x*x + y*y <= 1;
        p.circle(90 + x * 250, 40 + y * 250, 2.2, {fill: hit ? '#6EE7B7' : '#F28A83'});
      }
      p.text(`样本 ${n} / ${points.length}    π ≈ ${estimate.toFixed(4)}`, 610, 105,
        {size: 24, color: '#E9F1FA', align: 'left'});
      const barX = 610, barY = 160, barW = 230, barH = 210;
      p.rect(barX, barY, barW, barH, {color: '#435064', width: 2});
      p.line(barX + 115, barY, barX + 115, barY + barH, {color: '#435064', width: 1});
      p.line(barX, barY + 105, barX + barW, barY + 105, {color: '#435064', width: 1});
      const curve = simulation.curve(t);
      const curvePoints: [number, number][] = curve.map(point => [barX + point.progress * barW,
        barY + barH - Math.max(0, Math.min(4, point.value)) / 4 * barH]);
      if (curvePoints.length > 1) p.poly(curvePoints, {color: '#8FD8FF', width: 2});
      const referenceY = barY + barH - Math.PI / 4 * barH;
      p.line(barX, referenceY, barX + barW, referenceY, {color: '#F5CF73', width: 1, dash: [4, 5]});
      p.text('同一预计算样本同时驱动计数与点阵', 610, 415, {size: 19, color: '#A9B5C4', align: 'left'});
    }},
];

function App() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [selected, setSelected] = useState(demos[0]!.id);
  const [progress, setProgress] = useState(0);
  const [playing, setPlaying] = useState(true);
  const demo = useMemo(() => demos.find(item => item.id === selected)!, [selected]);
  useEffect(() => {
    if (!playing) return;
    let request = 0, previous = performance.now(), lastPaint = previous;
    const tick = (now: number) => {
      request = requestAnimationFrame(tick);
      if (now - lastPaint < 33) return;
      const delta = now - previous; previous = now; lastPaint = now;
      setProgress(value => { const next = value + delta / 9000;
        if (next >= 1) { setPlaying(false); return 1; } return next; });
    };
    request = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(request);
  }, [playing]);
  useEffect(() => {
    const target = canvas.current, ctx = target?.getContext('2d');
    if (!target || !ctx) return;
    target.width = 960; target.height = 540;
    demo.paint(new Painter(ctx, 960, 540), progress);
  }, [demo, progress]);
  const choose = (id: string) => { setSelected(id); setProgress(0); setPlaying(true); };
  return <main>
    <header><div><p className="eyebrow">MATERIAL2VIDEO · DEV TOOL</p><h1>Painter 能力货架</h1></div>
      <span>仅开发服务器提供 · 不进入作品构建</span></header>
    <nav>{demos.map(item => <button className={selected === item.id ? 'active' : ''}
      key={item.id} onClick={() => choose(item.id)}>{item.title}</button>)}</nav>
    <section className="showcase"><div className="screen"><canvas ref={canvas} /></div>
      <div className="controls"><button onClick={() => setPlaying(value => !value)}>{playing ? '暂停' : '播放'}</button>
        <button onClick={() => { setProgress(0); setPlaying(false); }}>复位</button>
        <input aria-label="演示进度" type="range" min="0" max="1" step="0.001" value={progress}
          onChange={event => { setPlaying(false); setProgress(Number(event.target.value)); }} />
        <output>{(progress * 100).toFixed(1)}%</output></div>
      <p className="description">{demo.description}</p>
      <aside><h2>最小调用</h2><pre><code>{demo.source}</code></pre></aside>
    </section>
  </main>;
}

createRoot(document.getElementById('root')!).render(<App />);
