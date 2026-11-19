import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three/webgpu';
import {normalWorld, positionView, texture, uniform, uv, vec2, vec4, wgslFn} from 'three/tsl';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {TRANSMISSIVE_BACKGROUND_ENVIRONMENT, WebGPUPathTracer} from 'three-gpu-pathtracer/webgpu';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {fade, half, macroState, type Block, type Glass} from './compound-model';

function yieldRenderer() {
  return new Promise<void>(resolve => {
    const channel = new MessageChannel();
    channel.port1.onmessage = () => { channel.port1.close(); channel.port2.close(); resolve(); };
    channel.port2.postMessage(null);
  });
}

const cleanupNoise = wgslFn(`
  fn cleanupNoise(tex: texture_2d<f32>, guide: texture_2d<f32>, coord: vec2f, axis: vec2f) -> vec3f {
    let luma = vec3f(.2126, .7152, .0722);
    let size = vec2i(textureDimensions(tex, 0));
    let pixel = clamp(vec2i(coord * vec2f(size)), vec2i(0), size - 1);
    let normalDepth = textureLoad(guide, pixel, 0);
    let surfaceKind = floor(normalDepth.w * 3.);
    let depth = fract(normalDepth.w * 3.);
    let isFloor = surfaceKind == 0. && normalDepth.y > .96 && depth > .28;
    let spread = select(3.7, 5.5, isFloor);
    let depthTolerance = select(.002, .018, isFloor);
    var total = vec3f(0.);
    var sum = 0.;
    for (var step = -7; step <= 7; step++) {
      let neighborPixel = clamp(pixel + i32(step) * vec2i(axis), vec2i(0), size - 1);
      let neighbor = textureLoad(tex, neighborPixel, 0).rgb;
      let neighborSurface = textureLoad(guide, neighborPixel, 0);
      let surfaceDelta = neighborSurface - normalDepth;
      let normalDirection = surfaceDelta.rgb * 12.;
      let viewDepth = (fract(neighborSurface.w * 3.) - depth) / depthTolerance;
      let distance = f32(step) / spread;
      let sameMaterial = select(0., 1., floor(neighborSurface.w * 3.) == surfaceKind);
      let weight = sameMaterial * exp(-.5 * distance * distance - dot(normalDirection, normalDirection) - viewDepth * viewDepth);
      // 柔光箱的亮部保留渐变，避免单个高能样本污染周围像素。
      let shoulder = max(0., dot(neighbor, luma) - 1.15);
      let clean = neighbor / (1. + .5 * shoulder * shoulder / (.45 + shoulder));
      total += clean * weight;
      sum += weight;
    }
    return total / max(.0001, sum);
  }
`);

const combineGlass = wgslFn(`
  fn combineGlass(radiance: texture_2d<f32>, background: texture_2d<f32>, guide: texture_2d<f32>,
    coord: vec2f, amount: f32, focus: f32, stacked: f32, nearOptics: f32, windowOptics: f32, towerOptics: f32) -> vec3f {
    let extent = vec2i(textureDimensions(radiance, 0));
    let pixel = clamp(vec2i(coord * vec2f(extent)), vec2i(0), extent - 1);
    let reflected = textureLoad(radiance, pixel, 0).rgb;
    let surface = textureLoad(guide, pixel, 0);
    let kind = floor(surface.w * 3.);
    if (kind < 1. || amount <= .001) { return reflected; }

    let normal = normalize(surface.xyz * 2. - 1.);
    let horizon = coord.x * 23. - coord.y * 34.;
    let depth = fract(surface.w * 3.);
    let wedge = vec2f(normal.x + .48 * normal.z, -.55 * normal.y - .31 * normal.z);
    let warp = vec2f(sin(horizon + depth * 84.) * .0032, cos(horizon * .8 + depth * 38.) * .0038);
    let plateDisplacement = select(0., .069 + .022 * (coord.x - .5) + .009 * sin(coord.x * 16.), kind >= 2.);
    let surfaceBend = vec2f(.077 * normal.x + .026 * normal.z, .055 * normal.y - .037 * normal.z);
    let closePlateShift = vec2f(.055 * normal.x + .025 * normal.z - .009, .036 * normal.y - .018 * normal.z - .006);
    let nearShift = select(surfaceBend + vec2f(-.026, .029), closePlateShift, kind >= 2.);
    let oldShift = mix((.006 + .010 * abs(normal.x)) * wedge + warp + vec2f(0., plateDisplacement), nearShift, nearOptics);
    let windowShift = vec2f(-.015 + .022 * normal.x + .010 * normal.z, .011 - .022 * normal.y + .020 * normal.z);
    let tower = towerOptics * stacked * smoothstep(.62, .70, coord.x);
    let towerShift = vec2f(-.009 + .081 * normal.x, .012 - .058 * normal.y + .008 * normal.z);
    let shift = mix(mix(oldShift, windowShift, windowOptics), towerShift, tower);
    let pos = (coord + shift) * vec2f(extent) - .5;
    let p = vec2i(floor(pos));
    let t = fract(pos);
    let a = textureLoad(background, clamp(p, vec2i(0), extent - 1), 0).rgb;
    let b = textureLoad(background, clamp(p + vec2i(1, 0), vec2i(0), extent - 1), 0).rgb;
    let c = textureLoad(background, clamp(p + vec2i(0, 1), vec2i(0), extent - 1), 0).rgb;
    let d = textureLoad(background, clamp(p + vec2i(1), vec2i(0), extent - 1), 0).rgb;
    let behind = mix(mix(a, b, t.x), mix(c, d, t.x), t.y);
    if (windowOptics > .5) {
      let grazing = pow(1. - abs(dot(normal, normalize(vec3f(.23, .21, .95)))), 2.);
      let facet = max(grazing, smoothstep(.19, .86, abs(normal.x)));
      let through = behind * mix(vec3f(1.50, .77, .28), vec3f(1.49, .63, .18), facet);
      let glimmer = (reflected / (1. + .9 * reflected)) * vec3f(.92, .66, .42);
      let optics = mix(through, glimmer, .14 + .29 * facet);
      let priority = select(1. - .22 * focus, 1.20, kind >= 2.);
      return mix(reflected, optics * priority, amount);
    }
    if (nearOptics > .5) {
      let grazing = pow(1. - abs(dot(normal, normalize(vec3f(.42, .27, .87)))), 2.);
      let facet = smoothstep(.32, .92, 1. - abs(normal.y));
      let opticalPath = mix(.62, 1.28, facet);
      let tint = exp(-vec3f(.04, .47, 1.52) * opticalPath);
      let incident = max(0., dot(behind, vec3f(.2126, .7152, .0722)));
      let interior = behind * tint * (.42 + 1.6 * smoothstep(.015, .45, incident));
      let bounce = reflected * vec3f(.60, .39, .22);
      let transmission = .98 - .19 * facet - .24 * grazing;
      let edge = smoothstep(.11, .58, behind.b) * (.42 * facet + .54 * grazing);
      let accent = vec3f(.30, .097, .016) * edge;
      let prominence = select(1. - .33 * focus, 1.15, kind >= 2.);
      return (mix(bounce, interior, transmission) * vec3f(1.32, .78, .45) + accent) * prominence;
    }
    let glancing = pow(1. - abs(dot(normal, normalize(vec3f(.45, .18, 1.)))), 2.2);
    let tint = vec3f(1.44, .85, .35);
    let warm = vec3f(.042, .021, .007) * (1. + 1.6 * glancing);
    let transmitted = behind * tint + warm;
    let transparency = select(.57, .74, kind >= 2.) * (1. - .46 * glancing);
    let glass = mix(reflected, transmitted, amount * transparency);
    if (kind >= 2.) {
      let offsets = array<vec2i, 4>(vec2i(-4, 0), vec2i(4, 0), vec2i(0, -4), vec2i(0, 4));
      var contour = 0.;
      for (var i = 0; i < 4; i++) {
        let adjacent = textureLoad(guide, clamp(pixel + offsets[i], vec2i(0), extent - 1), 0);
        contour = max(contour, select(0., 1., floor(adjacent.w * 3.) < 2.));
      }
      let side = smoothstep(.22, .85, 1. - abs(normal.y));
      let bevel = max(.23 * contour, .55 * glancing + .62 * side);
      let clearFace = mix(reflected * .72, behind * vec3f(1.19, .89, .57), .90);
      let lateralLight = .48 + .64 * smoothstep(.41, .74, coord.x) + .22 * abs(normal.x);
      let amberSide = vec3f(.53, .204, .037) * focus * bevel * lateralLight;
      return clearFace * (1. - .28 * side) + amberSide;
    }
    let luminance = dot(glass, vec3f(.2126, .7152, .0722));
    let highlight = max(0., luminance - .23);
    let compressed = glass / (1. + stacked * 1.64 * highlight);
    let front = smoothstep(.36, .92, abs(normal.z));
    let warmGlass = compressed * mix(vec3f(.88, .66, .42), vec3f(1.13, .87, .51), front);
    let classicGlass = mix(compressed, warmGlass, stacked) * (1. - .32 * focus);
    // 正面透出棚景和暗隔，转向的截面才主要显出琥珀反光。
    let rim = pow(1. - abs(normal.z), 1.7);
    let pathTint = mix(vec3f(.72, .47, .31), vec3f(.87, .52, .25), rim);
    let rearImage = behind * pathTint;
    let amberRim = reflected / (1. + .8 * reflected) * vec3f(1.08, .77, .46);
    return mix(classicGlass, mix(rearImage, amberRim, .08 + .49 * rim), tower);
  }
`);

