/**
 * Node 侧的逐帧渲染与编码。
 *
 * 这一层只做三件事：把 composition 的真实元数据报出来、按 Python 的确认渲染成
 * 无声 MP4、以及导出未编码的中间帧（只有基准与跨并发一致性验收会用）。
 * 分镜校验、路径归属、配音与字幕、成片验收、交付权限都在 Python 侧——
 * 两边以 stdout 上的**带前缀的 JSON 行**通信，不靠退出码猜原因。
 *
 * 为什么要先把画面报出来再渲：`durationInFrames` / `fps` / 尺寸在 React 侧是由
 * `calculateMetadata` 从分镜 props 推导的，也就是说「画面声明的时长」与
 * 「分镜累计的时长」是两份可能不一致的数据。渲染入口拿这条元数据与分镜交叉校验，
 * 不一致就终止——而不是渲出一支长度不对的片子再让人去发现。
 *
 * 会话模式（`--session`）：只开**一个**浏览器，选完 composition 报出元数据后
 * 停在原地等 Python 的确认行；确认里才带渲染参数。拒绝（`ABORT`）或父进程
 * EOF 时直接退出，不渲染任何一帧。
 *
 * 用法（bundle 由 `remotion bundle` 先构建好，因此这里不需要打包配置）：
 *
 * ```
 * node scripts/remotion-render.mjs --bundle <目录> --props <分镜> [--composition-id <id>]
 *   [--out <mp4>] [--crf 18] [--preset medium] [--frames 0-29] [--concurrency 1]
 *   [--scale 1] [--metadata-only] [--session] [--frames-out <目录>]
 * ```
 */

import fs from 'node:fs';
import process from 'node:process';
import {
  openBrowser,
  renderFrames,
  renderMedia,
  renderStill,
  selectComposition,
} from '@remotion/renderer';

/** Python 侧按前缀取行，因此打包器与 Remotion 自己的日志都不影响解析。 */
const METADATA_PREFIX = '__M2V_COMPOSITION__';
const PROGRESS_PREFIX = '__M2V_PROGRESS__';
const SESSION_PREFIX = '__M2V_SESSION__';
const READY_PREFIX = '__M2V_READY__';
const DONE_PREFIX = '__M2V_DONE__';
const CONFIRM_PREFIX = '__M2V_CONFIRM__';
const ABORT_PREFIX = '__M2V_ABORT__';

const COMPOSITION_ID = 'M2V';

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      throw new Error(`无法识别的参数: ${token}`);
    }
    const name = token.slice(2);
    if (name === 'metadata-only' || name === 'session') {
      parsed[name === 'metadata-only' ? 'metadataOnly' : 'session'] = true;
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

function parseConcurrency(text) {
  if (text === undefined || text === null || text === '') {
    return 1;
  }
  const value = Number(text);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`--concurrency 必须是正整数，收到 ${text}`);
  }
  return value;
}

/**
 * 等待父进程的确认行。
 *
 * 三种结束方式都要能收场：收到 `CONFIRM` 返回参数、收到 `ABORT` 返回 null、
 * stdin 关闭（父进程没了）返回 null——父进程一死就绝不能继续渲染。
 */
function waitForConfirmation() {
  return new Promise((resolve) => {
    let buffer = '';
    const finish = (value) => {
      process.stdin.off('data', onData);
      process.stdin.off('end', onEnd);
      process.stdin.off('close', onEnd);
      // 收完确认行必须把 stdin 交还：`on('data')` 会让 stdin 进入 flowing 模式，
      // 即使监听器已移除，这个句柄仍会让 Node 在渲染结束后永不退出——
      // 父进程等不到 EOF，一次正常的渲染就会被记成超时。
      process.stdin.pause();
      if (typeof process.stdin.unref === 'function') {
        process.stdin.unref();
      }
      resolve(value);
    };
    const onData = (chunk) => {
      buffer += chunk.toString('utf8');
      let index = buffer.indexOf('\n');
      while (index >= 0) {
        const line = buffer.slice(0, index);
        buffer = buffer.slice(index + 1);
        if (line.startsWith(CONFIRM_PREFIX)) {
          try {
            finish(JSON.parse(line.slice(CONFIRM_PREFIX.length)));
          } catch (error) {
            process.stderr.write(`remotion-render: 确认行不是合法 JSON: ${error}\n`);
            finish(null);
          }
          return;
        }
        if (line.startsWith(ABORT_PREFIX)) {
          finish(null);
          return;
        }
        index = buffer.indexOf('\n');
      }
    };
    const onEnd = () => finish(null);
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', onData);
    process.stdin.on('end', onEnd);
    process.stdin.on('close', onEnd);
  });
}

