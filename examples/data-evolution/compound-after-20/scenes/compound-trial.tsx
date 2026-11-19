import {useLayoutEffect, useRef} from 'react';
import type {CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {makePhysicalStage} from './physical-stage';
import {TracedCanvas} from './pathtrace-study';
import {MacroGlassCanvas} from './macro-glass-study';
import {
  annualState, beats, chartX, contribution, fade, half, halfTotals, macroGlance, macroOffsetX, macroState,
  principal, rate, ratio, share, towerCenters, towerScale, yearly,
  type Layout,
} from './compound-model';

const font = '"M2V Inter", "M2V Sans"';
const white = '#f5f1e8';
const muted = '#a7b1c3';
const gold = '#ffce8f';
const integer = new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 0});
const yuan = (value: number) => integer.format(value);
const wan = (value: number) => (value / 1e4).toFixed(2);
const percent = (value: number) => `${Math.round(value * 100)}%`;
const small: CSSProperties = {fontSize: 29, fontWeight: 500, letterSpacing: '0.06em'};
const position = (left: number, top: number): CSSProperties => ({position: 'absolute', left, top});
const centered = (left: number, top: number): CSSProperties => ({...position(left, top), transform: 'translateX(-50%)', whiteSpace: 'nowrap'});

function Reinvestment({seconds, macro}: {seconds: number; macro: ReturnType<typeof macroState>}) {
  const firstY = macro.first.y;
  const contributionY = macro.extra.y;
  const interestTop = contributionY - macro.extra.height / 2 - macro.extra.depth * macroGlance;
  const interestBottom = macro.second.y + macro.second.height / 2;
  const firstLabel = fade(0.12, 0.4, seconds);
  const second = fade(2.27, 2.81, seconds);
  const firstAmount = firstLabel * (1 - fade(1.93, 2.16, seconds));
  return (
    <>
      <div style={{...position(137, 186), fontSize: 48, fontWeight: 520, color: gold}}>年利率 {percent(rate)}</div>
      <div style={{...position(128, 272), fontSize: 99, lineHeight: 1.16, fontWeight: 650, letterSpacing: '-0.065em'}}>
        利息也开始<br/>赚利息
      </div>
      <div style={{...position(138, 591), opacity: second, transform: `translateY(${(1 - second) * 20}px)`}}>
        <div style={{color: gold, fontSize: 104, lineHeight: 1, letterSpacing: '-0.068em', fontWeight: 540}}>
          +{yuan(contribution)}<span style={{fontSize: 38, marginLeft: 16, letterSpacing: 0}}>元</span>
        </div>
        <div style={{fontSize: 45, fontWeight: 520, color: white, marginTop: 24}}>首年收益<br/>{yuan(yearly[0])} 元带来的利息</div>
      </div>
      <div style={{position: 'absolute', inset: 0, transform: `translateX(${macroOffsetX}px)`}}>
      <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
        <path d={`M 1511 ${firstY + 7} h 94 l 31 -24 h 41`} stroke="#ffe0ac" strokeWidth="3.2" strokeOpacity={0.82 * firstAmount} fill="none"/>
        <path d={`M 1079 ${contributionY} h -33 l -52 -65 h -70`} stroke="#fff0d2" strokeWidth="3.1" strokeOpacity={second * 0.9} fill="none"/>
        <circle cx="1079" cy={contributionY} r="5.7" opacity={second} fill={gold}/>
        <path d={`M 1648 ${interestTop} h 24 V ${interestBottom} h -24 M 1672 ${(interestTop + interestBottom) / 2} h 32`}
          stroke="#ffdcaa" strokeWidth="3.2" strokeOpacity={second * 0.9} fill="none"/>
      </svg>
      <span style={{...position(879, contributionY - 123), fontSize: 43, fontWeight: 560, color: gold, opacity: second}}>{yuan(contribution)} 元</span>
      <span style={{...position(1694, firstY - 47), fontSize: 49, lineHeight: 1.13, fontWeight: 540, color: gold, opacity: firstAmount}}>首年收益<br/>+{yuan(yearly[0])} 元</span>
      <span style={{...centered(macro.first.x - macroOffsetX, 852), fontSize: 49, fontWeight: 540, color: white}}>本金 {yuan(principal)} 元</span>
      <span style={{...position(1722, 469), fontSize: 44, lineHeight: 1.17, fontWeight: 540, color: gold, opacity: second, whiteSpace: 'nowrap'}}>
        次年收益<br/>{yuan(yearly[0])} + {yuan(contribution)}<br/>= {yuan(yearly[1])} 元
      </span>
      </div>
    </>
  );
}