function studioEnvironment() {
  const width = 256;
  const height = 128;
  const pixels = new Uint16Array(width * height * 4);
  const lightSources = [
    [.23, .42, .10, .22, 1.5, 2.2, 3.4],
    [.62, .47, .035, .21, 3.6, 2.15, .87],
    [.78, .32, .085, .05, 2.1, 2.25, 2.55],
    [.45, .65, .19, .065, .45, .65, 1.03],
  ];
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const u = (x + .5) / width;
      const v = (y + .5) / height;
      const radiance = [.055, .083, .142];
      for (const [centerX, centerY, spreadX, spreadY, red, green, blue] of lightSources) {
        const dx = Math.min(Math.abs(u - centerX), 1 - Math.abs(u - centerX)) / spreadX;
        const dy = (v - centerY) / spreadY;
        const envelope = Math.exp(-2 * (dx * dx + dy * dy));
        radiance[0] += red * envelope;
        radiance[1] += green * envelope;
        radiance[2] += blue * envelope;
      }
      const pixel = (y * width + x) * 4;
      radiance.forEach((value, channel) => { pixels[pixel + channel] = THREE.DataUtils.toHalfFloat(value); });
      pixels[pixel + 3] = THREE.DataUtils.toHalfFloat(1);
    }
  }
  const texture = new THREE.DataTexture(pixels, width, height, THREE.RGBAFormat, THREE.HalfFloatType);
  texture.mapping = THREE.EquirectangularReflectionMapping;
  texture.colorSpace = THREE.LinearSRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

const traceScale = .78;