function writeLine(prefix, payload) {
  process.stdout.write(`${prefix}${JSON.stringify(payload)}\n`);
}

const args = parseArgs(process.argv.slice(2));
if (args.scale !== undefined && (!Number.isFinite(Number(args.scale)) || Number(args.scale) <= 0)) {
  throw new Error(`--scale 必须是正数，收到 ${args.scale}`);
}
const concurrency = parseConcurrency(args.concurrency);

if (!args.bundle || !args.props) {
  process.stderr.write('remotion-render: 需要 --bundle 与 --props\n');
  process.exit(2);
}
if (!args.metadataOnly && !args.session && !args['frames-out'] && !args.out) {
  process.stderr.write('remotion-render: 渲染模式需要 --out\n');
  process.exit(2);
}

const browserExecutable = process.env.VIDEO_BROWSER_EXECUTABLE;
if (!browserExecutable || !fs.existsSync(browserExecutable)) throw new Error("缺少作品浏览器配置；通过本地scripts/video.py执行，并先setup --install-browser");

const inputProps = JSON.parse(fs.readFileSync(args.props, 'utf8'));
const compositionId = args['composition-id'] ?? COMPOSITION_ID;

/** 元数据先落一行：Python 会在开始渲染之前就完成交叉校验 */
function reportMetadata(composition, browsersOpened) {
  writeLine(METADATA_PREFIX, {
    id: composition.id,
    fps: composition.fps,
    width: composition.width,
    height: composition.height,
    durationInFrames: composition.durationInFrames,
    browsersOpened,
  });
}

function reportProgressFactory() {
  let lastReported = -1;
  return ({ progress }) => {
    const percent = Math.floor(progress * 100);
    if (percent >= lastReported + 10) {
      lastReported = percent;
      process.stdout.write(`${PROGRESS_PREFIX}${percent}\n`);
    }
  };
}

/** 编码参数在这里定死，Python 侧的验收会逐项复核。 */
function mediaOptions(composition, outputLocation, params) {
  return {
    composition,
    // 已构建好的 bundle 路径：会话里浏览器已就绪，这里只是让渲染器知道去哪取画面
    serveUrl: args.bundle,
    browserExecutable,
    codec: 'h264',
    outputLocation,
    inputProps,
    crf: params.crf !== undefined ? Number(params.crf) : 18,
    // 色彩空间与像素格式决定成片能不能被播放器按 BT.709 正确解出颜色，
    // 不是可调的风格选项。
    pixelFormat: 'yuv420p',
    colorSpace: 'bt709',
    x264Preset: params.preset ?? 'medium',
    // 中间帧用 JPEG：1080×1920 下单帧 JPEG 约 66ms、PNG 约 225ms，
    // 而 q98 对文字画面几乎无可感损失
    imageFormat: 'jpeg',
    jpegQuality: 98,
    // 并发由 Python 显式给出，默认 1：竖屏 1080×1920 + 大字库在 Windows
    // Chromium 下并发页签会显著抬高峰值内存，长片可能被系统关闭并报
    // Target closed。
    concurrency: params.concurrency !== undefined ? parseConcurrency(String(params.concurrency)) : 1,
    frameRange: parseFrameRange(params.frames),
    scale: params.scale !== undefined ? Number(params.scale) : 1,
    overwrite: true,
    logLevel: 'error',
    onProgress: reportProgressFactory(),
  };
}

