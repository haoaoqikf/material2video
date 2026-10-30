import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  DrivingRoute, basemapBlend, buildRouteModel, cameraForFrame, displayDistanceMeters,
  distanceForFrame, fitCameraInContent, formatDistance, headingAtDistance, highwayLabels,
  pointAtDistance, projectPoint, type DrivingRouteProps,
} from './DrivingRoute';
import { contentRect } from './driving/layout';
import { estimateTextWidth, placeDistancePill, truncateText } from './driving/labels';

const frameState = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return {
    ...actual,
    AbsoluteFill: ({ children, ...rest }: React.ComponentProps<'div'>) => <div {...rest}>{children}</div>,
    useCurrentFrame: () => frameState.value,
  };
});

const props: DrivingRouteProps = {
  schemaVersion: 2,
  durationInFrames: 1800,
  fps: 60,
  width: 1080,
  height: 1920,
  originLabel: '上海',
  destinationLabel: '郑州',
  origin: [121.47, 31.23],
  destination: [121.5, 31.26],
  routeStart: [121.47, 31.23],
  routeEnd: [121.5, 31.26],
  totalDistanceMeters: 5000,
  attribution: '地图数据 © 高德地图（合成测试）',
  steps: [
    {road: '沪蓉高速', points: [[121.47, 31.23], [121.48, 31.24], [121.49, 31.25]]},
    {road: '沪蓉高速', points: [[121.49, 31.25], [121.5, 31.26]]},
  ],
};

const model = buildRouteModel(props.steps);
const renderProps = (frame: number, value: DrivingRouteProps) => {
  frameState.value = frame;
  return renderToStaticMarkup(<DrivingRoute {...value} />);
};
const render = (frame: number) => renderProps(frame, props);
const attribute = (markup: string, name: string) => markup.match(new RegExp(`${name}="([^"]+)"`, 'u'))?.[1] ?? '';

describe('route geometry', () => {
  it('removes consecutive duplicate points and keeps road spans in order', () => {
    const duplicate = buildRouteModel([
      {road: '沪蓉高速', points: [[121.47, 31.23], [121.47, 31.23], [121.48, 31.24]]},
      {road: '城市道路', points: [[121.48, 31.24], [121.48, 31.24], [121.49, 31.25]]},
    ]);
    expect(duplicate.coordinates).toEqual([[121.47, 31.23], [121.48, 31.24], [121.49, 31.25]]);
    expect(duplicate.spans.map((span) => span.road)).toEqual(['沪蓉高速', '城市道路']);
    expect(duplicate.projectedLength).toBeGreaterThan(0);
  });

  it('keeps the vehicle on the polyline at every sampled distance', () => {
    for (const fraction of [0, 0.02, 0.33, 0.5, 0.77, 1]) {
      const point = pointAtDistance(model, model.lengthMeters * fraction);
      const nearest = Math.min(...model.projected.slice(1).map((end, index) => {
        const start = model.projected[index];
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const lengthSquared = dx * dx + dy * dy;
        const t = lengthSquared === 0 ? 0
          : Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared));
        return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
      }));
      expect(nearest).toBeLessThan(1e-6);
    }
  });

  it('averages headings over the route window and never returns NaN', () => {
    for (const distance of [0, 1, model.lengthMeters / 2, model.lengthMeters]) {
      const heading = headingAtDistance(model, distance);
      expect(Number.isFinite(heading)).toBe(true);
      expect(heading).toBeGreaterThanOrEqual(-Math.PI);
      expect(heading).toBeLessThanOrEqual(Math.PI);
    }
  });

  it('formats only API distance for display', () => {
    expect(formatDistance(5000)).toBe('5.0 公里');
    expect(formatDistance(950_000)).toBe('950 公里');
    expect(displayDistanceMeters(0, model.lengthMeters, 5000)).toBe(0);
    expect(displayDistanceMeters(model.lengthMeters, model.lengthMeters, 5000)).toBe(5000);
  });
});

