/**
 * 收束：设计缓冲之前要回答的三个问题，各自按真实旁白时间窗点亮。
 *
 * 三张卡片从左到右依次亮起，最后一段旁白落到底部结论：缓冲用存储换时间，
 * 不增加长期处理能力。
 */
import {motion} from 'm2v/code-scene';
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const QUESTIONS = [
  {segment: 'buffer-questions-0', index: '01', title: '波动有多大', body: '测量短期波动的大小与持续时长，不只比较平均。'},
  {segment: 'buffer-questions-1', index: '02', title: '允许等多久', body: '实时数据太晚就没有价值；离线任务的容忍度更高。'},
  {segment: 'buffer-questions-2', index: '03', title: '满了怎么办', body: '提前决定丢弃、拒绝还是通知上游，并观察积压趋势。'},
];

export default function Questions(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const bottom = contentBottom(props);
  const cards = {left: 200, top: 320, width: (props.width - 400 - 2 * 48) / 3, height: 330};

  return (
    <Stage props={props} title="设计缓冲，先问三个问题" note="三个问题决定容量、等待与失败策略">
      {QUESTIONS.map((item, index) => {
        const progress = clock.progress(item.segment);
        const x = cards.left + index * (cards.width + 48);
        return (
          <motion.div key={item.index}
            animate={{opacity: mix(0.25, 1, progress), y: mix(28, 0, progress)}}
            transition={{duration: 0.5, ease: 'easeOut'}}
            style={{position: 'absolute', left: x, top: cards.top, width: cards.width, height: cards.height,
              padding: 32, borderRadius: 16, background: COLOR.panel, border: `2px solid ${COLOR.rule}`,
              opacity: mix(0.25, 1, progress)}}>
            <div style={{fontSize: SIZE.note, color: COLOR.accent, marginBottom: 14}}>{item.index}</div>
            <div style={{fontSize: SIZE.lead, fontWeight: 700, marginBottom: 18}}>{item.title}</div>
            <div style={{fontSize: SIZE.body, lineHeight: 1.6, color: COLOR.muted}}>{item.body}</div>
            <div style={{position: 'absolute', left: 32, right: 32, bottom: 28, height: 6, borderRadius: 3,
              background: COLOR.rule}}>
              <div style={{width: `${progress * 100}%`, height: '100%', borderRadius: 3, background: COLOR.accent}}/>
            </div>
          </motion.div>
        );
      })}
      <div style={{position: 'absolute', left: 200, top: bottom - 56, fontSize: SIZE.lead}}>
        缓冲用存储换时间：吸收短期波动，不增加长期处理能力
      </div>
    </Stage>
  );
}
