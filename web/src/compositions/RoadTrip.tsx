/**
 * 多日地图游记 composition：每日章节卡、真实路线跟随、行政区标签、数据卡与字幕。
 *
 * 画面只读 props 与静态布局；相机、里程、已走路线与标签都是当前帧的纯函数。
 * 底图只挂载当前视口可见的瓦片，地址由渲染时注入的 `assetBase` 拼接。
 */
import {useEffect, useMemo} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame} from 'remotion';
import {FONT_STACK} from '../fonts';
import {
  buildTileIndex, headingAtDistance, selectVisibleTiles, type FollowTile,
} from './driving/route';
import {MapLayer} from './driving/MapLayer';
import {estimateTextWidth} from './driving/labels';
import {
  cameraForDay, chapterOpacity, contentRect, dayAtFrame, dayDistance, followOpacity,
  formatDistance, localModel, resolveBasemap, screenOf, walkedPointsAt, LAYOUT,
  type RoadTripDay, type RoadTripProps,
} from './roadtrip/model';

export type {RoadTripProps} from './roadtrip/model';

const INK = '#142433';
const MUTED = '#5b6b7c';
const WALKED = '#1f6feb';
const UNWALKED = '#64717f';
const MAP_BG = '#f3f0e9';
const PANEL = '#ffffff';

const platePadding = (size: number): string => `${Math.round(size * 0.2)}px ${Math.round(size * 0.5)}px`;

/** 已解码过的瓦片地址；只保留字符串，避免把整幅位图长期驻留内存。 */
const loadedImages = new Set<string>();