describe('timeline and camera', () => {
  it('stays at the start during the opening and reaches the end by the last driving frame', () => {
    expect(distanceForFrame(0, 1800, 60, model.lengthMeters)).toBe(0);
    expect(distanceForFrame(179, 1800, 60, model.lengthMeters)).toBe(0);
    expect(distanceForFrame(1619, 1800, 60, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(1799, 1800, 60, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(180, 1800, 60, model.lengthMeters)).toBeGreaterThan(0);
  });

  it('supports a one-minute timeline', () => {
    expect(distanceForFrame(3419, 3600, 60, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(180, 3600, 60, model.lengthMeters)).toBeGreaterThan(0);
  });

  it('opens close at the origin, follows at 6x and ends on the full route', () => {
    const full = fitCameraInContent(model.bounds, 1080, 1920);
    expect(cameraForFrame(model, 0, 1800, 60, 1080, 1920).scale).toBeCloseTo(full.scale * 5, 6);
    expect(cameraForFrame(model, 179, 1800, 60, 1080, 1920).scale).toBeCloseTo(full.scale * 6, 6);
    expect(cameraForFrame(model, 900, 1800, 60, 1080, 1920).scale).toBeCloseTo(full.scale * 6, 6);
    expect(cameraForFrame(model, 1799, 1800, 60, 1080, 1920).scale).toBeCloseTo(full.scale, 9);
  });

  it('keeps the opening zoom monotonic and transitions smoothly', () => {
    const start = cameraForFrame(model, 0, 1800, 60, 1080, 1920).scale;
    const end = cameraForFrame(model, 179, 1800, 60, 1080, 1920).scale;
    let previous = start - 1;
    for (let frame = 0; frame <= 179; frame += 17) {
      const scale = cameraForFrame(model, frame, 1800, 60, 1080, 1920).scale;
      expect(scale).toBeGreaterThanOrEqual(previous);
      previous = scale;
    }
    expect(end).toBeGreaterThan(start);
    for (const [a, b] of [[179, 180], [239, 240], [1619, 1620], [1739, 1740]]) {
      const first = cameraForFrame(model, a, 1800, 60, 1080, 1920).scale;
      const second = cameraForFrame(model, b, 1800, 60, 1080, 1920).scale;
      expect(Math.abs(second - first) / first).toBeLessThan(0.03);
    }
  });

  it('fits the full route inside the content area below the title', () => {
    const content = contentRect(1080, 1920);
    const camera = cameraForFrame(model, 1799, 1800, 60, 1080, 1920);
    for (const point of model.projected) {
      const screen = {x: point.x * camera.scale + camera.tx, y: point.y * camera.scale + camera.ty};
      expect(screen.x).toBeGreaterThanOrEqual(content.innerLeft - 0.01);
      expect(screen.x).toBeLessThanOrEqual(content.innerRight + 0.01);
      expect(screen.y).toBeGreaterThanOrEqual(content.innerTop - 0.01);
      expect(screen.y).toBeLessThanOrEqual(content.innerBottom + 0.01);
    }
  });

  it('keeps the vehicle visible on very short routes', () => {
    const short = buildRouteModel([{road: '短高速', points: [[121.47, 31.23], [121.4702, 31.23]]}]);
    for (const frame of [0, 240, 900, 1500]) {
      const camera = cameraForFrame(short, frame, 1800, 60, 1080, 1920);
      const position = pointAtDistance(short, distanceForFrame(frame, 1800, 60, short.lengthMeters));
      const screen = {x: position.x * camera.scale + camera.tx, y: position.y * camera.scale + camera.ty};
      expect(screen.x).toBeGreaterThan(0);
      expect(screen.x).toBeLessThan(1080);
      expect(screen.y).toBeGreaterThan(0);
      expect(screen.y).toBeLessThan(1920);
    }
  });

  it('is a pure function of the frame, independent of evaluation order', () => {
    const first = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 60, 1080, 1920)};
    pointAtDistance(model, 0);
    cameraForFrame(model, 1799, 1800, 60, 1080, 1920);
    const again = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 60, 1080, 1920)};
    expect(again).toEqual(first);
  });
});

