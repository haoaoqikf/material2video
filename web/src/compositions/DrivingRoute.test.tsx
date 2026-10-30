import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  DrivingRoute, buildRouteModel, cameraForFrame, displayDistanceMeters, distanceForFrame, fitCamera,
  formatDistance, headingAtDistance, highwayLabels, pointAtDistance, projectPoint, roadLabelKey,
  toScreen, type DrivingRouteProps,
} from './DrivingRoute';

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
  schemaVersion: 1,
  durationInFrames: 1800,
  fps: 60,
  width: 1920,
  height: 1080,
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
const render = (frame: number) => {
  frameState.value = frame;
  return renderToStaticMarkup(<DrivingRoute {...props} />);
};
const attribute = (markup: string, name: string) => markup.match(new RegExp(`${name}="([^"]+)"`, 'u'))?.[1] ?? '';

describe('route geometry', () => {
  it('removes consecutive duplicate points and keeps road spans in order', () => {
    const duplicate = buildRouteModel([
      {road: '沪蓉高速', points: [[121.47, 31.23], [121.47, 31.23], [121.48, 31.24]]},
      {road: '城市道路', points: [[121.48, 31.24], [121.48, 31.24], [121.49, 31.25]]},
    ]);
    expect(duplicate.coordinates).toEqual([[121.47, 31.23], [121.48, 31.24], [121.49, 31.25]]);
    expect(duplicate.spans.map((span) => span.road)).toEqual(['沪蓉高速', '城市道路']);
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
    expect(pointAtDistance(model, 0)).toMatchObject(model.projected[0]);
    expect(pointAtDistance(model, model.lengthMeters)).toMatchObject(model.projected[model.projected.length - 1]);
  });

  it('averages headings over the route window and never returns NaN', () => {
    for (const distance of [0, 1, model.lengthMeters / 2, model.lengthMeters]) {
      const heading = headingAtDistance(model, distance);
      expect(Number.isFinite(heading)).toBe(true);
      expect(heading).toBeGreaterThanOrEqual(-Math.PI);
      expect(heading).toBeLessThanOrEqual(Math.PI);
    }
    const reversed = buildRouteModel([
      {road: '合成高速', points: [[121.5, 31.26], [121.48, 31.24], [121.47, 31.23]]},
    ]);
    expect(headingAtDistance(reversed, reversed.lengthMeters / 2)).not.toBeCloseTo(
      headingAtDistance(model, model.lengthMeters / 2), 2);
  });

  it('formats only API distance for display', () => {
    expect(formatDistance(5000)).toBe('5.0 公里');
    expect(formatDistance(950_000)).toBe('950 公里');
    expect(displayDistanceMeters(0, model.lengthMeters, 5000)).toBe(0);
    expect(displayDistanceMeters(model.lengthMeters, model.lengthMeters, 5000)).toBe(5000);
    expect(displayDistanceMeters(1234, model.lengthMeters, 5000)).toBeCloseTo(
      5000 * (1234 / model.lengthMeters), 6);
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

  it('advances monotonically through the driving segment', () => {
    let previous = -1;
    for (let frame = 180; frame <= 1619; frame += 37) {
      const value = distanceForFrame(frame, 1800, 60, model.lengthMeters);
      expect(value).toBeGreaterThanOrEqual(previous);
      previous = value;
    }
  });

  it('opens and closes on the full route and follows at 2.5x', () => {
    const full = fitCamera(model.bounds, 1920, 1080, 130);
    expect(cameraForFrame(model, 0, 1800, 60, 1920, 1080).scale).toBeCloseTo(full.scale, 9);
    expect(cameraForFrame(model, 1799, 1800, 60, 1920, 1080).scale).toBeCloseTo(full.scale, 9);
    expect(cameraForFrame(model, 900, 1800, 60, 1920, 1080).scale).toBeCloseTo(full.scale * 2.5, 6);
    expect(cameraForFrame(model, 120, 1800, 60, 1920, 1080).scale).toBeCloseTo(full.scale, 9);
  });

  it('transitions continuously into and out of the follow camera', () => {
    const enter = [cameraForFrame(model, 239, 1800, 60, 1920, 1080), cameraForFrame(model, 240, 1800, 60, 1920, 1080)];
    const leave = [cameraForFrame(model, 1739, 1800, 60, 1920, 1080), cameraForFrame(model, 1740, 1800, 60, 1920, 1080)];
    for (const pair of [enter, leave]) {
      expect(Math.abs(pair[1].scale - pair[0].scale) / pair[0].scale).toBeLessThan(0.01);
    }
  });

  it('is a pure function of the frame, independent of evaluation order', () => {
    const first = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 60, 1920, 1080)};
    pointAtDistance(model, 0);
    cameraForFrame(model, 1799, 1800, 60, 1920, 1080);
    const again = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 60, 1920, 1080)};
    expect(again).toEqual(first);
  });

  it('keeps the vehicle visible on very short routes', () => {
    const short = buildRouteModel([{road: '短高速', points: [[121.47, 31.23], [121.4702, 31.23]]}]);
    for (const frame of [240, 900, 1500]) {
      const camera = cameraForFrame(short, frame, 1800, 60, 1920, 1080);
      const position = toScreen(camera, pointAtDistance(
        short, distanceForFrame(frame, 1800, 60, short.lengthMeters)));
      expect(position.x).toBeGreaterThan(0);
      expect(position.x).toBeLessThan(1920);
      expect(position.y).toBeGreaterThan(0);
      expect(position.y).toBeLessThan(1080);
    }
  });
});