function cyclorama(nearCamera: THREE.PerspectiveCamera, macroLook: MacroLook) {
  const profile = [{y: 0, z: 35, v: 0}, {y: 0, z: -4, v: .3}];
  for (let step = 1; step <= 16; step++) {
    const theta = step * Math.PI / 32;
    profile.push({y: 3 - 3 * Math.cos(theta), z: -4 - 3 * Math.sin(theta), v: .30 + step / 16 * .27});
  }
  profile.push({y: 20, z: -7, v: 1});
  const positions: number[] = [];
  const coordinates: number[] = [];
  const triangles: number[] = [];
  profile.forEach(({y, z, v}, row) => {
    positions.push(-24, y, z, 24, y, z);
    coordinates.push(0, v, 1, v);
    if (row > 0) {
      const i = (row - 1) * 2;
      triangles.push(i, i + 1, i + 2, i + 1, i + 3, i + 2);
    }
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(coordinates, 2));
  geometry.setIndex(triangles);
  geometry.computeVertexNormals();

  const plate = document.createElement('canvas');
  plate.width = 1024;
  plate.height = 1024;
  const context = plate.getContext('2d');
  if (!context) throw new Error('摄影棚背光纹理无法初始化');
  const paint = context;
  const backdrop = paint.createLinearGradient(0, 0, 0, 1024);
  backdrop.addColorStop(0, '#112234');
  backdrop.addColorStop(.55, '#0b1c2d');
  backdrop.addColorStop(.76, '#060d18');
  backdrop.addColorStop(1, '#030712');
  paint.fillStyle = backdrop;
  paint.fillRect(0, 0, 1024, 1024);

  const screen = paint.createRadialGradient(540, 466, 0, 540, 466, 175);
  screen.addColorStop(0, '#7198b7');
  screen.addColorStop(.35, '#496d8b');
  screen.addColorStop(.71, '#263d5b');
  screen.addColorStop(1, '#14284000');
  paint.fillStyle = screen;
  paint.fillRect(352, 286, 380, 366);

  const beams = paint.createLinearGradient(453, 0, 664, 0);
  beams.addColorStop(0, '#c0d9fb00');
  beams.addColorStop(.47, '#d0e9ff67');
  beams.addColorStop(1, '#d6e9ff00');
  paint.strokeStyle = beams;
  for (let ray = 0; ray < 5; ray++) {
    paint.lineWidth = ray === 1 ? 4 : 1.7;
    paint.beginPath();
    paint.moveTo(418, 541 + ray * 9);
    paint.bezierCurveTo(507, 547 + ray * 6, 543, 449 + ray * 5, 660, 407 + ray * 5);
    paint.stroke();
  }
  const transmittedStripe = paint.createLinearGradient(310, 0, 628, 0);
  transmittedStripe.addColorStop(0, '#aad6f400');
  transmittedStripe.addColorStop(.22, '#c7e9ff6d');
  transmittedStripe.addColorStop(.52, '#dceeff89');
  transmittedStripe.addColorStop(1, '#9ed7fa00');
  paint.strokeStyle = transmittedStripe;
  for (let ray = 0; ray < 3; ray++) {
    const offset = ray * 3.8;
    paint.lineWidth = ray === 1 ? 3.2 : 1.5;
    paint.beginPath();
    paint.moveTo(310, 488 + offset);
    paint.bezierCurveTo(421, 460 + offset, 490, 502 + offset, 628, 473 + offset);
    paint.stroke();
  }
  function warmFloor(strength: number) {
    paint.save();
    paint.globalAlpha = strength;
    const caustic = paint.createLinearGradient(472, 0, 675, 0);
    caustic.addColorStop(0, '#e18e4400');
    caustic.addColorStop(.35, '#ffb36575');
    caustic.addColorStop(.62, '#ffd2a890');
    caustic.addColorStop(1, '#e18e4400');
    paint.strokeStyle = caustic;
    paint.lineWidth = 1.8;
    for (let ray = 0; ray < 6; ray++) {
      const offset = ray * 2.4;
      paint.beginPath();
      paint.moveTo(478, 764 + offset);
      paint.bezierCurveTo(540, 729 + offset, 568, 768 + offset, 671, 742 + offset);
      paint.stroke();
    }
    paint.translate(506, 735);
    paint.scale(29, 21);
    const floorFocus = paint.createRadialGradient(0, 0, 0, 0, 0, 1);
    floorFocus.addColorStop(0, '#f7c796dc');
    floorFocus.addColorStop(.42, '#e7a5668f');
    floorFocus.addColorStop(1, '#c4753600');
    paint.fillStyle = floorFocus;
    paint.fillRect(-1, -1, 2, 2);
    paint.restore();
  }
  const texture = new THREE.CanvasTexture(plate);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshPhysicalMaterial({
    color: '#14253c', emissive: '#ffffff', emissiveMap: texture, emissiveIntensity: .66,
    roughness: .52, metalness: .04,
  });
  const paintedStage = paint.getImageData(0, 0, plate.width, plate.height);
  const mesh = new THREE.Mesh<THREE.BufferGeometry, THREE.Material>(geometry, material);
  nearCamera.updateMatrixWorld();
  const ray = new THREE.Raycaster();
  const rayStart = new THREE.Vector3();
  const rayEnd = new THREE.Vector3();
  function project(x: number, y: number, camera: THREE.Camera = nearCamera) {
    rayStart.set(x * 2 - 1, 1 - y * 2, -1).unproject(camera);
    rayEnd.set(x * 2 - 1, 1 - y * 2, .9).unproject(camera);
    ray.set(rayStart, rayEnd.sub(rayStart).normalize());
    const hit = ray.intersectObject(mesh)[0]?.uv;
    if (!hit) throw new Error('近景棚灯没有投到棚面');
    return [hit.x * plate.width, (1 - hit.y) * plate.height] as const;
  }
  function lightWindow(camera: THREE.Camera, isMacro: boolean, reveal: number, sculpture: number) {
    camera.updateMatrixWorld();
    function blade(x: number, top: number, bottom: number, gradient: number, strength: number) {
      const trace = (offset: number) => Array.from({length: 17}, (_, index) => {
        const t = index / 16;
        const y = top + (bottom - top) * t;
        const taper = .14 + .86 * Math.sqrt(1 - (2 * t - 1) ** 4);
        return project(x + gradient * (t - .5) + .048 * (t - .5) ** 2 + offset * taper, y, camera);
      });
      paint.save();
      for (const [left, right, color] of [
        [-.048, .052, '#6aade22c'], [-.029, .028, '#78a0cd8b'],
        [-.023, .001, '#aacdecab'], [.008, .023, '#84aed5b7'],
        [.024, .030, '#c9deef90'],
      ] as const) {
        paint.beginPath();
        for (const [x, y] of [...trace(left), ...trace(right).reverse()]) paint.lineTo(x, y);
        paint.closePath();
        paint.fillStyle = color;
        paint.globalAlpha = strength;
        paint.fill();
      }
      paint.restore();
    }
    if (isMacro) {
      blade(.64 - .076 * reveal, .11, .60 - .22 * reveal, -.245 + .057 * reveal, .79);
    } else if (sculpture > .001) {
      blade(.745, .20, .79, .24, .66 * sculpture);
      blade(.545, .65, .84, -.091, .52 * sculpture);
    }
  }
  function towerLight(camera: THREE.Camera, strength: number) {
    camera.updateMatrixWorld();
    const p = project(.752, .56, camera);
    const e = project(.95, .56, camera);
    const down = project(.752, .82, camera);
    paint.save();
    paint.setTransform(e[0] - p[0], e[1] - p[1], down[0] - p[0], down[1] - p[1], ...p);
    const pool = paint.createRadialGradient(0, 0, 0, 0, 0, 1);
    pool.addColorStop(0, '#84b7df93');
    pool.addColorStop(.46, '#5281b45a');
    pool.addColorStop(1, '#34558100');
    paint.globalAlpha = strength;
    paint.fillStyle = pool;
    paint.fillRect(-1, -1, 2, 2);
    paint.restore();
    paint.save();
    // 弯曲的连续灯窗从各层后方穿过，光窗以外留真实暗棚用于辨别折射位移。
    const ribbon = (edge: number) => Array.from({length: 27}, (_, point) => {
      const t = point / 26;
      return project(.728 + .053 * Math.sin(Math.PI * t) + edge, .20 + .55 * t, camera);
    });
    for (const [left, right, color] of [
      [-.021, .022, '#08142751'], [-.020, -.012, '#a8d9f96e'],
      [.018, .028, '#b4d2e675'], [.021, .025, '#f1d9b97a'],
    ] as const) {
      paint.beginPath();
      for (const [x, y] of [...ribbon(left), ...ribbon(right).reverse()]) paint.lineTo(x, y);
      paint.closePath();
      paint.fillStyle = color;
      paint.globalAlpha = strength;
      paint.fill();
    }
    for (let index = 0; index < 6; index++) {
      const arc = Array.from({length: 27}, (_, point) => {
        const t = point / 26;
        const x = .555 + .372 * t;
        const y = .197 + index * .081 + .078 * Math.sin(t * Math.PI * 1.1 + index * .15) - .057 * t;
        return project(x, y, camera);
      });
      const glow = paint.createLinearGradient(arc[0][0], 0, arc.at(-1)![0], 0);
      glow.addColorStop(0, '#799edb00');
      glow.addColorStop(.43, '#8ab7db2b');
      glow.addColorStop(.64, index % 2 ? '#d2e5f59e' : '#96c0e673');
      glow.addColorStop(.84, '#a1c5e22f');
      glow.addColorStop(1, '#7b9ac600');
      paint.globalAlpha = strength;
      paint.strokeStyle = glow;
      paint.lineWidth = index % 2 ? 1.85 : 1.15;
      paint.beginPath();
      paint.moveTo(...arc[0]);
      for (const point of arc.slice(1)) paint.lineTo(...point);
      paint.stroke();
    }
    paint.restore();
  }
  function shaftFill(strength: number) {
    const center = project(.61, .41);
    const right = project(.76, .41);
    const bottom = project(.61, .54);
    paint.save();
    paint.setTransform(right[0] - center[0], right[1] - center[1], bottom[0] - center[0], bottom[1] - center[1], ...center);
    const light = paint.createRadialGradient(0, 0, 0, 0, 0, 1);
    light.addColorStop(0, '#a7c7e796');
    light.addColorStop(.41, '#6188b37a');
    light.addColorStop(1, '#4274a700');
    paint.globalAlpha = strength;
    paint.fillStyle = light;
    paint.fillRect(-1, -1, 2, 2);
    paint.restore();
  }
  // 同一个棚面出现在玻璃后方和折射缓冲，落位后的逆光抬向次年悬片。
  function rearLight(reveal: number) {
    const lift = .113 * reveal;
    paint.save();
    const start = .36;
    const end = 1;
    const pathY = (t: number) => .435 - .286 * t + .078 * t * (1 - t) - lift;
    const spine = Array.from({length: 25}, (_, step) => {
      const t = step / 24;
      return project(start + (end - start) * t, pathY(t));
    });
    const [fromX] = spine[0];
    const [toX] = spine.at(-1)!;
    for (const [width, color] of [[15, '#75adf124'], [7, '#8bbdf541'], [2.2, '#bcdcffb2']] as const) {
      const dimEnds = paint.createLinearGradient(fromX, 0, toX, 0);
      dimEnds.addColorStop(0, '#659bdd00');
      dimEnds.addColorStop(.27, color);
      dimEnds.addColorStop(.69, color);
      dimEnds.addColorStop(1, '#659bdd37');
      paint.beginPath();
      paint.moveTo(...spine[0]);
      for (const point of spine.slice(1)) paint.lineTo(...point);
      paint.lineCap = 'round';
      paint.strokeStyle = dimEnds;
      paint.lineWidth = width;
      paint.stroke();
    }
    paint.restore();
  }
  let lastLightKey = '';
  function lightFromGlass(sources: readonly {x: number; z: number; breadth: number; power: number}[], isMacro: boolean,
      reveal: number, sculpture: number, camera: THREE.Camera) {
    const key = JSON.stringify([isMacro, reveal, sculpture, sources]);
    if (key === lastLightKey) return;
    lastLightKey = key;
    paint.putImageData(paintedStage, 0, 0);
    warmFloor(1 - .72 * sculpture);
    if (isMacro && macroLook === 'overhead' && reveal < .999) shaftFill(1 - reveal);
    if (isMacro && (macroLook === 'slit' || macroLook === 'studio')) rearLight(reveal);
    if (macroLook === 'window') lightWindow(camera, isMacro, reveal, sculpture);
    if (!isMacro && macroLook === 'classic' && sculpture > .001) towerLight(camera, sculpture);
    for (const {x, z, breadth, power} of sources) {
      const px = plate.width * (x + 24) / 48;
      const py = plate.height * (1 - .3 * (35 - z) / 39);
      const spread = 17 + breadth * 10;
      const warmth = paint.createLinearGradient(px - spread, 0, px + spread * 1.6, 0);
      warmth.addColorStop(0, '#ffb76000');
      warmth.addColorStop(.29, '#f6a85558');
      warmth.addColorStop(.52, '#ffd3a4e8');
      warmth.addColorStop(.73, '#eda44764');
      warmth.addColorStop(1, '#e7985100');
      paint.save();
      paint.strokeStyle = warmth;
      paint.globalAlpha = power;
      for (let index = 0; index < 6; index++) {
        const distance = index / 5;
        paint.lineWidth = .65 + (1 - distance) * .75;
        paint.beginPath();
        paint.moveTo(px - spread * (1 - .30 * distance), py + 7 + 13 * distance);
        paint.bezierCurveTo(px - spread * .44, py - 7 + distance * 6, px + spread * .19, py + 12 + distance * 12,
          px + spread * (1.35 + distance * .21), py + 14 + distance * 7);
        paint.stroke();
      }
      paint.restore();
    }
    texture.needsUpdate = true;
  }
  return {mesh, texture, lightFromGlass};
}

class ChartCamera extends THREE.OrthographicCamera {
  rise = 0;

  override updateProjectionMatrix() {
    super.updateProjectionMatrix();
    const matrix = this.projectionMatrix.elements;
    matrix[8] = -.56 * matrix[0];
    matrix[9] = -(this.rise ?? 0) * matrix[5];
    matrix[12] += matrix[8] * this.position.z;
    matrix[13] += matrix[9] * this.position.z;
    this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
}

type StageFrame = {
  blocks: Block[]; floor: number; rise: number; isMacro: boolean; sculpture: number; reveal: number;
  motionSamples?: number;
};
export type MacroLook = 'classic' | 'cut' | 'slit' | 'studio' | 'window' | 'fluted' | 'overhead';

function curvedGlass(flatGlass: RoundedBoxGeometry) {
  const shape = flatGlass.clone();
  const points = shape.getAttribute('position');
  const normals = shape.getAttribute('normal');
  const direction = new THREE.Vector3();
  for (let index = 0; index < points.count; index++) {
    const x = points.getX(index);
    const z = points.getZ(index);
    const aboveBase = points.getY(index) + .5;
    const curvature = .92 * x * x + .62 * z * z + .45 * x * z - .13;
    points.setY(index, aboveBase * (1 + curvature) - .5);
    // 曲面从平底向上展开，玻璃落位时仍与本金共享接触面。
    const y = normals.getY(index) / (1 + curvature);
    direction.set(normals.getX(index) - y * aboveBase * (1.84 * x + .45 * z), y,
      normals.getZ(index) - y * aboveBase * (1.24 * z + .45 * x)).normalize();
    normals.setXYZ(index, direction.x, direction.y, direction.z);
  }
  return shape;
}

function flutedGlass(segments: number, amplitude: number, frequency = Math.PI * 6) {
  const shape = new RoundedBoxGeometry(1, 1, 1, segments, .11);
  const points = shape.getAttribute('position');
  const normals = shape.getAttribute('normal');
  const direction = new THREE.Vector3();
  for (let index = 0; index < points.count; index++) {
    const x = points.getX(index);
    const z = points.getZ(index) + .5;
    const curve = amplitude * Math.sin(frequency * x);
    points.setZ(index, z - .5 + curve * z ** 3);
    const normalZ = normals.getZ(index) / (1 + 3 * curve * z ** 2);
    direction.set(normals.getX(index) - normalZ * amplitude * frequency * Math.cos(frequency * x) * z ** 3,
      normals.getY(index), normalZ).normalize();
    normals.setXYZ(index, direction.x, direction.y, direction.z);
  }
  return shape;
}

function startStudio(canvas: HTMLCanvasElement, width: number, height: number, sampleBudget: number, capacity: number, macroLook: MacroLook) {
  const fluted = macroLook === 'fluted';
  const overhead = macroLook === 'overhead';
  const directOptics = macroLook === 'studio' || fluted || overhead;
  const windowOptics = macroLook === 'window';
  const renderer = new THREE.WebGPURenderer({canvas, alpha: false, antialias: false});
  renderer.setSize(width, height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const stage = new THREE.Scene();
  stage.background = new THREE.Color('#152332');
  const environment = studioEnvironment();
  stage.environment = environment;
  stage.environmentIntensity = .52;
  const nearCamera = new THREE.PerspectiveCamera(34, width / height, .1, 60);
  nearCamera.position.set(4.2, 4.68, 10.5);
  nearCamera.lookAt(-1.45, 1.55, -.65);
  if (overhead) {
    nearCamera.position.set(4.7, 10.64, 6.9);
    nearCamera.lookAt(-1.25, 1.92, -.35);
  }
  const chartCamera = new ChartCamera(-9.6, 9.6, 8.14, -2.66, .1, 45);
  chartCamera.position.z = 14;

  const {mesh: floor, texture: field, lightFromGlass} = cyclorama(nearCamera, macroLook);
  stage.add(floor);

  function softbox(color: string, intensity: number, width: number, height: number, position: [number, number, number], aim: [number, number, number] = [0, 1.5, -1]) {
    const source = new THREE.RectAreaLight(color, intensity, width, height);
    source.position.set(...position);
    source.lookAt(...aim);
    stage.add(source);
    return source;
  }

  const keyLight = softbox('#ffc689', 3.25, 5.1, 2.65, [-.7, 6.2, 2.3]);
  const rimFill = softbox('#b8d9ff', 4.5, 4, 4, [4.5, 3.8, 1.2]);
  const backLight = softbox('#ffb171', 4.2, 4.1, 2.3, [3, 2.8, -4.6]);
  const coolFill = softbox('#cde6ff', 2.8, 8, 2.2, [-4.7, 4.5, 7]);
  const faceFill = softbox('#b5d2ff', 2.25, 6, 3.2, [-1.1, 2.9, 7]);
  const chartFill = softbox('#ffdbad', 2.8, 6.4, 1.1, [-2.3, 1.7, 4.3], [-2, .5, 0]);
  const lowStackFill = softbox('#ffdfb8', 0, .7, 1.5, [-.62, 1.46, 1.82], [.73, .45, -.3]);
  const transmissionKey = directOptics ? softbox('#ffddaa', 0, 3.1, 1.25, [1.45, 3.1, -3.9], [0, 2, .2]) : undefined;
  const outlineKey = directOptics ? softbox('#b9dbff', 0, .42, 4.8, [3.8, 3.1, -2.7], [.6, 2, 0]) : undefined;
  const lowTowerBack = directOptics ? softbox('#ffcf90', 0, 1.85, .42, [.55, .54, -2.05], [.73, .46, -.25]) : undefined;
  const shortStackBack = macroLook === 'classic'
    ? softbox('#ffd3a2', 0, 1.23, .36, [.52, .53, -1.86], [.73, .40, -.22])
    : undefined;
  const tallStackFoot = macroLook === 'classic'
    ? softbox('#ffd2a5', 0, 1.03, .95, [4.42, .68, -1.35], [4.86, .72, -.22])
    : undefined;
  const glintBack = directOptics ? softbox('#ffe4b7', 0, 1.28, .46, [0, 4, -2.2]) : undefined;
  const capitalEdge = overhead ? softbox('#9dc9ff', 0, 1.35, 3.1, [2.7, 1.3, 2.92], [.25, .87, -.5]) : undefined;
  const transmissionBars: THREE.Mesh<THREE.BoxGeometry, THREE.MeshPhysicalMaterial>[] = [];
  const towerRibs: THREE.Mesh<THREE.TubeGeometry, THREE.MeshPhysicalMaterial>[] = [];
  if (overhead) {
    const geometry = new THREE.BoxGeometry(3.45, .035, .054);
    const material = new THREE.MeshPhysicalMaterial({color: '#263c57', emissive: '#a9d7ff', emissiveIntensity: .82, roughness: .24});
    const floorRib = new THREE.MeshPhysicalMaterial({color: '#101929', emissive: '#a9cdf0', emissiveIntensity: 0, roughness: .27});
    for (let index = 0; index < 3; index++) {
      const strip = new THREE.Mesh(geometry, material);
      strip.position.set(-.25 + .18 * index, 2.32, -2.17 - .25 * index);
      strip.rotation.y = -.39;
      stage.add(strip);
      transmissionBars.push(strip);
    }
    const positions = [
      [[2.48, 4.96, -2.04], [3.33, 4.05, -2.04], [3.88, 2.61, -2.04], [4.24, .17, -2.04]],
      [[-.99, .79, -1.70], [-.62, .62, -1.70], [-.28, .38, -1.70], [.37, .12, -1.70]],
    ];
    for (const points of positions) {
      for (const offset of [0, .14]) {
        const curve = new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x + offset, y, z)));
        const rib = new THREE.Mesh(new THREE.TubeGeometry(curve, 32, offset ? .023 : .035, 7), floorRib);
        stage.add(rib);
        towerRibs.push(rib);
      }
    }
  }

  const box = new RoundedBoxGeometry(1, 1, 1, 3, .065);
  const closeGlass = new RoundedBoxGeometry(1, 1, 1, 6, .13);
  const lensGlass = fluted ? flutedGlass(9, .092)
    : macroLook === 'slit' || directOptics || windowOptics ? curvedGlass(closeGlass) : closeGlass;
  const towerGlass = fluted ? flutedGlass(7, .064) : box;
  const clearTowerGlass = macroLook === 'classic' ? flutedGlass(8, .09, Math.PI * 2.6) : towerGlass;
  function glass(color: string, attenuationColor: string, roughness: number, transmission = .96) {
    return new THREE.MeshPhysicalMaterial({
      color, attenuationColor, attenuationDistance: 1.55, roughness, ior: 1.48, transmission, thickness: .32,
    });
  }
  const surfaces: Record<Glass, THREE.MeshPhysicalMaterial> = {
    ink: new THREE.MeshPhysicalMaterial({
      color: '#183b64', roughness: .16, metalness: .48, clearcoat: .68, clearcoatRoughness: .11,
    }),
    amber: glass('#fff1d3', '#ffa24c', .11, .87), honey: glass('#ffe8bb', '#ffaf4d', .14, .78),
    glint: glass('#fff8e9', '#fd9d4b', .045, .995), etched: glass('#ffeabf', '#ec9746', .155, .78),
  };
  const clearTowerSurfaces = {amber: surfaces.amber.clone(), etched: surfaces.etched.clone()};
  const towerColor = new THREE.Color('#fff4df');
  const towerAbsorption = new THREE.Color('#ffb35b');
  surfaces.glint.emissive.set('#ffb86d');
  surfaces.glint.emissiveIntensity = directOptics ? 0 : .02;
  if (directOptics) {
    surfaces.ink.color.set('#598bd2');
    surfaces.ink.attenuationColor.set('#1e61b2');
    surfaces.ink.attenuationDistance = .52;
    surfaces.ink.ior = 1.45;
    surfaces.ink.transmission = .82;
    surfaces.ink.metalness = 0;
    surfaces.ink.roughness = .13;
    surfaces.amber.attenuationColor.set(fluted || overhead ? '#ffdba4' : '#ffc27b');
    surfaces.honey.attenuationColor.set(fluted || overhead ? '#ffdbac' : '#ffd397');
    surfaces.glint.attenuationColor.set(overhead ? '#ffd198' : fluted ? '#ffe0ae' : '#ffd192');
  }
  const transparency = {amber: [.87, .98, .11, .058], honey: [.78, .985, .14, .052], etched: [.78, .95, .155, .094]} as const;
  const shapes = Array.from({length: capacity}, () => {
    const mesh = new THREE.Mesh<THREE.BufferGeometry, THREE.Material>(box, surfaces.ink);
    stage.add(mesh);
    return mesh;
  });
  const placeholder = new THREE.StorageTexture(1, 1);
  const source = texture(placeholder);
  const traceWidth = Math.floor(width * traceScale);
  const traceHeight = Math.floor(height * traceScale);
  function studioBuffer(depthBuffer = false) {
    return new THREE.RenderTarget(traceWidth, traceHeight, {
      type: THREE.HalfFloatType, depthBuffer, colorSpace: THREE.LinearSRGBColorSpace,
      magFilter: THREE.LinearFilter, minFilter: THREE.LinearFilter,
    });
  }
  const guide = studioBuffer(true);
  const guideSurfaces = [0, 1, 2].map(kind => {
    const material = new THREE.MeshBasicNodeMaterial({toneMapped: false});
    material.lights = false;
    const depth = positionView.z.negate().div(120).min(.29).add(kind / 3);
    material.outputNode = vec4(normalWorld.mul(.5).add(.5), depth);
    return material;
  });
  const cycloramaPass = new THREE.MeshBasicNodeMaterial({toneMapped: false});
  cycloramaPass.lights = false;
  cycloramaPass.colorNode = texture(field).rgb.mul(1.75);
  const emptyStage = studioBuffer(true);
  const opticalAmount = uniform(0);
  const interestFocus = uniform(0);
  const stackLighting = uniform(0);
  const nearOptics = uniform(0);
  const windowGlass = uniform(Number(windowOptics));
  const towerOptics = uniform(Number(macroLook === 'classic'));
  const guideMap = texture(guide.texture);
  const horizontal = studioBuffer();
  const polished = studioBuffer();
  const resolved = studioBuffer();
  function polishMaterial(input: ReturnType<typeof texture>, x: number, y: number) {
    const material = new THREE.MeshBasicNodeMaterial({toneMapped: false});
    material.colorNode = cleanupNoise({tex: input, guide: guideMap, coord: uv(), axis: vec2(x, y)}) as THREE.Node<'vec3'>;
    return material;
  }
  const horizontalMaterial = polishMaterial(source, 1, 0);
  const verticalMaterial = polishMaterial(texture(horizontal.texture), 0, 1);
  const horizontalPass = new THREE.QuadMesh(horizontalMaterial);
  const verticalPass = new THREE.QuadMesh(verticalMaterial);
  const lensMaterial = new THREE.MeshBasicNodeMaterial({toneMapped: false});
  lensMaterial.colorNode = combineGlass({
    radiance: texture(polished.texture), background: texture(emptyStage.texture),
    guide: guideMap, coord: uv(), amount: opticalAmount, focus: interestFocus, stacked: stackLighting,
    nearOptics, windowOptics: windowGlass, towerOptics,
  }) as THREE.Node<'vec3'>;
  const lensPass = new THREE.QuadMesh(lensMaterial);
  const presentMaterial = new THREE.MeshBasicNodeMaterial();
  presentMaterial.colorNode = texture(resolved.texture).rgb;
  const presentQuad = new THREE.QuadMesh(presentMaterial);
  const intermediate = new THREE.RenderTarget(1, 1, {depthBuffer: false});
  let displayedState: string | undefined;

  let tracer: WebGPUPathTracer | undefined;
  const prepared = renderer.init().then(() => {
    if (!(renderer.backend as {isWebGPUBackend?: boolean}).isWebGPUBackend) {
      throw new Error('路径追踪小试要求可用的 WebGPU 设备');
    }
    tracer = new WebGPUPathTracer(renderer);
    tracer.stableNoise = true;
    tracer.renderDelay = 0;
    tracer.fadeDuration = 0;
    tracer.minSamples = 0;
    tracer.dynamicLowRes = false;
    tracer.renderScale = traceScale;
    tracer.frameBudget = polished.width * polished.height;
    tracer.maxBounces = 8;
    tracer.maxTransparentBounces = directOptics ? 16 : 8;
    tracer.maxSamples = sampleBudget;
    tracer.filterGlossyFactor = .22;
    tracer.clampDirect = 5.5;
    tracer.clampIndirect = 2.8;
    tracer.transmissiveBackground = TRANSMISSIVE_BACKGROUND_ENVIRONMENT;
    return tracer;
  });

  return {
    async draw(state: StageFrame, cancelled: () => boolean) {
      const raytrace = await prepared;
      if (cancelled()) return;
      const stateKey = JSON.stringify(state);
      if (stateKey === displayedState) {
        presentQuad.render(renderer);
        return;
      }
      displayedState = undefined;
      const {blocks, floor: floorPx, rise, isMacro, sculpture, reveal} = state;
      const polish = isMacro ? 1 : sculpture;
      const direct = directOptics ? overhead && !isMacro ? THREE.MathUtils.smoothstep(sculpture, .33, .97) : polish : 0;
      opticalAmount.value = directOptics ? 0 : polish;
      interestFocus.value = THREE.MathUtils.smoothstep(reveal, .15, .91);
      const macroFocus = isMacro ? interestFocus.value * direct : 0;
      stackLighting.value = sculpture;
      nearOptics.value = Number(isMacro && macroLook !== 'classic');
      for (const glassType of ['amber', 'honey', 'etched'] as const) {
        const [columnTransmission, glassTransmission, columnRoughness, glassRoughness] = transparency[glassType];
        const material = surfaces[glassType];
        material.transmission = directOptics ? THREE.MathUtils.lerp(columnTransmission, .999, direct)
          : THREE.MathUtils.lerp(columnTransmission, glassTransmission, polish);
        material.roughness = directOptics ? THREE.MathUtils.lerp(columnRoughness, .036, direct)
          : THREE.MathUtils.lerp(columnRoughness, glassRoughness, polish);
        material.attenuationDistance = THREE.MathUtils.lerp(1.55, fluted || overhead ? .92 : .56, direct);
      }
      const clearMix = THREE.MathUtils.smoothstep(sculpture, .06, .82);
      for (const type of ['amber', 'etched'] as const) {
        const original = surfaces[type];
        const clear = clearTowerSurfaces[type];
        clear.color.lerpColors(original.color, towerColor, clearMix);
        clear.attenuationColor.lerpColors(original.attenuationColor, towerAbsorption, clearMix);
        clear.attenuationDistance = THREE.MathUtils.lerp(original.attenuationDistance, .94, clearMix);
        clear.roughness = THREE.MathUtils.lerp(original.roughness, .038, clearMix);
        clear.transmission = THREE.MathUtils.lerp(original.transmission, 1, clearMix);
      }
      stage.environmentIntensity = .52 - .20 * sculpture - .18 * direct;
      keyLight.intensity = 3.25 - 1.7 * sculpture - 1.1 * direct;
      backLight.intensity = 4.2 - 2.4 * sculpture - (overhead ? isMacro ? 2.9 : 1.04 * direct : 2.7 * macroFocus);
      rimFill.intensity = 4.5 - 1.25 * sculpture - (isMacro && (macroLook === 'slit' || windowOptics) ? 2.2 : 1.9 * direct);
      coolFill.intensity = 2.8 - 1.25 * sculpture - .95 * direct;
      faceFill.intensity = 2.25 - 1.3 * sculpture - (isMacro && macroLook === 'slit' ? 1.35 : .83 * direct);
      chartFill.intensity = 2.8 - 2.07 * sculpture;
      lowStackFill.intensity = 2.4 * sculpture;
      if (shortStackBack) shortStackBack.intensity = 4.4 * sculpture;
      if (tallStackFoot) tallStackFoot.intensity = 2.7 * sculpture;
      if (capitalEdge) capitalEdge.intensity = isMacro ? 1.45 - .9 * reveal : 0;
      if (transmissionKey && outlineKey && lowTowerBack) {
        transmissionKey.position.set(1.45 - .87 * macroFocus, 3.1 + .77 * macroFocus, -3.9 + .93 * macroFocus);
        transmissionKey.lookAt(.10, 2.3 + 1.30 * macroFocus, -.28);
        transmissionKey.width = 3.1 - 1.8 * macroFocus;
        transmissionKey.height = 1.25 - .68 * macroFocus;
        const keyPower = isMacro ? overhead ? 5.2 * (1 - .82 * macroFocus) : 6.1 + 6.7 * macroFocus
          : overhead ? 1.18 : 5.9;
        transmissionKey.intensity = keyPower * direct * (fluted ? .48 : 1);
        outlineKey.intensity = (isMacro ? 2.2 : overhead ? 2.14 : 3.8) * direct * (fluted ? .78 : 1);
        lowTowerBack.intensity = (overhead ? 1.42 : fluted ? 3 : 4.6) * direct * (isMacro ? 0 : 1);
      }
      const camera = isMacro ? nearCamera : chartCamera;
      towerRibs.forEach(rib => { rib.visible = !isMacro && direct > .001; });
      if (towerRibs[0]) towerRibs[0].material.emissiveIntensity = 1.02 * direct * (isMacro ? 0 : 1);
      if (!isMacro) {
        chartCamera.top = floorPx * .01;
        chartCamera.bottom = (floorPx - 1080) * .01;
        chartCamera.rise = rise + (overhead ? .09 * sculpture : 0);
        chartCamera.updateProjectionMatrix();
      }
      shapes.forEach((mesh, index) => {
        const block = blocks[index];
        mesh.visible = !!block && block.height > .02;
        if (!mesh.visible) return;
        const lowStack = !isMacro && index < half;
        const seam = overhead && isMacro && block.glass === 'ink' ? 2.4
          : Math.min(.55 + (lowStack ? .98 : .60) * sculpture,
            block.height * (.10 + (lowStack ? .12 : .04) * sculpture));
        mesh.geometry = isMacro && block.glass !== 'ink' ? lensGlass
          : sculpture > .001 ? (lowStack ? towerGlass : clearTowerGlass) : box;
        mesh.material = macroLook === 'classic' && !isMacro && !lowStack && sculpture > .001
          ? clearTowerSurfaces[block.glass === 'etched' ? 'etched' : 'amber']
          : surfaces[block.glass];
        mesh.rotation.x = block.pitch ?? 0;
        mesh.rotation.y = block.yaw ?? 0;
        let cut = 0;
        if (isMacro && block.glass === 'glint' && macroLook !== 'classic') cut = 1;
        if (isMacro && block.glass === 'honey' && macroLook === 'cut') {
          cut = THREE.MathUtils.smoothstep(block.pitch ?? 0, 0, .245);
        }
        const lowRib = lowStack && block.glass === 'etched' && macroLook === 'classic'
          ? .065 * sculpture : 0;
        const widthFactor = 1 - .15 * cut;
        const depthFactor = 1 - .18 * cut;
        const height = block.height / (widthFactor * depthFactor);
        mesh.scale.set(block.width * (widthFactor + lowRib) * .01,
          Math.max(.0002, (height - seam) * .01), block.depth * depthFactor * .01);
        mesh.position.set((block.x - (isMacro ? 1087 : 960)) * .01,
          (floorPx - block.y + (height - block.height) / 2) * .01, ((block.z ?? 0) - block.depth / 2) * .01);
      });
      const illuminated = isMacro
        ? [blocks.findIndex(block => block.glass === 'honey'), blocks.findIndex(block => block.glass === 'glint')]
        : [0, half];
      const floater = isMacro ? shapes[illuminated[1]] : undefined;
      if (transmissionBars.length) {
        transmissionBars[0].material.emissiveIntensity = .82 - .23 * reveal;
        const position = floater?.position;
        const depth = position ? .69 / (nearCamera.position.y - position.y) : 0;
        transmissionBars.forEach((strip, index) => {
          strip.visible = isMacro;
          strip.scale.x = 1 - .45 * reveal;
          const spread = index - 1;
          const startX = -.25 + .18 * index;
          const startZ = -2.17 - .25 * index;
          strip.position.set(startX, 2.32, startZ);
          if (position && floater?.visible) {
            const rearX = position.x + (position.x - nearCamera.position.x) * depth;
            const rearZ = position.z + (position.z - nearCamera.position.z) * depth;
            strip.position.x = THREE.MathUtils.lerp(startX, rearX + .09 * spread, reveal);
            strip.position.y = THREE.MathUtils.lerp(2.32, position.y - .69, reveal);
            strip.position.z = THREE.MathUtils.lerp(startZ, rearZ - .16 * spread, reveal);
          }
        });
      }
      if (glintBack) {
        glintBack.intensity = (overhead ? 1.1 : fluted ? 3.6 : 7.2) * macroFocus;
        if (floater?.visible) {
          const {x, y, z} = floater.position;
          glintBack.position.set(x + .32, y + .55, z - 1.05);
          glintBack.lookAt(x, y, z);
        }
      }
      lightFromGlass(illuminated.flatMap((index, element) => {
        const source = shapes[index];
        const power = isMacro ? .74 * (element === 0 ? 1 - reveal : reveal) : (element === 0 ? .27 : .79) * sculpture;
        return source?.visible && power > .001 ? [{
          x: source.position.x, z: source.position.z, breadth: source.scale.x,
          power: power / (1 + source.position.y * .25),
        }] : [];
      }), isMacro, reveal, sculpture, camera);
      raytrace.setScene(stage, camera);
      const samples = state.motionSamples ?? sampleBudget;
      raytrace.maxSamples = samples;
      // 完整颜色保留在路径追踪缓冲区，只在该帧准备完成时绘制到画布。
      renderer.setRenderTarget(intermediate);
      try {
        for (let sample = 0; sample < samples * 3 && !cancelled(); sample++) {
          raytrace.renderSample();
          await yieldRenderer();
        }
      } finally {
        renderer.setRenderTarget(null);
      }
      if (!cancelled()) {
        const counts = await raytrace.getSampleCountsAsync();
        canvas.dataset.samples = counts.avg.toFixed(2);
        if (counts.avg < 1) throw new Error('路径追踪没有形成有效样本');
        if (!raytrace.target) throw new Error('路径追踪色彩缓冲缺失');
        source.value = raytrace.target;
        const litSurfaces = shapes.filter(mesh => mesh.visible);
        const lighting = litSurfaces.map(mesh => mesh.material);
        const floorMaterial = floor.material;
        try {
          if (opticalAmount.value > .001) {
            // 每个视点都实绘一份未遮挡的棚面，玻璃位置从这份画面按法线取折射光。
            litSurfaces.forEach(mesh => { mesh.visible = false; });
            floor.material = cycloramaPass;
            renderer.setRenderTarget(emptyStage);
            renderer.render(stage, camera);
          }
          // 法线缓冲同时区分蓝底座、一般玻璃和次年悬片，避免跨过轮廓滤色。
          floor.material = guideSurfaces[0];
          litSurfaces.forEach((mesh, index) => {
            mesh.visible = true;
            const surface = lighting[index];
            mesh.material = guideSurfaces[surface === surfaces.ink ? 0 : surface === surfaces.glint ? 2 : 1];
          });
          renderer.setRenderTarget(guide);
          renderer.render(stage, camera);
          renderer.setRenderTarget(horizontal);
          horizontalPass.render(renderer);
          renderer.setRenderTarget(polished);
          verticalPass.render(renderer);
          renderer.setRenderTarget(resolved);
          lensPass.render(renderer);
        } finally {
          floor.material = floorMaterial;
          litSurfaces.forEach((mesh, index) => { mesh.material = lighting[index]; mesh.visible = true; });
          renderer.setRenderTarget(null);
        }
        presentQuad.render(renderer);
        displayedState = stateKey;
      }
    },
    dispose() {
      tracer?.dispose();
      box.dispose();
      closeGlass.dispose();
      if (lensGlass !== closeGlass) lensGlass.dispose();
      if (towerGlass !== box) towerGlass.dispose();
      if (clearTowerGlass !== towerGlass) clearTowerGlass.dispose();
      Object.values(clearTowerSurfaces).forEach(material => material.dispose());
      transmissionBars[0]?.geometry.dispose();
      transmissionBars[0]?.material.dispose();
      towerRibs.forEach(rib => rib.geometry.dispose());
      towerRibs[0]?.material.dispose();
      floor.geometry.dispose();
      floor.material.dispose();
      field.dispose();
      environment.dispose();
      guideSurfaces.forEach(material => material.dispose());
      guide.dispose();
      cycloramaPass.dispose();
      emptyStage.dispose();
      lensMaterial.dispose();
      resolved.dispose();
      horizontalMaterial.dispose();
      verticalMaterial.dispose();
      horizontal.dispose();
      presentMaterial.dispose();
      polished.dispose();
      placeholder.dispose();
      intermediate.dispose();
      Object.values(surfaces).forEach(surface => surface.dispose());
      renderer.dispose();
    },
  };
}

