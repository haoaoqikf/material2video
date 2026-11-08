/** 固定画布、关闭交互并在卸载时释放图表；option 动画使用 ECharts 原生时钟。 */
import {useEffect, useRef} from 'react';
import * as echarts from 'echarts';

export function Chart({option, width, height}: {
  option: echarts.EChartsOption; width?: number; height?: number;
}) {
  const canvas = window.__M2V_CODE_CONFIG__;
  if (!canvas) throw new Error('Chart 只能在代码场景录制页中使用');
  const host = useRef<HTMLDivElement>(null);
  const box = {width: width ?? canvas.width, height: height ?? canvas.height};
  useEffect(() => {
    const chart = echarts.init(host.current!, undefined, {...box, renderer: 'canvas',
      ...(canvas.captureScale ? {devicePixelRatio: canvas.captureScale} : {})});
    chart.setOption({...option, tooltip: {show: false}, toolbox: {show: false}, dataZoom: []});
    return () => chart.dispose();
  }, [option, box.width, box.height]);
  return <div ref={host} style={{...box, pointerEvents: 'none'}}/>;
}
