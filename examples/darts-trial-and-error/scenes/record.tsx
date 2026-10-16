/**
 * 素材：把反馈写成三列表格。
 *
 * 示意图由 `useMediaAsset('darts-feedback')` 按素材 ID 取用——地址和实测尺寸来自
 * 准备阶段复核过的导入记录，作品代码不自己拼路径。图片未解码完成不调用 `ready()`，
 * 免得录制一开始就是一张空框。
 */
import {useEffect, useState} from 'react';
import {useMediaAsset, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, INSET, Panel, SIZE, Stage, contentBottom, mix, useNarration, useReadyWhen} from './stage';

const COLUMNS = [
  {title: '这次想验证什么', body: '写下一个可检验的假设，而不是一句愿望。'},
  {title: '实际发生什么', body: '记录与目标的差别，不急着解释原因。'},
  {title: '下次只改什么', body: '一次只动一个关键因素，下一轮再看结果。'},
];

export default function Record(props: CodeSceneProps) {
  const assetId = typeof props.props.assetId === 'string' ? props.props.assetId : 'darts-feedback';
  const asset = useMediaAsset(assetId);
  const [decoded, setDecoded] = useState(false);
  useEffect(() => {
    const image = new Image();
    image.onload = () => setDecoded(true);
    image.onerror = () => setDecoded(true);
    image.src = asset.src;
  }, [asset.src]);
  useReadyWhen(decoded);

  const clock = useNarration(props);
  const progress = clock.progress('darts-record-0');
  const board = {left: INSET, top: 400, width: 520, height: 580};

  return (
    <Stage props={props} title="把反馈写成记录"
      lead={`示意表来自已导入素材（${asset.kind === 'video' ? '视频' : '图片'}，实测 ${asset.width}×${asset.height}）`}>
      <Panel left={board.left} top={board.top} width={board.width} height={board.height}>
        <img src={asset.src} alt="反馈记录示意表"
          style={{width: '100%', height: '100%', objectFit: 'contain', opacity: mix(0.25, 1, progress)}}/>
      </Panel>
      <div style={{position: 'absolute', left: INSET + board.width + 44, top: board.top, width: 300}}>
        {COLUMNS.map((item, index) => (
          <div key={item.title} style={{marginBottom: 34, opacity: mix(0.35, 1, progress * 3 - index * 0.5)}}>
            <div style={{fontSize: SIZE.body, fontWeight: 700, color: COLOR.accent, marginBottom: 10}}>
              {`${index + 1}. ${item.title}`}
            </div>
            <div style={{fontSize: SIZE.note, lineHeight: 1.6, color: COLOR.muted}}>{item.body}</div>
          </div>
        ))}
      </div>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 58, fontSize: SIZE.body,
        color: COLOR.muted}}>
        把三列写下来，才能区分你改变了方法，还是仅仅重复了动作
      </div>
    </Stage>
  );
}
