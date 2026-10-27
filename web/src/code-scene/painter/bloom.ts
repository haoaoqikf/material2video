/**
 * 出帧管线：底 → 内容层 → 辉光 → 颗粒。
 *
 * 辉光做法是缩小两次、模糊、加法叠回：内容画在一张透明层上，越亮的东西光晕
 * 越大。这也是为什么大面积实心色块会糊成一片——需要看清结构的物体应画进
 * `under`（底之上、内容之下），不参加辉光累加。
 *
 * 全部步骤只由本帧的绘制内容决定，不读挂钟或随机数。
 */

export type BloomOptions = {
  /** 辉光强度；0 关闭。 */
  bloom?: number;
  /** 胶片颗粒强度；0 关闭。 */
  grain?: number;
  /** 颗粒的固定种子，同一镜头内保持相同。 */
  seed?: number;
};

const GRAIN_TILES = 6;
const GRAIN_WIDTH = 480;
const GRAIN_HEIGHT = 270;

/** 预生成几张固定噪声，按帧号轮换；不依赖 `Math.random`。 */
const grainTiles = new Map<number, HTMLCanvasElement>();

function hash(value: number): number {
  const x = Math.sin(value * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function grainTile(seed: number): HTMLCanvasElement {
  const cached = grainTiles.get(seed);
  if (cached) return cached;
  const canvas = document.createElement('canvas');
  canvas.width = GRAIN_WIDTH;
  canvas.height = GRAIN_HEIGHT;
  const ctx = canvas.getContext('2d')!;
  const image = ctx.createImageData(GRAIN_WIDTH, GRAIN_HEIGHT);
  for (let index = 0; index < image.data.length; index += 4) {
    const value = 128 + (hash(seed + index) - .5) * 220;
    image.data[index] = image.data[index + 1] = image.data[index + 2] = value;
    image.data[index + 3] = 255;
  }
  ctx.putImageData(image, 0, 0);
  grainTiles.set(seed, canvas);
  return canvas;
}

export type ComposeOptions = BloomOptions & {
  width: number;
  height: number;
  /** 逻辑坐标对设备像素的倍数；与画布后备缓冲一致。 */
  scale?: number;
  /** 已画好的底；为 `null` 时只铺黑。 */
  background?: HTMLCanvasElement | null;
  /** 已画好的底层内容（不参加辉光）；为 `null` 时跳过。 */
  under?: HTMLCanvasElement | null;
  /** 已画好的内容层，参与辉光。 */
  content: HTMLCanvasElement;
  /** 画在辉光之后、颗粒之前的锐利层：需要保持锐利的文字与细线。 */
  overlay?: HTMLCanvasElement | null;
  /** 出帧后的全幅效果，例如闪白或染色。 */
  post?: HTMLCanvasElement | null;
  /** 帧号，用于颗粒轮换。 */
  frame: number;
};

/**
 * 把一帧合成到 `target` 上。
 *
 * 各层由调用方各自画在自己的画布上再传进来：这样绘制只发生一次，量测清单和
 * 像素都由同一次绘制产出，不会出现「量测按第一遍、画面按第二遍」的错位。
 */
export function compose(target: HTMLCanvasElement, options: ComposeOptions): void {
  const {width, height} = options;
  const output = target.getContext('2d')!;
  output.setTransform(1, 0, 0, 1, 0, 0);
  output.globalAlpha = 1;
  output.globalCompositeOperation = 'source-over';
  output.filter = 'none';
  output.fillStyle = '#000000';
  output.fillRect(0, 0, target.width, target.height);
  if (options.background) output.drawImage(options.background, 0, 0, target.width, target.height);
  if (options.under) output.drawImage(options.under, 0, 0, target.width, target.height);
  const layer = options.content;
  output.drawImage(layer, 0, 0, target.width, target.height);

  const bloom = options.bloom ?? 1;
  if (bloom > 0) {
    const small = document.createElement('canvas');
    small.width = Math.max(1, Math.round(width * (options.scale ?? 1) / 4));
    small.height = Math.max(1, Math.round(height * (options.scale ?? 1) / 4));
    const dim = small.getContext('2d')!;
    // 两档半径：近处收紧轮廓，远处铺开大范围柔光。
    for (const [blur, alpha] of [[3, .42], [11, .34]] as const) {
      dim.setTransform(1, 0, 0, 1, 0, 0);
      dim.clearRect(0, 0, small.width, small.height);
      dim.filter = `blur(${blur}px)`;
      dim.drawImage(layer, 0, 0, small.width, small.height);
      dim.filter = 'none';
      output.save();
      output.globalCompositeOperation = 'lighter';
      output.globalAlpha = alpha * bloom;
      output.drawImage(small, 0, 0, target.width, target.height);
      output.restore();
    }
  }
  if (options.post) output.drawImage(options.post, 0, 0, target.width, target.height);
  // 锐利层画在最上面：文字进辉光会被自己的光晕冲出重影，也不该被全幅后期染色。
  if (options.overlay) output.drawImage(options.overlay, 0, 0, target.width, target.height);
  const grain = options.grain ?? 0;
  if (grain > 0) {
    const tile = grainTile(options.seed ?? 20261006);
    // 帧号轮换的是同一组固定瓦片的位置偏移，不引入随机。
    const offset = (options.frame * 37) % GRAIN_TILES;
    const shift = {x: offset * GRAIN_TILES, y: offset * 3};
    output.save();
    output.globalCompositeOperation = 'overlay';
    output.globalAlpha = Math.min(1, grain);
    output.imageSmoothingEnabled = true;
    const pattern = output.createPattern(tile, 'repeat');
    if (pattern) {
      pattern.setTransform(new DOMMatrix([target.width / GRAIN_WIDTH, 0, 0,
        target.height / GRAIN_HEIGHT, shift.x, shift.y]));
      output.fillStyle = pattern;
      output.fillRect(0, 0, target.width, target.height);
    }
    output.restore();
  }
}
