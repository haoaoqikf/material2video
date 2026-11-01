/** 粗片复用正式 composition 和已录制片段，只播放，不编码完整视频。 */
import {createRoot} from 'react-dom/client';
import {Player} from '@remotion/player';
import {Audio} from 'remotion';
import {ArticleExplainer, type ArticleExplainerProps} from '../types/general/ArticleExplainer';
import {ensureFonts} from '../fonts';

type ReviewProps = ArticleExplainerProps & {reviewAudio?: string};
const Review = (props: ReviewProps) => <>
  <ArticleExplainer {...props}/>
  {props.reviewAudio ? <Audio src={props.reviewAudio}/> : null}
</>;

const container = document.getElementById('root');
if (!container) throw new Error('缺少播放容器');
void fetch('./timeline.json').then(async response => {
  if (!response.ok) throw new Error('缺少时间线');
  const props = await response.json() as ReviewProps;
  await ensureFonts();
  createRoot(container).render(<Player component={Review} inputProps={props}
    durationInFrames={props.durationInFrames} fps={props.fps} compositionWidth={props.width}
    compositionHeight={props.height} style={{width:'100%', maxWidth:props.width}} controls
    acknowledgeRemotionLicense/>);
}).catch(error => {container.textContent = String(error);});
