/** 本轮图片试制独用的透明摄影棚；复用现有圆片几何与环境，正式入口不引用。 */
import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three';
import {createCapitalGeometry} from './capital-geometry';
import {createStudioEnvironment} from './capital-lighting';
import {designFrame} from '../capital-state';
import {CAPITAL_STYLE, RESULT_LAYOUT} from '../capital-style';

export type RedesignVariant = 0 | 1 | 2;
const STAGES = [
  {scale: 2.35, left: 880, right: 1490, base: 858, exposure: 1.02, dark: false},
  {scale: 2.7, left: 520, right: 1370, base: 915, exposure: .91, dark: true},
  {scale: 2.05, left: 1140, right: 1600, base: 858, exposure: 1.08, dark: false},
] as const;

function build(canvas: HTMLCanvasElement, variant: RedesignVariant, density: number) {
  const style = STAGES[variant];
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true});
  renderer.setSize(1920, 1080, false);
  renderer.setPixelRatio(density);
  renderer.setClearColor('#000000', 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = style.exposure;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const environment = createStudioEnvironment(renderer, !style.dark);
  scene.environment = environment.texture;
  scene.environmentIntensity = style.dark ? 1.15 : .85;
  const elevation = .6;
  const focusY = CAPITAL_STYLE.floorY + ((style.base - 540) / style.scale
    - RESULT_LAYOUT.rowDepth * Math.sin(elevation)) / Math.cos(elevation);
  const camera = new THREE.OrthographicCamera(-960, 960, 540, -540, .1, 4000);
  camera.position.set(960, focusY + 1800 * Math.sin(elevation), 1800 * Math.cos(elevation));
  camera.lookAt(960, focusY, 0);
  camera.zoom = style.scale;
  camera.updateProjectionMatrix();

  const key = new THREE.DirectionalLight(style.dark ? '#c8e2ff' : '#fff6e5', style.dark ? 2.2 : 2.7);
  key.position.set(500, 2000, 700);
  key.target.position.set(960, CAPITAL_STYLE.floorY, 0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {left: -650, right: 650, top: 650, bottom: -650, near: .1, far: 3000});
  key.shadow.bias = -.0001;
  key.shadow.normalBias = .04;
  key.shadow.radius = 4;
  scene.add(key, key.target);
  const fill = new THREE.DirectionalLight(style.dark ? '#428cff' : '#dce6f4', style.dark ? .8 : .7);
  fill.position.set(1800, 800, -300);
  scene.add(fill, new THREE.HemisphereLight('#dce6ef', '#6b5b40', .3));

  // 透明接触影让网页的建筑/海报背景成为空间的一部分，而非整图贴面。
  const floorGeometry = new THREE.PlaneGeometry(5000, 5000);
  const floorMaterial = new THREE.ShadowMaterial({opacity: style.dark ? .48 : .19});
  const floor = new THREE.Mesh(floorGeometry, floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(960, CAPITAL_STYLE.floorY, 0);
  floor.receiveShadow = true;
  scene.add(floor);

  const geometry = createCapitalGeometry();
  const materials: THREE.Material[] = [];
  const original = designFrame(2);
  const xAt = (screenX: number) => 960 + (screenX - 960) / style.scale;
  const originalLeft = 960 + (RESULT_LAYOUT.left - 960) / original.camera.scale;
  const originalRight = 960 + (RESULT_LAYOUT.right - 960) / original.camera.scale;
  for (const item of original.tokens) {
    const isLeft = item.id.startsWith('l-');
    const color = item.tone === 'gold' ? '#d9a746' : item.tone === 'dark'
      ? (style.dark ? '#5b6675' : '#9b8261') : (style.dark ? '#d2deeb' : '#f1eadc');
    const metallic = item.tone === 'gold' ? .88 : style.dark ? .65 : .18;
    const faceMaterial = new THREE.MeshPhysicalMaterial({color, metalness: metallic,
      roughness: item.tone === 'gold' ? .28 : .38, clearcoat: .3});
    const sideMaterial = new THREE.MeshStandardMaterial({color, metalness: metallic, roughness: .42});
    materials.push(faceMaterial, sideMaterial);
    const body = new THREE.Mesh(geometry.body, [faceMaterial, sideMaterial]);
    const face = new THREE.Mesh(geometry.face, faceMaterial);
    const edge = new THREE.Mesh(geometry.edge, sideMaterial);
    const group = new THREE.Group();
    group.add(body, face, edge);
    group.position.set(item.x - (isLeft ? originalLeft : originalRight)
      + xAt(isLeft ? style.left : style.right), 1080 - item.y, item.z);
    group.rotation.set(item.pitch ?? 0, item.tilt, 0);
    const radius = Math.sqrt(item.units);
    group.scale.set(radius, radius, Math.max(.35, radius) * (item.thickness ?? 1));
    for (const mesh of [body, face, edge]) {mesh.castShadow = true; mesh.receiveShadow = true;}
    scene.add(group);
  }
  renderer.render(scene, camera);
  return () => {
    key.shadow.dispose();
    renderer.dispose(); environment.dispose();
    Object.values(geometry).forEach(value => value.dispose());
    materials.forEach(value => value.dispose());
    floorGeometry.dispose(); floorMaterial.dispose();
  };
}

export default function RedesignStage({variant, density, onReady}: {
  variant: RedesignVariant; density: number; onReady: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const dispose = build(canvas.current!, variant, density);
    onReady();
    return dispose;
  }, [variant, density, onReady]);
  return <canvas ref={canvas} style={{position: 'absolute', inset: 0, width: 1920, height: 1080}}/>;
}
