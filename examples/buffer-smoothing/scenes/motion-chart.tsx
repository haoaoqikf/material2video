import {useEffect, useMemo} from 'react';
import {motion, Chart, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export default function MotionChart({props}: CodeSceneProps) {
  const {ready, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  const option = useMemo(() => ({animationDuration: 1800, textStyle: {color: '#f3f4f6'},
    xAxis: {type: 'category' as const, data: ['观察', '反馈', '修正']}, yAxis: {type: 'value' as const},
    series: [{type: 'bar' as const, data: [24, 52, 84], itemStyle: {color: '#f7c85b'}}]}), []);
  return <div>
    <motion.div initial={{opacity: 0, y: 40}} animate={running ? {opacity: 1, y: 0} : {opacity: 0, y: 40}}
      transition={{type: 'spring'}} style={{fontSize: 48, padding: 30}}>{String(props.label ?? '逐步吸收变化')}</motion.div>
    {running && <Chart option={option} height={740}/>}
  </div>;
}
