const stops = [
  {position: 0, rgb: [41, 46, 66]},
  {position: .28, rgb: [24, 28, 40]},
  {position: .49, rgb: [14, 17, 28]},
  {position: .78, rgb: [9, 12, 19]},
];
const dithering = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];

// 写入固定的原尺寸背景像素，避免 Chromium 重新分配渐变图层时改变抖动网格。
export function paintStageBackdrop(canvas: HTMLCanvasElement) {
  const {width, height} = canvas;
  const context = canvas.getContext('2d', {alpha: false});
  if (!context) throw new Error('无法绘制发布会舞台背景');
  const image = context.createImageData(width, height);
  const horizontal = Array.from({length: width}, (_, x) => ((x / width - .67) / .67) ** 2);
  let offset = 0;
  for (let y = 0; y < height; y++) {
    const vertical = ((y / height - .32) / .68) ** 2;
    for (let x = 0; x < width; x++, offset += 4) {
      const position = Math.min(.78, Math.sqrt((horizontal[x] + vertical) / 2));
      const end = position <= .28 ? 1 : position <= .49 ? 2 : 3;
      const from = stops[end - 1], to = stops[end];
      const progress = (position - from.position) / (to.position - from.position);
      const dither = (dithering[(y % 4) * 4 + x % 4] + .5) / 16;
      for (let channel = 0; channel < 3; channel++) {
        image.data[offset + channel] = Math.floor(from.rgb[channel] + (to.rgb[channel] - from.rgb[channel]) * progress + dither);
      }
      image.data[offset + 3] = 255;
    }
  }
  context.putImageData(image, 0, 0);
}
