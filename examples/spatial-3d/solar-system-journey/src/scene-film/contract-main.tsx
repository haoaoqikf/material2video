import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ensureFonts } from '@/fonts';
import { installOfflineGuard } from '@/runtime/offline-guard';
import '@/styles/index.css';
import { ExplainerContractApp } from './contract';

// 尽早开始加载字体：`ready()` 会等它，但它不必等到那时才开始
void ensureFonts();
// 运行期隔离：契约页路径对非本地请求先阻断，违规由量测读出并计为失败
installOfflineGuard();

/**
 * 渲染契约页。
 *
 * 职责只有一件：把 composition 挂进一个**可被 Playwright 驱动的页面**，
 * 并暴露 `window.__M2V__`（version 6）。布局量测全部通过它工作。
 *
 * 作品参数是**运行时数据**（`m2v-storyboard` 查询参数传入），
 * 因此一次构建服务任意作品，换作品不需要重建契约页。
 */
const container = document.getElementById('root');
if (!container) {
  throw new Error('契约页缺少 #root 挂载点');
}

createRoot(container).render(
  <StrictMode>
    <ExplainerContractApp />
  </StrictMode>,
);