export function TracedCanvas({width, height, state, samples, capacity, macroLook = 'classic', active = true}: {
  width: number; height: number; state: StageFrame; samples: number; capacity: number; macroLook?: MacroLook; active?: boolean;
}) {
  const {ready, waitForFrame} = useSceneContext();
  const canvas = useRef<HTMLCanvasElement>(null);
  const studio = useRef<ReturnType<typeof startStudio> | null>(null);

  useLayoutEffect(() => {
    if (!canvas.current) return;
    studio.current = startStudio(canvas.current, width, height, samples, capacity, macroLook);
    return () => { studio.current?.dispose(); studio.current = null; };
  }, [capacity, height, macroLook, samples, width]);

  useLayoutEffect(() => {
    if (!active) return;
    let cancelled = false;
    const pending = studio.current?.draw(state, () => cancelled);
    if (pending) {
      waitForFrame(pending);
      ready();
    }
    return () => { cancelled = true; };
  }, [active, state, ready, waitForFrame]);

  return <canvas ref={canvas} aria-hidden="true"
    style={{position: 'absolute', inset: 0, width, height, display: active ? 'block' : 'none'}}/>;
}

export default function PathtraceStudy({width, height, props}: CodeSceneProps) {
  const {elapsedSeconds} = useSceneContext();
  const {blocks, reveal} = macroState(elapsedSeconds);
  const samples = typeof props.samples === 'number' ? Math.min(72, Math.max(8, props.samples)) : 24;
  const extra = fade(2.1, 2.75, elapsedSeconds);
  return (
    <div style={{position: 'relative', width, height, background: '#142438', color: '#f4efe9', overflow: 'hidden', fontFamily: '"M2V Inter", "M2V Sans"'}}>
      <TracedCanvas width={width} height={height} state={{blocks, floor: 790, rise: .37, isMacro: true, sculpture: 0, reveal}} samples={samples} capacity={blocks.length}/>
      <div style={{position: 'absolute', width: 1920, height: 1080, inset: 0, transform: `scale(${width / 1920},${height / 1080})`, transformOrigin: 'top left'}}>
        <div style={{position: 'absolute', left: 135, top: 168, color: '#ffd18f', fontSize: 45, fontWeight: 540}}>年利率 10%</div>
        <div style={{position: 'absolute', left: 128, top: 258, fontSize: 97, lineHeight: 1.12, fontWeight: 650, letterSpacing: '-.061em'}}>利息也开始<br/>赚利息</div>
        <div style={{position: 'absolute', left: 140, bottom: 222, color: '#ffd18f', fontSize: 96, lineHeight: 1.05, fontWeight: 530, letterSpacing: '-.047em'}}>
          {extra > .5 ? '+100 元' : '+1,000 元'}
          <div style={{fontSize: 37, color: '#f4efe9', letterSpacing: 0, marginTop: 19}}>{extra > .5 ? '来自首年的 1,000 元' : '首年收益'}</div>
        </div>
      </div>
    </div>
  );
}