describe('labels and basemap blend', () => {
  it('merges consecutive highway segments and excludes ordinary roads', () => {
    const labels = highwayLabels(model);
    expect(labels).toHaveLength(2);
    const ordinary = buildRouteModel([{road: '城市道路', points: [[121.47, 31.23], [121.48, 31.24]]}]);
    expect(highwayLabels(ordinary)).toEqual([]);
  });

  it('moves the distance pill away from an occupied endpoint box', () => {
    const obstacle = {left: 500, right: 700, top: 1000, bottom: 1060};
    const pill = placeDistancePill(540, 1085, '已行驶 937 公里', 1080, 1920, 312, [obstacle]);
    const box = {left: pill.cx - pill.width / 2, right: pill.cx + pill.width / 2,
      top: pill.cy - pill.height / 2, bottom: pill.cy + pill.height / 2};
    const overlap = !(box.right < obstacle.left || box.left > obstacle.right
      || box.bottom < obstacle.top || box.top > obstacle.bottom);
    expect(overlap).toBe(false);
  });

  it('truncates long text to the available width', () => {
    const text = truncateText('一个非常长的目的地名称需要被截断', 200, 34);
    expect(estimateTextWidth(text, 34)).toBeLessThanOrEqual(201);
    expect(text.endsWith('…')).toBe(true);
  });

  it('projects with north up and blends the follow layer by camera ratio', () => {
    expect(projectPoint([121.47, 31.24]).y).toBeLessThan(projectPoint([121.47, 31.23]).y);
    expect(basemapBlend(1, 1)).toBe(0);
    expect(basemapBlend(1.5, 1)).toBe(0.5);
    expect(basemapBlend(4, 1)).toBe(1);
  });
});

describe('composition markup', () => {
  it('centers a large two-line title and removes the bottom panel', () => {
    const markup = render(0);
    expect(markup).toContain('data-m2v-title-kicker="true"');
    expect(markup).toContain('data-m2v-title-main="true"');
    expect(markup).toContain('模拟行程');
    expect(markup).toContain('上海 → 郑州');
    expect(markup).toMatch(/data-m2v-title-main="true"[^>]*x="540"[^>]*text-anchor="middle"/u);
    expect(markup).toMatch(/data-m2v-title-main="true"[^>]*font-size="88"/u);
    expect(markup).not.toContain('data-m2v-panel');
    expect(markup).not.toContain('路线规划估算');
    expect(markup).not.toContain('全程');
  });

  it('shows the traveled distance beside the vehicle and no full route at the start', () => {
    const markup = render(0);
    expect(markup).toContain('data-m2v-distance-pill="true"');
    expect(markup).toContain('已行驶 0.0 公里');
    expect(markup).not.toContain('data-m2v-walked="true"');
    expect(markup).toContain('data-m2v-origin-label="true"');
  });

  it('shows the full walked route and traveled total at the end', () => {
    const markup = render(1799);
    expect(markup).toContain('data-m2v-walked="true"');
    expect(markup).toContain('已行驶 5.0 公里');
    expect(Number(attribute(markup, 'data-m2v-traveled'))).toBeCloseTo(5000, 1);
    expect(markup).toContain('data-m2v-origin-label="true"');
    expect(markup).toContain('data-m2v-destination-label="true"');
  });

  it('zooms in while following and draws both basemap layers', () => {
    const layer = (zoom: number) => ({
      zoom,
      bbox: [121.44, 31.2, 121.53, 31.29] as [number, number, number, number],
      image: {path: 'assets/basemap/x.jpg', sha256: 'a'.repeat(64), width: 256, height: 256},
      projected: {left: 13_500_000, top: -3_660_000, width: 200_000, height: 200_000},
      tileCount: 4,
      dataUri: 'data:image/jpeg;base64,/9j/4AAQSkZJRg==',
    });
    const basemap = {
      provider: 'amap',
      service: 'road-tiles',
      attribution: '地图数据 © 高德地图',
      fetchedAt: '2026-10-30T13:00:00+08:00',
      overview: layer(8),
      follow: layer(9),
    };
    const markup = renderProps(900, {...props, basemap});
    const full = fitCameraInContent(model.bounds, 1080, 1920);
    expect(Number(attribute(markup, 'data-m2v-scale'))).toBeCloseTo(full.scale * 6, 5);
    expect(markup).toContain('data-m2v-basemap="overview"');
    expect(markup).toContain('data-m2v-basemap="follow"');
    expect(markup).toContain('data:image/jpeg;base64');
  });

  it('draws city names at their route locations', () => {
    const markup = renderProps(0, {
      ...props,
      cities: [
        {name: '上海城区', adcode: '310100', location: [121.47, 31.23]},
        {name: '苏州市', adcode: '320500', location: [121.472, 31.232]},
        {name: '郑州市', adcode: '410100', location: [121.5, 31.26]},
      ],
    });
    expect(markup).toContain('data-m2v-city-label="苏州市"');
    expect(markup).not.toContain('data-m2v-city-label="上海城区"');
    expect(markup).not.toContain('data-m2v-city-label="郑州市"');
  });

  it('produces identical markup for the same frame', () => {
    expect(render(900)).toBe(render(900));
  });
});
