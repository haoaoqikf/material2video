/**
 * Node 侧的逐帧渲染与编码。
 *
 * 这一层只做两件事：把 composition 的真实元数据报出来，以及把它渲染成无声 MP4。
 * 分镜校验、路径归属、配音与字幕、成片验收、交付权限都在 Python 侧——
 * 两边以 stdout 上的**带前缀的 JSON 行**通信，不靠退出码猜原因。
 *
 * 为什么要先把画面报出来再渲：`durationInFrames` / `fps` / 尺寸在 React 侧是由
 * `calculateMetadata` 从分镜 props 推导的，也就是说「画面声明的时长」与
 * 「分镜累计的时长」是两份可能不一致的数据。渲染入口拿这条元数据与分镜交叉校验，
 * 不一致就终止——而不是渲出一支长度不对的片子再让人去发现。
 *
 * 用法（bundle 由 `remotion bundle` 先构建好，因此这里不需要打包配置）：
 *
 * ```
 * node scripts/remotion-render.mjs --bundle <目录> --props <分镜> [--out <mp4>]
 *   [--crf 18] [--preset medium] [--frames 0-29] [--metadata-only]
 * ```
 */

import fs from 'node:fs';
import process from 'node:process';
import { renderMedia, selectComposition } from '@remotion/renderer';

/** Python 侧按前缀取行，因此打包器与 Remotion 自己的日志都不影响解析。 */
const METADATA_PREFIX = '__A2V_COMPOSITION__';
const PROGRESS_PREFIX = '__A2V_PROGRESS__';

const COMPOSITION_ID = 'A2V';

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      throw new Error(`无法识别的参数: ${token}`);
    }
    const name = token.slice(2);
    if (name === 'metadata-only') {
      parsed.metadataOnly = true;
      continue;
    }
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) {
      throw new Error(`参数 --${name} 缺少取值`);
    }
    parsed[name] = value;
    i += 1;
  }
  return parsed;
}

function parseFrameRange(text) {
  if (!text) {
    return null;
  }
  const match = /^(\d+)-(\d+)$/.exec(text);
  if (!match) {
    throw new Error(`--frames 需要 start-end 形式，收到 ${text}`);
  }
  return [Number(match[1]), Number(match[2])];
}

const args = parseArgs(process.argv.slice(2));

if (!args.bundle || !args.props) {
  process.stderr.write('remotion-render: 需要 --bundle 与 --props\n');
  process.exit(2);
}
if (!args.metadataOnly && !args.out) {
  process.stderr.write('remotion-render: 渲染模式需要 --out\n');
  process.exit(2);
}

const inputProps = JSON.parse(fs.readFileSync(args.props, 'utf8'));

const composition = await selectComposition({
  serveUrl: args.bundle,
  id: COMPOSITION_ID,
  inputProps,
  logLevel: 'error',
});

// 元数据先落一行：Python 会在开始渲染之前就完成交叉校验
process.stdout.write(
  `${METADATA_PREFIX}${JSON.stringify({
    id: composition.id,
    fps: composition.fps,
    width: composition.width,
    height: composition.height,
    durationInFrames: composition.durationInFrames,
  })}\n`,
);

if (!args.metadataOnly) {
  let lastReported = -1;
  await renderMedia({
    composition,
    serveUrl: args.bundle,
    codec: 'h264',
    outputLocation: args.out,
    inputProps,
    crf: args.crf ? Number(args.crf) : 18,
    // 编码参数在这里定死，Python 侧的验收会逐项复核：色彩空间与像素格式
    // 决定成片能不能被播放器按 BT.709 正确解出颜色，不是可调的风格选项。
    pixelFormat: 'yuv420p',
    colorSpace: 'bt709',
    x264Preset: args.preset ?? 'medium',
    // 中间帧用 JPEG：1080×1920 下单帧 JPEG 约 66ms、PNG 约 225ms，
    // 而 q98 对文字画面几乎无可感损失
    imageFormat: 'jpeg',
    jpegQuality: 98,
    // 竖屏 1080×1920 + 大字库在 Windows Chromium 下并发页签会显著抬高峰值内存，
    // 长片可能被系统关闭并报 Target closed。单并发牺牲吞吐，换取确定的资源上限。
    concurrency: 1,
    frameRange: parseFrameRange(args.frames),
    overwrite: true,
    logLevel: 'error',
    onProgress: ({ progress }) => {
      const percent = Math.floor(progress * 100);
      if (percent >= lastReported + 10) {
        lastReported = percent;
        process.stdout.write(`${PROGRESS_PREFIX}${percent}\n`);
      }
    },
  });
}
