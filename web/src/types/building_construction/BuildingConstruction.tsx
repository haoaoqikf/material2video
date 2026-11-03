/**
 * 两层框架住宅建造示意：构件级三维、多镜头与可读性覆盖层。
 *
 * 场景只在挂载时构建一次；每帧只由 `frame` 更新构件变换、相机、可见性
 * 与标签，不读取上一帧、挂钟或随机数。
 */
import {useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {
  baseOpacity, contactShadowTexture, createComponentObject, createGhost, createMaterials,
} from './geometry';
import {
  boxBounds, buildComponents, cameraAt, componentBox, currentStep, hiddenSet, ownerMap,
  shotAt, smooth, stepIds, transformFor,
  type Component, type House, type Shot, type Stage, type Step,
} from './model';

export type BuildingProps = {
  schemaVersion: number;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  building: {schemaVersion: number; canvas: {width: number; height: number}; house: House};
  construction: {
    schemaVersion: number;
    durationSeconds: number;
    fps: number;
    stages: Stage[];
    shots: Shot[];
    initial: string[];
    steps: Step[];
  };
  assets: {schemaVersion: number; assets: {path: string; sha256: string}[]};
  components: Component[];
};

type SceneObject = {
  component: Component;
  group: THREE.Group;
  material: THREE.Material;
  edges: THREE.LineSegments;
  baseOpacity: number;
};

type SceneState = {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  objects: SceneObject[];
  owners: Map<string, Step>;
  components: Component[];
  house: House;
  ghostMaterial: THREE.LineBasicMaterial;
};

const STAGE_LABEL_SIZE = 15;
const NOTE_SIZE = 17;
const BG = 'linear-gradient(180deg, #eef1f2 0%, #e3e7e5 58%, #d7dcd8 100%)';

function buildScene(canvas: HTMLCanvasElement, props: BuildingProps): SceneState {
  const house = props.building.house;
  const components = buildComponents(house);
  const expected = props.components.map((item) => `${item.id}:${item.kind}:${item.floor}`).sort();
  const actual = components.map((item) => `${item.id}:${item.kind}:${item.floor}`).sort();
  if (expected.join('|') !== actual.join('|')) {
    throw new Error('前端构件图与 Python 校验器不一致；请同步 components.py 与 model.ts');
  }
  const owners = ownerMap(components, props.construction.steps);
  const materials = createMaterials();
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true});
  renderer.setPixelRatio(1);
  renderer.setSize(props.width, props.height, false);
  renderer.setClearAlpha(0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, props.width / props.height, 0.1, 240);

  scene.add(new THREE.HemisphereLight(0xe9eff3, 0x8c806d, 1.05));
  scene.add(new THREE.AmbientLight(0xffffff, 0.16));
  const sun = new THREE.DirectionalLight(0xfff3dd, 2.35);
  sun.position.set(14, 24, 12);
  sun.target.position.set(0, 3, 0);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -20;
  sun.shadow.camera.right = 20;
  sun.shadow.camera.top = 22;
  sun.shadow.camera.bottom = -12;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 70;
  sun.shadow.bias = -0.0002;
  sun.shadow.normalBias = 0.05;
  sun.shadow.radius = 2;
  scene.add(sun, sun.target);
  const fill = new THREE.DirectionalLight(0xdce8f0, 0.45);
  fill.position.set(-16, 10, -12);
  scene.add(fill);

  const contact = new THREE.Mesh(
    new THREE.PlaneGeometry(house.width + 12, house.depth + 12),
    new THREE.MeshBasicMaterial({
      map: contactShadowTexture(), transparent: true, opacity: 0.62,
      depthWrite: false, color: 0x000000,
    }),
  );
  contact.rotation.x = -Math.PI / 2;
  contact.position.y = 0.02;
  scene.add(contact);

  const objects: SceneObject[] = [];
  for (const component of components) {
    const step = owners.get(component.id);
    const spec = componentBox(house, component);
    const transparent = spec.material === 'glass' || step?.action === 'insert';
    const object = createComponentObject(spec, materials, transparent);
    object.group.userData.componentId = component.id;
    scene.add(object.group);
    objects.push({
      component,
      group: object.group,
      material: object.material,
      edges: object.edges,
      baseOpacity: baseOpacity(spec.material),
    });
  }
  const ghost = createGhost(house);
  scene.add(ghost.group);
  return {renderer, scene, camera, objects, owners, components, house, ghostMaterial: ghost.material};
}

