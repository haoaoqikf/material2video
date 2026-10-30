/**
 * SU7 汽车展示：本地 glTF、按帧求值的环绕镜头、车轮与视觉疾驰。
 * 画面只依赖当前帧；模型解码完成前 delayRender 阻止截图。
 */
import { useEffect, useRef, useState } from 'react';
import { AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame } from 'remotion';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';

export type VehicleShowcaseProps = {
  schemaVersion: number;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  showcase: {
    schemaVersion: number;
    canvas: {width: number; height: number};
    durationSeconds: number;
    fps: number;
    model: string;
    wheelNodes: string[];
    camera: {distance: number; height: number; orbitStartDegrees: number; orbitEndDegrees: number};
    effects: {speedStartSeconds: number; speedEndSeconds: number; fadeOutSeconds: number};
  };
  modelGltf: string;
};

type SceneState = {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  wheels: THREE.Group[];
  speedLines: THREE.LineSegments;
};

function smooth(value: number): number {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

function setFrame(state: SceneState, frame: number, props: VehicleShowcaseProps): void {
  const {camera: cameraSpec, effects} = props.showcase;
  const seconds = frame / props.fps;
  const orbit = smooth((seconds - 4) / 12);
  const angle = THREE.MathUtils.degToRad(
    cameraSpec.orbitStartDegrees
      + (cameraSpec.orbitEndDegrees - cameraSpec.orbitStartDegrees) * orbit);
  const speed = smooth((seconds - effects.speedStartSeconds)
    / Math.max(0.01, effects.speedEndSeconds - effects.speedStartSeconds));
  const close = seconds < 4 ? smooth(seconds / 4) : 0;
  const distance = cameraSpec.distance + close * 1.6 - speed * 0.7;
  const height = cameraSpec.height + close * 0.35;
  const shake = speed * 0.045;
  state.camera.position.set(
    Math.sin(angle) * distance + Math.sin(seconds * 31) * shake,
    height + Math.sin(seconds * 17) * shake,
    Math.cos(angle) * distance + Math.cos(seconds * 23) * shake,
  );
  state.camera.lookAt(0, 0.65, 0);
  state.camera.fov = 38 + close * 4 - speed * 2;
  state.camera.updateProjectionMatrix();
  state.wheels.forEach((wheel) => {
    wheel.rotation.z = -seconds * (2.5 + speed * 22);
  });
  const fade = seconds > props.showcase.durationSeconds - effects.fadeOutSeconds
    ? 1 - smooth((seconds - (props.showcase.durationSeconds - effects.fadeOutSeconds))
      / effects.fadeOutSeconds)
    : 1;
  state.speedLines.visible = speed > 0.01 && fade > 0.01;
  const material = state.speedLines.material as THREE.LineBasicMaterial;
  material.opacity = 0.24 * speed * fade;
  state.speedLines.rotation.y = angle;
  state.renderer.domElement.style.opacity = String(fade);
  state.renderer.render(state.scene, state.camera);
}

export function VehicleShowcase(props: VehicleShowcaseProps) {
  const frame = useCurrentFrame();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<SceneState | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false});
    renderer.setSize(props.width, props.height, false);
    renderer.setPixelRatio(1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#07090b');
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.add(new THREE.HemisphereLight('#d8ecff', '#18130d', 0.8));
    const key = new THREE.DirectionalLight('#ffffff', 4.2);
    key.position.set(5, 8, 6);
    scene.add(key);
    const rim = new THREE.PointLight('#45cfff', 30, 30);
    rim.position.set(-6, 3, -5);
    scene.add(rim);

    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(30, 96),
      new THREE.MeshStandardMaterial({color: '#111519', roughness: 0.28, metalness: 0.45}),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.02;
    scene.add(floor);
    const grid = new THREE.GridHelper(40, 40, '#22303a', '#151c21');
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.32;
    grid.position.y = 0;
    scene.add(grid);

    const lineGeometry = new THREE.BufferGeometry();
    const points: number[] = [];
    for (let index = 0; index < 48; index += 1) {
      const angle = (index / 48) * Math.PI * 2;
      const inner = 3.8 + (index % 3) * 0.5;
      const outer = 16 + (index % 5) * 1.2;
      points.push(Math.cos(angle) * inner, 0.015, Math.sin(angle) * inner,
        Math.cos(angle) * outer, 0.015, Math.sin(angle) * outer);
    }
    lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    const speedLines = new THREE.LineSegments(lineGeometry,
      new THREE.LineBasicMaterial({color: '#74d8ff', transparent: true, opacity: 0}));
    scene.add(speedLines);

    const camera = new THREE.PerspectiveCamera(38, props.width / props.height, 0.1, 120);
    const handle = delayRender('加载 SU7 模型', {timeoutInMilliseconds: 120_000});
    const loader = new GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);
    loader.parse(props.modelGltf, '', (gltf) => {
      const model = gltf.scene;
      const bounds = new THREE.Box3().setFromObject(model);
      const size = bounds.getSize(new THREE.Vector3());
      const center = bounds.getCenter(new THREE.Vector3());
      const scale = 5.4 / Math.max(size.x, size.z);
      model.scale.setScalar(scale);
      model.position.set(-center.x * scale, -bounds.min.y * scale, -center.z * scale);
      scene.add(model);
      model.updateWorldMatrix(true, true);
      const wheels = props.showcase.wheelNodes.flatMap((name) => {
        const found = model.getObjectByName(name);
        if (!found) return [];
        const box = new THREE.Box3().setFromObject(found);
        const center = box.getCenter(new THREE.Vector3());
        const pivot = new THREE.Group();
        scene.add(pivot);
        pivot.position.copy(center);
        pivot.updateWorldMatrix(true, true);
        pivot.attach(found);
        return [pivot];
      });
      stateRef.current = {renderer, scene, camera, wheels, speedLines};
      setReady(true);
      continueRender(handle);
    }, (error) => {
      cancelRender(error instanceof Error ? error : new Error('SU7 模型加载失败'));
    });
    return () => {
      pmrem.dispose();
      renderer.dispose();
      scene.traverse((item) => {
        if (item instanceof THREE.Mesh) {
          item.geometry.dispose();
          const materials = Array.isArray(item.material) ? item.material : [item.material];
          materials.forEach((material) => material.dispose());
        }
      });
      stateRef.current = null;
    };
  }, [props.modelGltf, props.width, props.height, props.showcase.wheelNodes]);

  useEffect(() => {
    const state = stateRef.current;
    if (!ready || !state) return;
    const handle = delayRender('渲染 SU7 当前帧');
    setFrame(state, frame, props);
    continueRender(handle);
  }, [frame, ready, props]);

  return <AbsoluteFill style={{background: '#07090b'}}>
    <canvas ref={canvasRef} width={props.width} height={props.height}
      data-m2v-vehicle-canvas="su7" style={{width: '100%', height: '100%'}} />
  </AbsoluteFill>;
}
