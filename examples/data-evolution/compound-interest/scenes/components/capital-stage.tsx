/** Three负责几何、材质与真实受光；每次布局提交只渲染显式状态，不建立自主动画循环。 */
import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three';
import type {CapitalFrame, Token} from '../capital-state';
import {createCapitalGeometry} from './capital-geometry';
import {createStudioEnvironment} from './capital-lighting';
import {CAPITAL_STYLE} from '../capital-style';

const COLORS = {white: '#eee7d7', gold: '#dbad4e', dark: '#79633d'};
type Coin = {group: THREE.Group; face: THREE.MeshPhysicalMaterial; side: THREE.MeshStandardMaterial};

function createStage(canvas: HTMLCanvasElement, width: number, height: number, density: number, bright: boolean) {
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false, preserveDrawingBuffer: true});
  renderer.setPixelRatio(density);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .85;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0c0e13');
  const camera = new THREE.OrthographicCamera(-960, 960, 540, -540, .1, 4000);
  const environment = createStudioEnvironment(renderer, bright);
  scene.environment = environment.texture;
  scene.environmentIntensity = .75;

  const key = new THREE.DirectionalLight('#fff0d3', bright ? 1 : 1.3);
  key.position.set(500, 2800, 500);
  key.target.position.set(960, 540, 0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {left: -700, right: 700, top: 700, bottom: -700, near: .1, far: 4000});
  key.shadow.normalBias = .04;
  key.shadow.bias = -.0001;
  key.shadow.radius = 3;
  scene.add(key, key.target);
  const fill = new THREE.DirectionalLight('#b6c6e2', bright ? .7 : .3);
  fill.position.set(1900, 500, 700);
  scene.add(fill);
  scene.add(new THREE.HemisphereLight('#d1ddf1', '#292019', bright ? .3 : .15));

  // 承载面距圆片背面只有数个单位，接触影保留物体归属，而非漂在黑场。
  const wallGeometry = new THREE.PlaneGeometry(8000, 5000);
  const background = new Uint8Array(256 * 256 * 4);
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const wx = (x / 255 - .5) * 8000 + 960;
    const wy = (.5 - y / 255) * 5000 + 540;
    const light = Math.exp(-((wx - 1200) ** 2 / 1200000 + (wy - 580) ** 2 / 900000));
    const index = (y * 256 + x) * 4;
    background.set([3 + light * 9, 4 + light * 10, 6 + light * 13, 255], index);
  }
  const backgroundMap = new THREE.DataTexture(background, 256, 256, THREE.RGBAFormat);
  backgroundMap.colorSpace = THREE.SRGBColorSpace;
  backgroundMap.needsUpdate = true;
  const wallMaterial = new THREE.MeshStandardMaterial({map: backgroundMap, roughness: .98, metalness: 0});
  const wall = new THREE.Mesh(wallGeometry, wallMaterial);
  wall.position.set(960, 540, -13);
  wall.receiveShadow = true;
  scene.add(wall);
  const floorGeometry = new THREE.PlaneGeometry(8000, 6000);
  const floorMaterial = new THREE.MeshStandardMaterial({color: '#0c1017', roughness: .8,
    metalness: .08, envMapIntensity: bright ? .85 : .15});
  const floor = new THREE.Mesh(floorGeometry, floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(960, CAPITAL_STYLE.floorY, 0);
  floor.receiveShadow = true;
  scene.add(floor);
  const pool = new THREE.SpotLight('#d7e1ef', 200000, 0, .7, 1, 2);
  pool.position.set(960, 2400, 200);
  pool.target.position.set(1000, CAPITAL_STYLE.floorY, 0);
  scene.add(pool, pool.target);

  const geometry = createCapitalGeometry();
  const coins = new Map<string, Coin>();
  const gold = new THREE.Color(COLORS.gold);
  const white = new THREE.Color(COLORS.white);
  const dark = new THREE.Color(COLORS.dark);

  function coinFor(id: string) {
    const found = coins.get(id);
    if (found) return found;
    const face = new THREE.MeshPhysicalMaterial({color: COLORS.white, roughness: .4,
      metalness: .12, clearcoat: .2, clearcoatRoughness: .28});
    const side = new THREE.MeshStandardMaterial({color: COLORS.white, roughness: .34, metalness: .55});
    const body = new THREE.Mesh(geometry.body, [face, side]);
    body.castShadow = true;
    body.receiveShadow = true;
    const reeding = new THREE.Mesh(geometry.edge, side);
    reeding.castShadow = true;
    const front = new THREE.Mesh(geometry.face, face);
    front.castShadow = true;
    front.receiveShadow = true;
    const group = new THREE.Group();
    group.add(body, front, reeding);
    scene.add(group);
    const value = {group, face, side};
    coins.set(id, value);
    return value;
  }

  function updateCoin(item: Token) {
    const coin = coinFor(item.id);
    coin.group.visible = item.opacity > .001 && item.units > .00001;
    coin.group.position.set(item.x, 1080 - item.y, item.z);
    coin.group.rotation.set(item.pitch ?? .16, item.tilt, 0);
    const radius = Math.sqrt(Math.max(0, item.units));
    coin.group.scale.set(radius, radius, Math.max(.35, radius) * (item.thickness ?? 1));
    coin.face.color.copy(item.tone === 'dark' ? dark : white).lerp(gold, item.gold);
    coin.face.metalness = item.tone === 'dark' ? .55 : .12 + .75 * item.gold;
    coin.face.roughness = item.tone === 'dark' ? .44 : .4 - .15 * item.gold;
    coin.face.clearcoat = .2 + .15 * item.gold;
    coin.side.color.copy(coin.face.color).multiplyScalar(bright ? .82 : .55);
    coin.side.metalness = bright && item.tone === 'white' ? .18 : Math.max(.55, coin.face.metalness);
    coin.side.roughness = bright ? .5 : .34;
    // 透明仅用于入退场；同一材质在opaque段关闭，避免遮挡排序改变实体接触。
    for (const material of [coin.face, coin.side]) {
      const transparent = item.opacity < .999;
      if (material.transparent !== transparent) {material.transparent = transparent; material.needsUpdate = true;}
      material.opacity = item.opacity;
    }
  }

  return {
    draw(state: CapitalFrame) {
      (scene.background as THREE.Color).set(state.palette?.background ?? '#0c0e13');
      floorMaterial.color.set(state.palette?.floor ?? '#0c1017');
      const map = state.palette ? null : backgroundMap;
      if (wallMaterial.map !== map) {wallMaterial.map = map; wallMaterial.needsUpdate = true;}
      wallMaterial.color.set(state.palette?.background ?? '#ffffff');
      for (const coin of coins.values()) coin.group.visible = false;
      state.tokens.forEach(updateCoin);
      const elevation = state.camera.elevation ?? 0;
      floor.visible = pool.visible = elevation > 0;
      wall.position.z = elevation > 0 ? -1000 : -13;
      camera.position.set(state.camera.x, 1080 - state.camera.y + 1800 * Math.sin(elevation),
        1800 * Math.cos(elevation));
      camera.lookAt(state.camera.x, 1080 - state.camera.y, 0);
      camera.zoom = state.camera.scale;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    },
    dispose() {
      coins.forEach(coin => {coin.face.dispose(); coin.side.dispose();});
      Object.values(geometry).forEach(value => value.dispose());
      backgroundMap.dispose(); wallGeometry.dispose(); wallMaterial.dispose();
      floorGeometry.dispose(); floorMaterial.dispose();
      environment.dispose(); renderer.dispose();
    },
  };
}

export default function CapitalStage({state, width, height, density = 1, onReady}: {
  state: CapitalFrame; width: number; height: number; density?: number; onReady: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const stage = useRef<ReturnType<typeof createStage> | null>(null);
  const bright = Boolean(state.palette);
  useLayoutEffect(() => {
    stage.current = createStage(canvas.current!, width, height, density, bright);
    return () => {stage.current?.dispose(); stage.current = null;};
  }, [width, height, density, bright]);
  useLayoutEffect(() => {stage.current!.draw(state); onReady();}, [state, onReady]);
  return <canvas ref={canvas} style={{position: 'absolute', width, height, inset: 0}} aria-hidden="true"/>;
}
