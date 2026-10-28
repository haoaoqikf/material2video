/** 凸多边形裁剪：分组矩形可旋转，不能拿轴对齐外框代替真实裁剪区。 */
export type Vertex = {x: number; y: number};

export function area(points: Vertex[]): number {
  return Math.abs(signedArea(points));
}

function signedArea(points: Vertex[]): number {
  return points.reduce((sum, p, i) => {
    const q = points[(i + 1) % points.length];
    return sum + p.x * q.y - q.x * p.y;
  }, 0) / 2;
}

export function intersect(subject: Vertex[], clip: Vertex[]): Vertex[] {
  if (clip.length < 3 || area(clip) < 1e-9) return [];
  let output = subject;
  const direction = signedArea(clip) >= 0 ? 1 : -1;
  for (let i = 0; i < clip.length; i++) {
    const a = clip[i], b = clip[(i + 1) % clip.length];
    const distance = (p: Vertex) => direction * ((b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x));
    const input = output;
    output = [];
    if (!input.length) break;
    let previous = input[input.length - 1], dp = distance(previous);
    for (const point of input) {
      const dc = distance(point);
      if ((dc >= 0) !== (dp >= 0)) {
        const t = dp / (dp - dc);
        output.push({x: previous.x + t * (point.x - previous.x), y: previous.y + t * (point.y - previous.y)});
      }
      if (dc >= 0) output.push(point);
      previous = point;
      dp = dc;
    }
  }
  return output;
}