if (args.session) {
  let browser = null;
  let browsersOpened = 0;
  try {
    browser = await openBrowser('chrome', { logLevel: 'error', browserExecutable });
    browsersOpened = 1;
    writeLine(SESSION_PREFIX, { browsersOpened, compositionId });
    const composition = await selectComposition({
      serveUrl: args.bundle,
      id: compositionId,
      inputProps,
      puppeteerInstance: browser,
      logLevel: 'error',
    });
    reportMetadata(composition, browsersOpened);
    process.stdout.write(`${READY_PREFIX}\n`);

    const params = await waitForConfirmation();
    if (!params) {
      process.stderr.write('remotion-render: 未获得渲染确认，会话终止\n');
      await browser.close({ silent: true });
      browser = null;
      process.exit(3);
    }
    if (!params.out) {
      process.stderr.write('remotion-render: 确认行缺少 out\n');
      await browser.close({ silent: true });
      browser = null;
      process.exit(2);
    }
    await renderMedia({
      ...mediaOptions(composition, params.out, params),
      // 同一个浏览器既用于选择 composition 也用于渲染：冷启动只付一次
      puppeteerInstance: browser,
    });
    writeLine(DONE_PREFIX, { frames: composition.durationInFrames, browsersOpened });
  } finally {
    if (browser) {
      await browser.close({ silent: true });
    }
  }
} else if (args['frames-out']) {
  // 未编码中间帧（JPEG q98）：跨并发一致性验收比较的就是这一层，
  // 因此它必须能在不编码的前提下单独导出。
  const outputDir = args['frames-out'];
  fs.mkdirSync(outputDir, { recursive: true });
  let browser = null;
  let browsersOpened = 0;
  try {
    browser = await openBrowser('chrome', { logLevel: 'error', browserExecutable });
    browsersOpened = 1;
    const composition = await selectComposition({
      serveUrl: args.bundle,
      id: compositionId,
      inputProps,
      puppeteerInstance: browser,
      logLevel: 'error',
    });
    reportMetadata(composition, browsersOpened);
    await renderFrames({
      composition,
      serveUrl: args.bundle,
      inputProps,
      imageFormat: 'jpeg',
      jpegQuality: 98,
      outputDir,
      concurrency,
      frameRange: parseFrameRange(args.frames),
      scale: args.scale ? Number(args.scale) : 1,
      puppeteerInstance: browser,
      // 这两个回调是 renderFrames 的必填项：不关心进度也要给，
      // 否则 Remotion 直接报参数错误。
      onStart: () => {},
      onFrameUpdate: () => {},
      logLevel: 'error',
    });
    writeLine(DONE_PREFIX, { frames: composition.durationInFrames, browsersOpened, outputDir });
  } finally {
    if (browser) {
      await browser.close({ silent: true });
    }
  }
} else {
  const composition = await selectComposition({
    browserExecutable,
    serveUrl: args.bundle,
    id: compositionId,
    inputProps,
    logLevel: 'error',
  });

  reportMetadata(composition, 1);

  if (args['still-frame'] !== undefined) {
    const frame = Number(args['still-frame']);
    if (!Number.isInteger(frame) || frame < 0 || frame >= composition.durationInFrames) {
      throw new Error('--still-frame 超出 composition 帧范围');
    }
    await renderStill({composition, serveUrl: args.bundle, inputProps, browserExecutable,
      output: args.out, frame, scale: args.scale ? Number(args.scale) : 1,
      imageFormat: 'png', overwrite: true, logLevel: 'error'});
  } else if (!args.metadataOnly) {
    await renderMedia(
      mediaOptions(composition, args.out, {
        crf: args.crf,
        preset: args.preset,
        frames: args.frames,
        scale: args.scale,
        concurrency,
      }),
    );
  }
}
