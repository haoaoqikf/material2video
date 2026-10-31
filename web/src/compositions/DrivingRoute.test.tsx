import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  DrivingRoute, basemapOpacity, buildRouteModel, buildTileIndex, cameraForFrame,
  displayDistanceMeters, distanceForFrame, fitCameraInContent, formatDistance,
  headingAtDistance, highwayLabels, pointAtDistance, projectPoint, selectVisibleTiles,
  timeline, type DrivingRouteProps,
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
  fps: 30,
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
    expect(distanceForFrame(0, 1800, 30, model.lengthMeters)).toBe(0);
    expect(distanceForFrame(59, 1800, 30, model.lengthMeters)).toBe(0);
    expect(distanceForFrame(1739, 1800, 30, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(1799, 1800, 30, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(60, 1800, 30, model.lengthMeters)).toBeGreaterThan(0);
  });

  it('uses a shared 60-second frame ledger', () => {
    expect(timeline(1800, 30)).toMatchObject({
      openingFrames: 60, transitionFrames: 0, driveFrames: 1680,
      endingFrames: 60, endingHoldFrames: 30, pulloutFrames: 30, endingStart: 1740,
    });
  });

  it('supports a one-minute timeline', () => {
    expect(distanceForFrame(1799, 1800, 30, model.lengthMeters)).toBe(model.lengthMeters);
    expect(distanceForFrame(60, 1800, 30, model.lengthMeters)).toBeGreaterThan(0);
  });

  it('opens close at the origin, follows at 16x and ends on the full route', () => {
    const full = fitCameraInContent(model.bounds, 1080, 1920);
    expect(cameraForFrame(model, 0, 1800, 30, 1080, 1920).scale).toBeCloseTo(full.scale * 9, 6);
    expect(cameraForFrame(model, 59, 1800, 30, 1080, 1920).scale).toBeCloseTo(full.scale * 16, 6);
    expect(cameraForFrame(model, 900, 1800, 30, 1080, 1920).scale).toBeCloseTo(full.scale * 16, 6);
    expect(cameraForFrame(model, 1799, 1800, 30, 1080, 1920).scale).toBeCloseTo(full.scale, 9);
  });

  it('opens with a fast ease-out push', () => {
    const full = fitCameraInContent(model.bounds, 1080, 1920);
    const halfway = cameraForFrame(model, 30, 1800, 30, 1080, 1920).scale;
    expect(halfway).toBeGreaterThan(full.scale * 13.5);
  });

  it('smooths the follow camera enough to keep labels steady', () => {
    const points: [number, number][] = Array.from({length: 120}, (_, index) => [
      121.47 + index * 0.02, 31.23 + (index % 2 ? 0.004 : -0.004),
    ]);
    const zigzag = buildRouteModel([{road: '合成高速', points}]);
    const content = contentRect(1080, 1920);
    const centers = [];
    for (let frame = 75; frame < 1740; frame += 1) {
      const camera = cameraForFrame(zigzag, frame, 1800, 30, 1080, 1920);
      centers.push({x: (content.cx - camera.tx) / camera.scale,
        y: (content.cy - camera.ty) / camera.scale, scale: camera.scale});
    }
    const accelerations: number[] = [];
    for (let index = 1; index < centers.length - 1; index += 1) {
      const dx = centers[index + 1].x - 2 * centers[index].x + centers[index - 1].x;
      const dy = centers[index + 1].y - 2 * centers[index].y + centers[index - 1].y;
      accelerations.push(Math.hypot(dx, dy) * centers[index].scale);
    }
    accelerations.sort((a, b) => a - b);
    expect(accelerations[Math.floor(accelerations.length * 0.95)]).toBeLessThan(0.8);
    expect(Math.max(...accelerations)).toBeLessThan(2);
  });

  it('keeps the opening zoom monotonic and transitions smoothly', () => {
    const start = cameraForFrame(model, 0, 1800, 30, 1080, 1920).scale;
    const end = cameraForFrame(model, 59, 1800, 30, 1080, 1920).scale;
    let previous = start - 1;
    for (let frame = 0; frame <= 59; frame += 6) {
      const scale = cameraForFrame(model, frame, 1800, 30, 1080, 1920).scale;
      expect(scale).toBeGreaterThanOrEqual(previous);
      previous = scale;
    }
    expect(end).toBeGreaterThan(start);
    for (const [a, b] of [[59, 60], [74, 75], [1739, 1740], [1769, 1770]]) {
      const first = cameraForFrame(model, a, 1800, 30, 1080, 1920).scale;
      const second = cameraForFrame(model, b, 1800, 30, 1080, 1920).scale;
      expect(Math.abs(second - first) / first).toBeLessThan(0.03);
    }
  });

  it('fits the full route inside the content area below the title', () => {
    const content = contentRect(1080, 1920);
    const camera = cameraForFrame(model, 1799, 1800, 30, 1080, 1920);
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
    for (const frame of [0, 60, 900, 1799]) {
      const camera = cameraForFrame(short, frame, 1800, 30, 1080, 1920);
      const position = pointAtDistance(short, distanceForFrame(frame, 1800, 30, short.lengthMeters));
      const screen = {x: position.x * camera.scale + camera.tx, y: position.y * camera.scale + camera.ty};
      expect(screen.x).toBeGreaterThan(0);
      expect(screen.x).toBeLessThan(1080);
      expect(screen.y).toBeGreaterThan(0);
      expect(screen.y).toBeLessThan(1920);
    }
  });

  it('is a pure function of the frame, independent of evaluation order', () => {
    const first = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 30, 1080, 1920)};
    pointAtDistance(model, 0);
    cameraForFrame(model, 1799, 1800, 30, 1080, 1920);
    const again = {point: pointAtDistance(model, 1234), heading: headingAtDistance(model, 1234),
      camera: cameraForFrame(model, 900, 1800, 30, 1080, 1920)};
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

  it('projects with north up and fades the follow tiles only during the ending', () => {
    expect(projectPoint([121.47, 31.24]).y).toBeLessThan(projectPoint([121.47, 31.23]).y);
    expect(basemapOpacity(0, 1800, 30)).toBe(1);
    expect(basemapOpacity(1739, 1800, 30)).toBe(1);
    expect(basemapOpacity(1740, 1800, 30)).toBeLessThan(1);
    expect(basemapOpacity(1769, 1800, 30)).toBe(0);
    expect(basemapOpacity(1799, 1800, 30)).toBe(0);
  });

  it('selects only tiles intersecting the current camera viewport', () => {
    const size = (2 * Math.PI * 6378137) / 2048;
    const offset = Math.PI * 6378137;
    const projected = (x: number, y: number) => ({
      left: -offset + x * size, top: -offset + y * size, width: size, height: size,
    });
    const tile = (x: number, y: number) => ({
      x, y, z: 11, projected: projected(x, y), dataUri: 'data:image/jpeg;base64,/9j/',
    });
    const index = buildTileIndex([
      tile(0, 0), tile(1, 0), tile(0, 1), tile(1, 1), tile(5, 5),
    ]);
    const visible = selectVisibleTiles(index, 11, {scale: 1, tx: offset, ty: offset},
      size * 1.5, size * 1.5, 1);
    expect(visible.map((item) => `${item.x}:${item.y}`)).toEqual(['0:0', '1:0', '0:1', '1:1']);
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

  it('keeps the vehicle aligned to the initial route direction through the opening zoom', () => {
    const headingAtFrame = (frame: number) => Number(attribute(
      renderProps(frame, props), 'data-m2v-heading'));
    const initialHeading = headingAtFrame(0);
    for (let frame = 1; frame < 60; frame += 1) {
      expect(headingAtFrame(frame), `vehicle heading changed during opening at frame ${frame}`)
        .toBe(initialHeading);
    }
    expect(distanceForFrame(60, props.durationInFrames, props.fps,
      buildRouteModel(props.steps).lengthMeters)).toBeGreaterThan(0);
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
    const layer = {
      zoom: 8,
      bbox: [121.44, 31.2, 121.53, 31.29] as [number, number, number, number],
      image: {path: 'assets/basemap/x.jpg', sha256: 'a'.repeat(64), width: 256, height: 256},
      projected: {left: 13_500_000, top: -3_660_000, width: 200_000, height: 200_000},
      tileCount: 4,
      dataUri: 'data:image/jpeg;base64,/9j/4AAQSkZJRg==',
    };
    const basemap = {
      provider: 'amap',
      service: 'road-tiles',
      attribution: '地图数据 © 高德地图',
      fetchedAt: '2026-10-30T13:00:00+08:00',
      overview: layer,
      followTiles: {zoom: 11, tileSize: 256, tiles: []},
    };
    const markup = renderProps(900, {...props, basemap});
    const full = fitCameraInContent(model.bounds, 1080, 1920);
    expect(Number(attribute(markup, 'data-m2v-scale'))).toBeCloseTo(full.scale * 16, 5);
    expect(markup).toContain('data-m2v-basemap="overview"');
    expect(markup).toContain('data-m2v-basemap-layer="follow"');
    expect(markup).toContain('data-m2v-basemap-opacity="1.0000"');
    expect(markup).toContain('data:image/jpeg;base64');
  });

  it('keeps administrative labels on a stable upper anchor between frames', () => {
    const places = [
      {name: '苏州市', level: 'city' as const, adcode: '320500', center: [121.485, 31.2462] as [number, number]},
      {name: '昆山市', level: 'county' as const, adcode: '320583', parentAdcode: '320500',
        center: [121.485, 31.2453] as [number, number]},
    ];
    const yAt = (frame: number) => {
      const markup = renderProps(frame, {...props, administrativePlaces: places});
      const match = markup.match(/data-m2v-administrative-label="苏州市"[^>]*y="(-?\d+(?:\.\d+)?)"/u);
      return match ? Number(match[1]) : null;
    };
    const first = yAt(900);
    let previous = first;
    expect(previous).not.toBeNull();
    for (let frame = 901; frame <= 910; frame += 1) {
      const current = yAt(frame);
      expect(current).not.toBeNull();
      expect(Math.abs((current as number) - (previous as number))).toBeLessThan(20);
      previous = current;
    }
  });

  it('preserves subpixel screen positions while the camera follows the route', () => {
    const markup = renderProps(901, {...props, administrativePlaces: [
      {name: '苏州市', level: 'city' as const, adcode: '320500', center: [121.485, 31.2462] as [number, number]},
    ]});
    expect(markup).toMatch(/data-m2v-administrative-label="苏州市"[^>]*x="\d+\.\d{2}"[^>]*y="-?\d+\.\d{2}"/u);
  });

  it('fades administrative labels continuously across collision thresholds for a full route', () => {
    const places = [
      {name: '苏州市', level: 'city' as const, adcode: '320500', center: [121.485, 31.2462] as [number, number]},
      {name: '昆山市', level: 'county' as const, adcode: '320583', parentAdcode: '320500',
        center: [121.485, 31.2453] as [number, number]},
    ];
    const previous = new Map<string, number>();
    for (let frame = 0; frame < props.durationInFrames; frame += 1) {
      const markup = renderProps(frame, {...props, administrativePlaces: places});
      const current = new Map([...markup.matchAll(
        /data-m2v-administrative-label="([^"]+)"[^>]*opacity="([\d.]+)"/gu,
      )].map((match) => [match[1]!, Number(match[2])]));
      for (const name of new Set([...previous.keys(), ...current.keys()])) {
        const opacity = current.get(name) ?? 0;
        const before = previous.get(name);
        if (before !== undefined) {
          expect(Math.abs(opacity - before), `${name} opacity jumped at frame ${frame}`)
            .toBeLessThan(0.12);
        }
        previous.set(name, opacity);
      }
    }
    expect(previous.size).toBe(2);
  });

  it('keeps administrative collision priority independent of material array order', () => {
    const places = [
      {name: '昆山市', level: 'county' as const, adcode: '320583', parentAdcode: '320500',
        center: [121.485, 31.2462] as [number, number]},
      {name: '苏州市', level: 'city' as const, adcode: '320500', center: [121.485, 31.2462] as [number, number]},
    ];
    const labels = (markup: string) => [...markup.matchAll(
      /data-m2v-administrative-label="([^"]+)"[^>]*x="([^"]+)"[^>]*y="([^"]+)"[^>]*text-anchor="middle"\s+opacity="([^"]+)"/gu,
    )].map((match) => match.slice(1));
    expect(labels(renderProps(900, {...props, administrativePlaces: places})))
      .toEqual(labels(renderProps(900, {...props, administrativePlaces: [...places].reverse()})));
  });

  it('shows only city labels in the settled full-route overview', () => {
    const places = [
      {name: '苏州市', level: 'city' as const, adcode: '320500', center: [121.485, 31.2462] as [number, number]},
      {name: '昆山市', level: 'county' as const, adcode: '320583', parentAdcode: '320500',
        center: [121.49, 31.25] as [number, number]},
    ];
    const markup = renderProps(props.durationInFrames - 1, {...props, administrativePlaces: places});
    expect(markup).toContain('data-m2v-administrative-label="苏州市"');
    expect(markup).not.toContain('data-m2v-administrative-label="昆山市"');
  });

  it('draws city and county administrative names at the same size', () => {
    const markup = renderProps(900, {
      ...props,
      administrativePlaces: [
        {name: '苏州市', level: 'city', adcode: '320500', center: [121.485, 31.2462]},
        {name: '昆山市', level: 'county', adcode: '320583', parentAdcode: '320500',
          center: [121.485, 31.2453]},
        {name: '黄浦区', level: 'county', adcode: '310101', parentAdcode: '310000',
          center: [121.485, 31.245]},
      ],
    });
    expect(markup).toContain('data-m2v-administrative-label="苏州市"');
    expect(markup).toContain('data-m2v-administrative-level="city"');
    expect(markup).toContain('data-m2v-administrative-label="昆山市"');
    expect(markup).toContain('data-m2v-administrative-level="county"');
    expect(markup).not.toContain('data-m2v-administrative-label="黄浦区"');
    for (const name of ['苏州市', '昆山市']) {
      expect(markup).toMatch(new RegExp(
        `data-m2v-administrative-label="${name}"[^>]*x="\\d+(?:\\.\\d+)?"[^>]*y="-?\\d+(?:\\.\\d+)?"`
        + '[^>]*opacity="[\\d.]+"[^>]*fill="#[\\da-f]+"[^>]*font-size="30"'
        + '[^>]*font-weight="700"[^>]*stroke="#[\\da-f]+"[^>]*stroke-width="8"', 'u'));
    }
    expect(markup).not.toContain('data-m2v-city-label');
  });

  it('produces identical markup for the same frame', () => {
    expect(render(900)).toBe(render(900));
  });
});