function TracedReinvestment({seconds}: {seconds: number}) {
  const first = fade(.10, .42, seconds) * (1 - fade(1.84, 2.14, seconds));
  const second = fade(2.26, 2.76, seconds);
  return (
    <>
      <div style={{...position(137, 173), fontSize: 47, fontWeight: 530, color: gold}}>年利率 {percent(rate)}</div>
      <div style={{...position(128, 269), fontSize: 97, lineHeight: 1.13, fontWeight: 650, letterSpacing: '-0.063em'}}>利息也开始<br/>赚利息</div>
      <div style={{...position(138, 645), fontSize: 91, lineHeight: 1.04, letterSpacing: '-.063em', opacity: first, color: gold}}>
        +{yuan(yearly[0])}<span style={{fontSize: 38, marginLeft: 14, letterSpacing: 0}}>元</span>
        <div style={{fontSize: 44, color: white, marginTop: 16, letterSpacing: 0}}>首年收益</div>
      </div>
      <div style={{...position(138, 645), fontSize: 91, lineHeight: 1.04, letterSpacing: '-.063em', opacity: second, color: gold}}>
        +{yuan(contribution)}<span style={{fontSize: 38, marginLeft: 14, letterSpacing: 0}}>元</span>
        <div style={{fontSize: 44, color: white, marginTop: 16, letterSpacing: 0}}>来自首年留下的<br/>{yuan(yearly[0])} 元收益</div>
      </div>
      <div style={{...position(1594, 366), color: gold, fontSize: 43, lineHeight: 1.2, whiteSpace: 'nowrap', opacity: second}}>
        次年收益<br/>{yuan(yearly[0])} + {yuan(contribution)}<br/>= {yuan(yearly[1])} 元
      </div>
      <div style={{...centered(1166, 936), fontSize: 47, color: white}}>本金 {yuan(principal)} 元</div>
    </>
  );
}

type AnnualState = ReturnType<typeof annualState>;

function ChartLabels({seconds, state}: {seconds: number; state: AnnualState}) {
  const visible = 1 - fade(beats.assemble, beats.assemble + 0.24, seconds);
  const last = yearly.length - 1;
  const lastLabel = fade(beats.chart + last * beats.yearStep, beats.chart + last * beats.yearStep + 0.46, seconds);
  return (
    <div style={{position: 'absolute', inset: 0, opacity: visible}}>
      <div style={{...position(133, 110), fontSize: 48, lineHeight: 1.12, fontWeight: 520, color: gold}}>年利率 {percent(rate)}</div>
      <div style={{...position(127, 183), fontSize: 99, letterSpacing: '-0.063em', fontWeight: 650}}>每年的新增收益</div>
      <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
        <line x1="132" x2="1785" y1={state.baseline} y2={state.baseline} stroke="#94a9c9" strokeOpacity=".64"/>
        {[0, 19, 39].map(index => <line key={index} x1={chartX(index)} x2={chartX(index)}
          y1={state.baseline} y2={state.baseline + 13} stroke="#94a9c9" strokeOpacity=".64"/>)}
      </svg>
      {[0, 19, 39].map(index => (
        <span key={index} style={{...centered(chartX(index), state.baseline + 26), fontSize: 46, fontWeight: 520, color: white}}>第 {index + 1} 年</span>
      ))}
      <span style={{...position(154, state.baseline - 104), fontSize: 40, color: gold}}>+{yuan(yearly[0])} 元</span>
      <span style={{...position(1476, 221), fontSize: 52, color: gold, opacity: lastLabel}}>+{wan(yearly[last])} 万元</span>
    </div>
  );
}

function TowerLabels({seconds, state, layout}: {seconds: number; state: AnnualState; layout: Layout}) {
  const show = fade(beats.assemble + 2.55, beats.assemble + 3.1, seconds);
  const shareShow = fade(beats.assemble + 3.27, beats.assemble + 3.7, seconds);
  const grouping = fade(beats.assemble + .31, beats.assemble + .88, seconds);
  const grounded = fade(beats.assemble + 2.20, beats.assemble + 2.50, seconds);
  const baseLineStart = 132 + ((layout === 'offset' ? 864 : 555) - 132) * grounded;
  const centers = towerCenters(layout);
  return (
    <div style={{position: 'absolute', inset: 0}}>
      {layout === 'offset' ? (
        <div style={{...position(137, 197), opacity: grouping}}>
          <div style={{fontSize: 73 - 11 * show, fontWeight: 620, letterSpacing: '-0.05em'}}>同样是 20 年</div>
          <div style={{fontSize: 176, lineHeight: 1.02, fontWeight: 550, letterSpacing: '-0.064em', marginLeft: -9, color: gold, marginTop: 19, opacity: show}}>{ratio.toFixed(2)}×</div>
          <div style={{fontSize: 46, fontWeight: 520, marginTop: 24, color: white, opacity: show}}>后 20 年收益 ÷ 前 20 年收益</div>
        </div>
      ) : (
        <div style={{...position(137, 154), opacity: show}}>
          <div style={{fontSize: 55, lineHeight: 1, fontWeight: 640, letterSpacing: '-0.05em'}}>同样是 20 年</div>
          <div style={{fontSize: 119, fontWeight: 550, color: gold, letterSpacing: '-0.08em', marginTop: 17}}>{ratio.toFixed(2)}×</div>
          <div style={{...small, color: muted}}>后期收益 ÷ 前期收益</div>
        </div>
      )}
      <div style={{...position(baseLineStart, state.baseline), right: 144, height: 3 - grounded,
        opacity: grouping, background: 'linear-gradient(90deg,#526479,#9baec9 38%,#9baec9 73%,#526479)'}}/>
      {centers.map((center, index) => (
        <div key={center}>
          <span style={{...centered(state.groupCenters[index], state.baseline + 41),
            fontSize: 43, fontWeight: 530, color: white, opacity: grouping}}>{index ? '后' : '前'} {half} 年</span>
          <div style={{...centered(center, state.baseline - halfTotals[index] * towerScale - (index ? 123 : 108)),
            fontSize: index ? 67 : 58, letterSpacing: '-0.056em', color: index ? white : gold, fontWeight: 560, opacity: show}}>
            +{wan(halfTotals[index])}<span style={{fontSize: 32, letterSpacing: 0, marginLeft: 10}}>万元</span>
          </div>
        </div>
      ))}
      <div style={{...position(140, 655), opacity: shareShow, fontSize: 42, color: white}}>
        前 20 年约占总收益 <strong style={{color: gold, fontWeight: 650}}>{percent(share)}</strong>
      </div>
    </div>
  );
}

