/** 按已登记素材 ID 取本地地址与实测信息；未登记时明确失败。 */
import type {MediaAsset} from './context';

export function useMediaAsset(id: string): MediaAsset {
  const media = window.__M2V_CODE_CONFIG__?.media;
  const asset = media?.[id];
  if (!asset) throw new Error(`未登记的素材 ID：${id}；请先在作品内登记并恢复素材`);
  return asset;
}