function useImagesReady(urls: string[]): void {
  const signature = urls.join('|');
  useEffect(() => {
    const pending = urls.filter((url) => !loadedImages.has(url));
    if (pending.length === 0) return;
    const handle = delayRender('加载当前视口瓦片', {timeoutInMilliseconds: 120_000});
    let remaining = pending.length;
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      continueRender(handle);
    };
    const fail = () => {
      if (settled) return;
      settled = true;
      cancelRender(new Error('当前视口瓦片加载失败'));
    };
    const images = pending.map((url) => {
      const image = new Image();
      image.onload = () => {
        loadedImages.add(url);
        remaining -= 1;
        if (remaining <= 0) finish();
      };
      image.onerror = fail;
      image.src = url;
      return image;
    });
    return () => {
      finish();
      for (const image of images) {
        image.onload = null;
        image.onerror = null;
      }
    };
    // urls 由 signature 唯一决定；不把数组本身加入依赖。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);
}

type Box = {left: number; right: number; top: number; bottom: number};

function overlaps(first: Box, second: Box): boolean {
  return !(first.right < second.left || first.left > second.right
    || first.bottom < second.top || first.top > second.bottom);
}

function AreaLabels({day, camera, width, height, offset, showCounties, endpoints}: {
  day: RoadTripDay; camera: {scale: number; tx: number; ty: number};
  width: number; height: number; offset: {x: number; y: number}; showCounties: boolean;
  endpoints: Array<{x: number; y: number}>;
}) {
  const boxes: Box[] = [];
  const places = [...(day.administrativePlaces ?? [])].sort((first, second) =>
    (first.level === 'city' ? 0 : 1) - (second.level === 'city' ? 0 : 1)
    || first.adcode.localeCompare(second.adcode, 'en')
    || first.name.localeCompare(second.name, 'zh-CN'));
  const labels = places.flatMap((place) => {
    if (place.level === 'county' && !showCounties) return [];
    if (place.name.endsWith('区')) return [];
    const point = screenOf(camera, place.center, offset);
    const size = place.level === 'city' ? LAYOUT.labels.citySize : 22;
    if (point.x < 30 || point.x > width - 30 || point.y < LAYOUT.title.height + 40
      || point.y > height - 40) return [];
    if (endpoints.some((endpoint) => Math.hypot(point.x - endpoint.x, point.y - endpoint.y) < 90)) {
      return [];
    }
    const halfWidth = (estimateTextWidth(place.name, size) + 16) / 2;
    const box = {left: point.x - halfWidth, right: point.x + halfWidth,
      top: point.y - size - 10, bottom: point.y + 8};
    if (boxes.some((other) => overlaps(box, other))) return [];
    boxes.push(box);
    return [<text key={place.adcode} data-m2v-administrative-label={place.name}
      data-m2v-administrative-level={place.level}
      x={point.x.toFixed(2)} y={(point.y - (place.level === 'city' ? 24 : 18)).toFixed(2)}
      textAnchor="middle" fill={INK} fontSize={size} fontWeight={LAYOUT.labels.cityWeight}
      stroke="#ffffff" strokeWidth={place.level === 'city' ? LAYOUT.labels.cityStrokeWidth : 7}
      paintOrder="stroke" strokeLinejoin="round">{place.name}</text>];
  });
  return <g data-m2v-administrative-labels="true">{labels}</g>;
}

export function RoadTrip(props: RoadTripProps) {
  const frame = useCurrentFrame();
  const {day, index, localFrame} = dayAtFrame(props, frame);
  const {model, offset} = useMemo(() => localModel(day.steps), [day.steps]);
  const assetBase = props.assetBase ?? '';
  const camera = cameraForDay(model, day, localFrame, props.width, props.height);
  const distance = dayDistance(model, day, localFrame);
  const walked = walkedPointsAt(model, distance);
  const basemap = resolveBasemap(day, assetBase, offset);
  const tileIndex = useMemo(
    () => buildTileIndex((basemap?.followTiles.tiles ?? []) as FollowTile[]),
    [basemap]);
  const visibleTiles = day.basemap && localFrame >= day.followStart
    ? selectVisibleTiles(tileIndex, day.basemap.followTiles.zoom, camera, props.width,
      props.height, 2)
    : [];
  const readyUrls = [
    ...(day.basemap ? [assetBase + day.basemap.overview.path] : []),
    ...visibleTiles.map((tile) => tile.dataUri),
  ];
  useImagesReady(readyUrls);
  const opacity = followOpacity(day, localFrame);
  const chapter = chapterOpacity(day, localFrame);
  const traveled = day.totalDistanceMeters * Math.min(1, distance / Math.max(1, model.lengthMeters));
  const traveling = walked[walked.length - 1]!;
  const vehicle = {x: traveling.x * camera.scale + camera.tx,
    y: traveling.y * camera.scale + camera.ty};
  // 起点首段可能是一小段连接线；用前 60 米的切向，避免车辆一开始朝反方向。
  const headingDistance = distance < 60 ? Math.min(model.lengthMeters, 60) : distance;
  const heading = (headingAtDistance(model, headingDistance) * 180) / Math.PI;
  const content = contentRect(props.width, props.height);
  const cardVisible = day.card && localFrame >= day.arrivalLocalFrame - 30;
  const cardTop = LAYOUT.dataCard.top;
  const cardHeight = LAYOUT.dataCard.padding * 2 + LAYOUT.dataCard.titleSize
    + (day.card?.facts.length ?? 0) * (LAYOUT.dataCard.valueSize + LAYOUT.dataCard.rowGap) + 38;
  const isLast = index === props.days.length - 1;
  const endingOpacity = isLast
    ? Math.max(0, Math.min(1, (localFrame - day.arrivalLocalFrame - 12) / 24)) : 0;
  // 端点标记直接用投影坐标换算，避免再由经纬度反投影。
  const first = model.projected[0]!;
  const last = model.projected[model.projected.length - 1]!;
  const startScreen = {x: first.x * camera.scale + camera.tx, y: first.y * camera.scale + camera.ty};
  const endScreen = {x: last.x * camera.scale + camera.tx, y: last.y * camera.scale + camera.ty};
  const showEndpoints = localFrame >= day.arrivalLocalFrame;

  const attributionSize = LAYOUT.labels.attributionSize;
  const attributionWidth = estimateTextWidth(props.attribution, attributionSize) + 32;

  const zoomWindow = LAYOUT.followZoomWindows.find((item) => item.dayId === day.id);
  const landmark = zoomWindow
    ? day.landmarks.find((item) => item.id === zoomWindow.landmarkId) : undefined;
  const landmarkNear = landmark && Math.abs(distance / Math.max(1, model.lengthMeters)
    - landmark.distanceMeters / Math.max(1, model.lengthMeters)) < 0.09;

  const endpointLabel = (point: {x: number; y: number}, label: string, key: string) => {
    if (point.x < 10 || point.x > props.width - 10 || point.y < LAYOUT.title.height + 20
      || point.y > props.height - 30) return null;
    const size = LAYOUT.labels.endpointSize;
    const half = (estimateTextWidth(label, size) + 16) / 2;
    const x = Math.min(props.width - half - 24, Math.max(half + 24, point.x));
    return <text key={key} data-m2v-endpoint-label={label} x={x.toFixed(2)}
      y={(point.y - 22).toFixed(2)} textAnchor="middle" fill={INK} fontSize={size}
      fontWeight={700} stroke="#ffffff" strokeWidth={7} paintOrder="stroke"
      strokeLinejoin="round">{label}</text>;
  };

  return <AbsoluteFill data-m2v-roadtrip="true"
    style={{background: MAP_BG, fontFamily: FONT_STACK}}>
    <svg width={props.width} height={props.height} viewBox={`0 0 ${props.width} ${props.height}`}
      role="img" aria-label={`${props.title}，第 ${index + 1} 天`} data-m2v-roadtrip-frame={frame}>
      <MapLayer camera={camera} model={model} distance={distance} walked={walked}
        basemap={basemap} visibleTiles={visibleTiles} followOpacity={opacity}
        walkedColor={WALKED} unwalkedColor={UNWALKED} />
      <AreaLabels day={day} camera={camera} width={props.width}
        height={props.height} offset={offset}
        showCounties={localFrame < day.arrivalLocalFrame}
        endpoints={showEndpoints ? [startScreen, endScreen] : []} />

      <g data-m2v-day-endpoints="true">
        <circle cx={startScreen.x} cy={startScreen.y} r={10} fill={WALKED}
          stroke="#ffffff" strokeWidth={3} />
        <circle cx={endScreen.x} cy={endScreen.y} r={12} fill="none" stroke={INK}
          strokeWidth={4} />
        <circle cx={endScreen.x} cy={endScreen.y} r={3} fill={INK} />
        {showEndpoints && endpointLabel(startScreen, day.originLabel, 'origin')}
        {showEndpoints && endpointLabel(endScreen, day.destinationLabel, 'destination')}
      </g>

      {landmarkNear && landmark && <g data-m2v-landmark-label={landmark.id}>
        <rect x={props.width / 2 - 150} y={LAYOUT.title.height + 20} width={300} height={52}
          rx={26} fill="rgba(255,255,255,0.94)" stroke="#d5dee8" strokeWidth={2} />
        <text x={props.width / 2} y={LAYOUT.title.height + 57} textAnchor="middle"
          fill={INK} fontSize={28} fontWeight={700}>{landmark.label}</text>
      </g>}

      <g data-m2v-vehicle="true" data-m2v-distance={distance.toFixed(1)}
        data-m2v-x={vehicle.x.toFixed(2)} data-m2v-y={vehicle.y.toFixed(2)}
        transform={`translate(${vehicle.x} ${vehicle.y}) rotate(${heading})`}>
        <circle r={24} fill={WALKED} opacity={0.16} />
        <path d="M 18 0 L -11 10 L -5 0 L -11 -10 Z" fill="#ffffff" stroke={INK}
          strokeWidth={2.5} strokeLinejoin="round" />
      </g>

      <g data-m2v-distance-pill="true">
        <rect x={content.left} y={props.height - 104} width={236} height={44} rx={22}
          fill="rgba(255,255,255,0.95)" stroke="#d5dee8" strokeWidth={2} />
        <text x={content.left + 118} y={props.height - 73} textAnchor="middle"
          fill={INK} fontSize={LAYOUT.labels.pillSize} fontWeight={700}>
          已行驶 {formatDistance(traveled)}
        </text>
      </g>

      <g data-m2v-title="true">
        <rect x={0} y={0} width={props.width} height={LAYOUT.title.height} fill={PANEL} />
        <text x={LAYOUT.title.sideMargin} y={LAYOUT.title.kickerY} fill={MUTED}
          fontSize={LAYOUT.title.kickerSize} fontWeight={600}>
          第 {index + 1} 天 / {props.days.length} · {day.originLabel} → {day.destinationLabel}
        </text>
        <text x={LAYOUT.title.sideMargin} y={LAYOUT.title.mainY} fill={INK}
          fontSize={LAYOUT.title.mainSize} fontWeight={700}>{day.title}</text>
        <line x1={0} y1={LAYOUT.title.height} x2={props.width} y2={LAYOUT.title.height}
          stroke="#dfe3e8" strokeWidth={2} />
      </g>

      <g data-m2v-attribution-box="true">
        <rect x={props.width - 22 - attributionWidth} y={props.height - 94}
          width={attributionWidth} height={52} rx={10} fill="rgba(255,255,255,0.94)" />
        <text data-m2v-attribution="true" x={props.width - 38} y={props.height - 59}
          textAnchor="end" fill={MUTED} fontSize={attributionSize}>
          {props.attribution}
        </text>
      </g>

      {cardVisible && <g data-m2v-card={day.card!.id}>
        <rect x={(props.width - LAYOUT.dataCard.width) / 2} y={cardTop}
          width={LAYOUT.dataCard.width} height={cardHeight}
          rx={18} fill="rgba(255,255,255,0.96)" stroke="#dbe3ec" strokeWidth={2} />
        <text x={props.width / 2} y={cardTop + LAYOUT.dataCard.padding + LAYOUT.dataCard.titleSize}
          textAnchor="middle" fill={INK} fontSize={LAYOUT.dataCard.titleSize} fontWeight={700}>
          {day.card!.title}
        </text>
        {day.card!.facts.map((fact, factIndex) => {
          const y = cardTop + LAYOUT.dataCard.padding + LAYOUT.dataCard.titleSize
            + (factIndex + 1) * (LAYOUT.dataCard.valueSize + LAYOUT.dataCard.rowGap);
          return <g key={fact.id}>
            <text x={props.width / 2 - LAYOUT.dataCard.width / 2 + LAYOUT.dataCard.padding}
              y={y} fill={MUTED} fontSize={LAYOUT.dataCard.labelSize}>{fact.label}</text>
            <text x={props.width / 2 + LAYOUT.dataCard.width / 2 - LAYOUT.dataCard.padding}
              y={y} textAnchor="end" fill={INK} fontSize={LAYOUT.dataCard.valueSize}
              fontWeight={700}>{fact.value}</text>
          </g>;
        })}
        <text x={props.width / 2 - LAYOUT.dataCard.width / 2 + LAYOUT.dataCard.padding}
          y={cardTop + cardHeight - 16} textAnchor="start" fill={MUTED} fontSize={24}>
          来源：{day.card!.facts.map((fact) => {
            const source = props.sources[fact.sourceId];
            return source ? `${source.publisher}·${source.title}` : fact.sourceId;
          }).filter((title, position, all) => all.indexOf(title) === position).join('；')}
        </text>
      </g>}

      {chapter > 0 && <g data-m2v-chapter-card={day.id} opacity={chapter}>
        <rect x={0} y={0} width={props.width} height={props.height}
          fill={LAYOUT.chapterCard.background} />
        {index === 0 && <text x={props.width / 2} y={props.height / 2 - 235} textAnchor="middle"
          fill="#7fa6c9" fontSize={26} fontWeight={600}>{props.title}</text>}
        <text x={props.width / 2} y={props.height / 2 - 180} textAnchor="middle"
          fill="#9dbdd8" fontSize={LAYOUT.chapterCard.kickerSize} fontWeight={600}>
          第 {index + 1} 天 · {day.originLabel} → {day.destinationLabel}
        </text>
        <text x={props.width / 2} y={props.height / 2 - 60} textAnchor="middle"
          fill="#ffffff" fontSize={LAYOUT.chapterCard.titleSize} fontWeight={800}>
          {day.title}
        </text>
        {day.subtitle && <text x={props.width / 2} y={props.height / 2 + 30} textAnchor="middle"
          fill="#c8d8e8" fontSize={LAYOUT.chapterCard.subtitleSize}>{day.subtitle}</text>}
      </g>}

      {endingOpacity > 0 && <g data-m2v-ending="true" opacity={endingOpacity}>
        <rect x={120} y={1160} width={840} height={230} rx={22} fill="rgba(13,27,42,0.94)" />
        <text x={props.width / 2} y={1260} textAnchor="middle" fill="#ffffff"
          fontSize={42} fontWeight={800}>{props.title}</text>
        <text x={props.width / 2} y={1322} textAnchor="middle" fill="#9dbdd8" fontSize={26}>
          {props.originLabel} → {props.destinationLabel} · {props.days.length} 天
        </text>
      </g>}
    </svg>
    <div data-m2v-subtitle="" style={{position: 'absolute', zIndex: 2,
      left: props.subtitle.safeArea.x, top: props.subtitle.safeArea.y,
      width: props.subtitle.safeArea.width, height: props.subtitle.safeArea.height,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: FONT_STACK, fontSize: props.subtitle.fontSize,
      lineHeight: props.subtitle.lineHeight, color: props.subtitle.textColor,
      textAlign: 'center'}}>
      {props.subtitleCues.find((cue) => cue.startFrame <= frame && frame < cue.endFrame)
        && <span data-m2v-copy="" style={{maxWidth: '100%', overflowWrap: 'anywhere',
          background: props.subtitle.plateColor,
          padding: platePadding(props.subtitle.fontSize)}}>
          {props.subtitleCues.find((cue) => cue.startFrame <= frame && frame < cue.endFrame)!.text}
        </span>}
    </div>
  </AbsoluteFill>;
}