export default function CompoundTrial(config: CodeSceneProps) {
  const {elapsedSeconds, ready} = useSceneContext();
  const canvas = useRef<HTMLCanvasElement>(null);
  const stage = useRef<ReturnType<typeof makePhysicalStage> | null>(null);
  const layout: Layout = config.props.layout === 'center' ? 'center' : 'offset';
  const pathtrace = config.props.renderer === 'webgpu';
  const macroLook = config.props.macroLook === 'cut' || config.props.macroLook === 'slit'
    || config.props.macroLook === 'studio' || config.props.macroLook === 'window' || config.props.macroLook === 'fluted'
    || config.props.macroLook === 'overhead'
    ? config.props.macroLook : 'classic';
  const samples = typeof config.props.samples === 'number' ? Math.min(72, Math.max(8, config.props.samples)) : 24;
  const isMacro = elapsedSeconds < beats.chart;
  const macroGlassLook = pathtrace && isMacro && (config.props.macroGlass === 'clear'
    || config.props.macroGlass === 'prism' || config.props.macroGlass === 'lens')
    ? config.props.macroGlass : null;
  const macro = macroState(elapsedSeconds);
  const annual = annualState(elapsedSeconds, layout);
  const blocks = isMacro ? macro.blocks : annual.blocks;
  const rendererDensity = config.captureScale ?? 1;
  const floor = isMacro ? 790 : annual.baseline;
  const reflections = isMacro ? .23 : fade(beats.assemble + 1.45, beats.assemble + 2.54, elapsedSeconds) * .20;
  const settled = isMacro ? 0 : fade(beats.assemble + 1.12, beats.assemble + 2.40, elapsedSeconds);
  const obliqueRise = isMacro ? macroGlance : (pathtrace ? .22 : macroGlance) * fade(beats.assemble + .16, beats.assemble + 1.45, elapsedSeconds);

  useLayoutEffect(() => {
    if (pathtrace || !canvas.current) return;
    stage.current = makePhysicalStage(canvas.current, config.width, config.height, rendererDensity, yearly.length);
    return () => {
      stage.current?.dispose();
      stage.current = null;
    };
  }, [config.width, config.height, pathtrace, rendererDensity]);

  useLayoutEffect(() => {
    if (pathtrace) return;
    const scan = fade(beats.assemble + 2.55, beats.assemble + 3.78, elapsedSeconds);
    const sweepAt = isMacro ? 1040 + 1020 * fade(0.44, 3.9, elapsedSeconds) : 785 + 1440 * scan;
    stage.current?.draw(blocks, {sweep: sweepAt, floor, reflection: reflections, landed: settled, glancing: obliqueRise, isMacro});
    ready();
  }, [blocks, elapsedSeconds, isMacro, pathtrace, ready, floor, reflections, settled, obliqueRise]);

  return (
    <div style={{position: 'relative', width: config.width, height: config.height, overflow: 'hidden', color: white, fontFamily: font, background: '#050b16'}}>
      {pathtrace ? (
        <TracedCanvas width={config.width} height={config.height} state={{blocks, floor, rise: obliqueRise, isMacro, sculpture: settled, reveal: isMacro ? macro.reveal : 0}}
          samples={samples} capacity={yearly.length} macroLook={macroLook} active={macroGlassLook === null}/>
      ) : (
        <canvas ref={canvas} aria-hidden="true" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}/>
      )}
      {macroGlassLook && <MacroGlassCanvas width={config.width} height={config.height} macro={macro} look={macroGlassLook}/>}
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${config.width / 1920}, ${config.height / 1080})`, transformOrigin: '0 0'}}>
        {!isMacro && <ChartLabels seconds={elapsedSeconds} state={annual}/>}
        {isMacro ? (
          pathtrace ? <TracedReinvestment seconds={elapsedSeconds}/> : <Reinvestment seconds={elapsedSeconds} macro={macro}/>
        ) : (
          <TowerLabels seconds={elapsedSeconds} state={annual} layout={layout}/>
        )}
      </div>
    </div>
  );
}