function drawFrame(state: SceneState, frame: number, props: BuildingProps): void {
  const seconds = frame / props.fps;
  const shot = shotAt(props.construction.shots, seconds);
  const cameraSpec = cameraAt(shot, seconds);
  const {camera, scene, renderer, house} = state;
  camera.fov = cameraSpec.fov;
  camera.position.set(...cameraSpec.position);
  camera.lookAt(new THREE.Vector3(...cameraSpec.target));
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  const hidden = hiddenSet(state.components, shot);
  for (const object of state.objects) {
    const step = state.owners.get(object.component.id);
    const transform = transformFor(house, object.component, step, seconds);
    object.group.position.set(...transform.position);
    object.group.rotation.set(...transform.rotation);
    object.group.scale.set(...transform.scale);
    object.group.visible = step ? seconds >= step.startSeconds && !hidden.has(object.component.id)
      : !hidden.has(object.component.id);
    const opacity = object.baseOpacity * (step?.action === 'insert' ? transform.opacity : 1);
    object.material.opacity = opacity;
    object.material.transparent = opacity < 1;
    object.edges.visible = object.group.visible;
    (object.edges.material as THREE.LineBasicMaterial).opacity = 0.24 * opacity;
  }
  const duration = props.construction.durationSeconds;
  state.ghostMaterial.opacity = 0.14 * (1 - smooth((seconds - (duration - 7)) / 4));
  renderer.render(scene, camera);
}

export function BuildingConstruction(props: BuildingProps) {
  const frame = useCurrentFrame();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<SceneState | null>(null);
  const [ready, setReady] = useState(false);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const handle = delayRender('构建建筑三维场景');
    let disposed = false;
    try {
      const state = buildScene(canvas, props);
      stateRef.current = state;
      setReady(true);
      const finish = () => { if (!disposed) continueRender(handle); };
      if (document.fonts?.ready) document.fonts.ready.then(finish).catch(finish);
      else finish();
    } catch (error) {
      cancelRender(error instanceof Error ? error : new Error(String(error)));
    }
    return () => {
      disposed = true;
      const state = stateRef.current;
      stateRef.current = null;
      if (state) {
        state.renderer.dispose();
        state.scene.traverse((item) => {
          if (item instanceof THREE.Mesh || item instanceof THREE.LineSegments) {
            item.geometry.dispose();
            const material = item.material;
            if (Array.isArray(material)) material.forEach((entry) => entry.dispose());
            else material.dispose();
          }
        });
      }
    };
  }, [props.width, props.height, props.building.house, props.construction.steps,
    props.components]);

  useEffect(() => {
    if (!ready || !stateRef.current) return;
    const handle = delayRender('绘制建筑当前帧');
    drawFrame(stateRef.current, frame, props);
    continueRender(handle);
  }, [frame, ready, props]);

  const overlay = useMemo(() => overlayFor(frame, props), [frame, props]);
  return <AbsoluteFill style={{background: BG}}>
    <canvas ref={canvasRef} width={props.width} height={props.height}
      data-m2v-building-canvas="two-story-house"
      style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />
    <div style={{
      position: 'absolute', inset: 0, pointerEvents: 'none',
      background: 'radial-gradient(ellipse at 50% 46%, rgba(255,255,255,0) 46%, rgba(43,47,51,0.16) 100%)',
    }} />
    <svg width={props.width} height={props.height} viewBox={`0 0 ${props.width} ${props.height}`}
      style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} aria-hidden>
      {overlay.anchor && overlay.label ? <>
        <line x1={overlay.anchor.x} y1={overlay.anchor.y}
          x2={overlay.label.x} y2={overlay.label.y}
          stroke="#3a3f43" strokeWidth={1.1} opacity={0.55}/>
        <circle cx={overlay.anchor.x} cy={overlay.anchor.y} r={4} fill="#c79a45" opacity={0.9}/>
      </> : null}
      {overlay.scaleBar > 0 ? <>
        <line x1={140} y1={props.height - 92} x2={140 + overlay.scaleBar} y2={props.height - 92}
          stroke="#3a3f43" strokeWidth={2} opacity={0.72}/>
        <line x1={140} y1={props.height - 98} x2={140} y2={props.height - 86}
          stroke="#3a3f43" strokeWidth={2} opacity={0.72}/>
        <line x1={140 + overlay.scaleBar} y1={props.height - 98}
          x2={140 + overlay.scaleBar} y2={props.height - 86}
          stroke="#3a3f43" strokeWidth={2} opacity={0.72}/>
      </> : null}
    </svg>
    {overlay.label ? <div style={{
      position: 'absolute', left: overlay.label.x, top: overlay.label.y,
      transform: 'translate(-50%, -50%)', fontFamily: 'var(--m2v-sans, sans-serif)',
      fontSize: 20, lineHeight: 1.25, color: '#2b2f33', whiteSpace: 'nowrap',
      opacity: 0.92, textShadow: '0 0 6px rgba(255,255,255,0.95)',
    }}>{overlay.label.text}</div> : null}
    {overlay.scaleBar > 0 ? <div style={{
      position: 'absolute', left: 140 + overlay.scaleBar + 10, top: props.height - 104,
      fontFamily: 'var(--m2v-sans, sans-serif)', fontSize: NOTE_SIZE, color: '#4a4f52',
      opacity: 0.72,
    }}>3 m</div> : null}
    <div style={{
      position: 'absolute', right: 48, bottom: 72, fontFamily: 'var(--m2v-sans, sans-serif)',
      fontSize: NOTE_SIZE, color: '#4a4f52', opacity: 0.66,
    }}>{overlay.cutaway ? '剖切观察 · 建造过程示意' : '建造过程示意'}</div>
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: 0, height: 104,
      pointerEvents: 'none',
      background: 'linear-gradient(to top, rgba(246,247,246,0.94), rgba(246,247,246,0))',
    }} />
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: 0, height: 58,
      display: 'flex', gap: 2, padding: '0 48px', alignItems: 'flex-end',
      fontFamily: 'var(--m2v-sans, sans-serif)',
    }}>
      {overlay.stages.map((stage) => <div key={stage.id} style={{
        flex: stage.endSeconds - stage.startSeconds,
        display: 'flex', flexDirection: 'column', gap: 5,
      }}>
        <div style={{
          height: 3, background: stage.current ? '#c79a45' : '#6e7477',
          opacity: stage.current ? 0.95 : stage.done ? 0.5 : 0.22,
        }} />
        <div style={{
          fontSize: STAGE_LABEL_SIZE, color: stage.current ? '#1f2326' : '#3a3f43',
          opacity: stage.current ? 1 : stage.done ? 0.82 : 0.68,
          fontWeight: stage.current ? 600 : 400,
          whiteSpace: 'nowrap', paddingBottom: 16,
        }}>{stage.label}</div>
      </div>)}
    </div>
  </AbsoluteFill>;
}