describe('labels', () => {
  it('merges consecutive highway segments and excludes ordinary roads', () => {
    const labels = highwayLabels(model);
    expect(labels).toHaveLength(2);
    expect(labels.every((label) => label.road === '沪蓉高速')).toBe(true);
    expect(labels[0].distance).toBeLessThan(labels[1].distance);
    const ordinary = buildRouteModel([
      {road: '城市道路', points: [[121.47, 31.23], [121.48, 31.24]]},
    ]);
    expect(highwayLabels(ordinary)).toEqual([]);
  });

  it('projects with north up', () => {
    const north = projectPoint([121.47, 31.24]);
    const south = projectPoint([121.47, 31.23]);
    expect(north.y).toBeLessThan(south.y);
  });

  it('creates unique keys for repeated labels on a north-south highway', () => {
    const northSouth = buildRouteModel([
      {road: '京港澳高速', points: [[121.47, 31.2], [121.47, 31.24], [121.47, 31.28]]},
    ]);
    const labels = highwayLabels(northSouth);
    expect(labels.length).toBe(2);
    expect(new Set(labels.map(roadLabelKey)).size).toBe(labels.length);
  });
});

describe('composition markup', () => {
  it('shows both endpoints and the start position during the opening', () => {
    const markup = render(0);
    expect(markup).toContain('data-m2v-driving="route"');
    expect(markup).toContain('data-m2v-origin-label="true"');
    expect(markup).toContain('data-m2v-destination-label="true"');
    expect(markup).toContain('上海');
    expect(markup).toContain('郑州');
    expect(markup).toContain('地图数据 © 高德地图（合成测试）');
    expect(markup).toContain('M2V Inter');
    expect(markup).toContain('M2V Sans');
    expect(markup).not.toContain('Noto Sans SC');
    expect(Number(attribute(markup, 'data-m2v-distance'))).toBe(0);
    expect(markup).not.toContain('data-m2v-walked="true"');
  });

  it('draws the full walked route and stops at the destination at the end', () => {
    const markup = render(1799);
    expect(markup).toContain('data-m2v-walked="true"');
    expect(Number(attribute(markup, 'data-m2v-distance'))).toBeCloseTo(model.lengthMeters, 1);
    expect(Number(attribute(markup, 'data-m2v-traveled'))).toBeCloseTo(5000, 1);
    expect(markup).toContain('已行驶 5.0 公里 · 全程 5.0 公里');
    expect(Number(attribute(markup, 'data-m2v-x'))).toBeCloseTo(
      model.projected[model.projected.length - 1].x * fitCamera(model.bounds, 1920, 1080, 130).scale
      + fitCamera(model.bounds, 1920, 1080, 130).tx, 0);
  });

  it('hides endpoint labels that would be clipped while following', () => {
    const markup = render(1500);
    expect(markup).not.toContain('data-m2v-origin="true"');
  });

  it('zooms in while following road labels stay readable', () => {
    const markup = render(1000);
    const scale = Number(attribute(markup, 'data-m2v-scale'));
    expect(scale).toBeGreaterThan(fitCamera(model.bounds, 1920, 1080, 130).scale * 2);
    expect(markup).toContain('data-m2v-road-label="沪蓉高速"');
  });

  it('produces identical markup for the same frame', () => {
    expect(render(900)).toBe(render(900));
  });
});