type Overlay = {
  stages: (Stage & {current: boolean; done: boolean})[];
  anchor: {x: number; y: number} | null;
  label: {x: number; y: number; text: string} | null;
  scaleBar: number;
  cutaway: boolean;
};

function project(point: [number, number, number], camera: THREE.PerspectiveCamera,
                 width: number, height: number): {x: number; y: number} {
  const vector = new THREE.Vector3(...point).project(camera);
  return {x: (vector.x + 1) / 2 * width, y: (1 - vector.y) / 2 * height};
}

function overlayFor(frame: number, props: BuildingProps): Overlay {
  const seconds = frame / props.fps;
  const stages = props.construction.stages;
  const current = stages.find((stage) => seconds >= stage.startSeconds && seconds < stage.endSeconds)
    ?? stages[stages.length - 1];
  const stageRows = stages.map((stage) => ({
    ...stage,
    current: stage.id === current.id,
    done: stage.endSeconds <= seconds,
  }));
  const shot = shotAt(props.construction.shots, seconds);
  const cameraSpec = cameraAt(shot, seconds);
  const camera = new THREE.PerspectiveCamera(cameraSpec.fov, props.width / props.height, 0.1, 240);
  camera.position.set(...cameraSpec.position);
  camera.lookAt(new THREE.Vector3(...cameraSpec.target));
  camera.updateMatrixWorld();
  const components = buildComponents(props.building.house);
  const active = props.construction.steps.filter((step) =>
    seconds >= step.startSeconds && seconds < step.endSeconds);
  let anchor: {x: number; y: number} | null = null;
  let label: {x: number; y: number; text: string} | null = null;
  if (active.length > 0) {
    const step = currentStep(props.construction.steps, seconds);
    if (seconds - step.startSeconds < 0.3) {
      return {stages: stageRows, anchor: null, label: null,
        scaleBar: scaleBarFor(camera, props), cutaway: shot.id === 'roof-cutaway'};
    }
    const primary = stepIds(step, components)[0];
    const component = components.find((item) => item.id === primary);
    if (component) {
      const anchorComponent = component.kind === 'roof'
        ? components.find((item) => item.id === 'roof-ridge') ?? component
        : component;
      const box = boxBounds(props.building.house, anchorComponent);
      const anchorPoint: [number, number, number] = component.kind === 'wall'
        ? [box.center[0], box.center[1] + box.size[1] * 0.35, box.center[2]]
        : component.kind === 'yard'
          ? [box.center[0], box.center[1], box.center[2]]
          : box.center;
      const projected = project(anchorPoint, camera, props.width, props.height);
      anchor = {
        x: Math.min(props.width - 80, Math.max(80, projected.x)),
        y: Math.min(props.height - 150, Math.max(80, projected.y)),
      };
      const left = anchor.x < props.width / 2;
      const yard = component.kind === 'yard';
      label = {
        x: left ? Math.min(props.width - 240, anchor.x + 120) : Math.max(240, anchor.x - 120),
        y: yard ? Math.min(props.height - 150, anchor.y + 54)
          : Math.min(props.height - 170, Math.max(110, anchor.y - 92)),
        text: step.label ?? step.action,
      };
    }
  }
  return {stages: stageRows, anchor, label, scaleBar: scaleBarFor(camera, props),
    cutaway: shot.id === 'roof-cutaway'};
}

function scaleBarFor(camera: THREE.PerspectiveCamera, props: BuildingProps): number {
  const halfD = props.building.house.depth / 2;
  const from = project([0, 0.02, halfD + 1], camera, props.width, props.height);
  const to = project([3, 0.02, halfD + 1], camera, props.width, props.height);
  return Math.max(24, Math.abs(to.x - from.x));
}
