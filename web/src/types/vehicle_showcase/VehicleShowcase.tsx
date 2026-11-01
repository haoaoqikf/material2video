/**
 * SU7 汽车展示：本地 glTF、HDR 影棚环境、平面反射地面、顶部柔光板与逐帧车轮。
 *
 * 画面只依赖当前帧：镜头、车轮角度、环境强度、反射与辉光全部由 frame 求值，
 * 反射目标每帧重渲染，不跨帧累积。模型与贴图解码完成前 delayRender 阻止截图。
 */
import { useEffect, useRef, useState } from 'react';
import { AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame } from 'remotion';
import * as THREE from 'three';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { RectAreaLightUniformsLib } from 'three/examples/jsm/lights/RectAreaLightUniformsLib.js';
import { BloomEffect, BlendFunction, EffectComposer, EffectPass, HueSaturationEffect, RenderPass } from 'postprocessing';

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
  studio: {
    environment: string;
    bodyAo: string;
    floorNormal: string;
    floorRoughness: string;
  };
};

type SceneState = {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  composer: EffectComposer;
  bloom: BloomEffect;
  floor: THREE.Mesh;
  floorMaterial: THREE.ShaderMaterial;
  panelMaterial: THREE.MeshBasicMaterial;
  panel: THREE.Mesh;
  contact: THREE.Mesh;
  axleContacts: THREE.Mesh[];
  contactMaterial: THREE.MeshBasicMaterial;
  wheels: THREE.Object3D[];
  reflectionCamera: THREE.PerspectiveCamera;
  reflectionTarget: THREE.WebGLRenderTarget;
  reflectionMatrix: THREE.Matrix4;
  litMaterials: Array<{material: THREE.MeshStandardMaterial; base: number}>;
  areaLights: Array<{light: THREE.RectAreaLight; base: number}>;
};

const FLOOR_RADIUS = 90;
const REFLECTION_WIDTH = 960;
const REFLECTION_HEIGHT = 540;

function smooth(value: number): number {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

/** 车轮节点名在 three.js 里会被清洗：去掉 [ ] . : /，空白换成下划线。 */
function sanitizeNodeName(name: string): string {
  return name.replace(/\s/g, '_').replace(/[[\].:/]/g, '');
}

function findWheel(model: THREE.Object3D, name: string): THREE.Object3D | null {
  return model.getObjectByName(name) ?? model.getObjectByName(sanitizeNodeName(name)) ?? null;
}

/** 速度轨道的解析积分：关键帧之间角速度线性变化，角度连续且与取帧顺序无关。 */
function wheelAngle(seconds: number, speedStart: number, speedEnd: number,
                    duration: number): number {
  const launch = Math.max(0, speedStart - 3);
  const settle = Math.min(duration, speedEnd + 2);
  const keys = [
    {t: 0, v: 0},
    {t: launch, v: 0},
    {t: speedStart, v: 4.5},
    {t: speedEnd, v: 13.5},
    {t: settle, v: 13.5},
    {t: duration, v: 2.5},
  ];
  let angle = 0;
  for (let index = 1; index < keys.length; index += 1) {
    const start = keys[index - 1];
    const end = keys[index];
    if (seconds <= start.t) break;
    const span = end.t - start.t;
    if (span <= 0) continue;
    const stop = Math.min(seconds, end.t);
    const tau = (stop - start.t) / span;
    angle += start.v * (stop - start.t) + (end.v - start.v) * (stop - start.t) * tau * 0.5;
    if (seconds <= end.t) break;
  }
  return angle;
}

function contactShadowTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const context = canvas.getContext('2d');
  if (context) {
    context.save();
    context.translate(256, 128);
    context.scale(1, 0.5);
    const gradient = context.createRadialGradient(0, 0, 24, 0, 0, 232);
    gradient.addColorStop(0, 'rgba(0, 0, 0, 0.85)');
    gradient.addColorStop(0.5, 'rgba(0, 0, 0, 0.55)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(0, 0, 232, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

/** 顶部柔光板：中心亮、边缘渐隐的圆形柔光，避免在环绕中读成硬多边形。 */
function panelTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const context = canvas.getContext('2d');
  if (context) {
    const gradient = context.createRadialGradient(256, 256, 32, 256, 256, 254);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.55, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.78, 'rgba(255, 255, 255, 0.72)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 512, 512);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const FLOOR_VERTEX = `
varying vec3 vWorldPosition;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

const FLOOR_FRAGMENT = `
uniform sampler2D uReflection;
uniform sampler2D uNormal;
uniform sampler2D uRoughness;
uniform mat4 uTextureMatrix;
uniform vec3 uColor;
uniform float uScroll;
uniform float uReflect;
uniform float uReveal;
varying vec3 vWorldPosition;

vec3 sampleReflection(vec2 uv, vec2 distortion, float radius) {
  vec3 sum = texture2D(uReflection, uv + distortion).rgb * 0.20;
  sum += texture2D(uReflection, uv + distortion + vec2(radius, 0.0)).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion - vec2(radius, 0.0)).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion + vec2(0.0, radius)).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion - vec2(0.0, radius)).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion + vec2(radius, radius) * 0.7).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion + vec2(-radius, radius) * 0.7).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion + vec2(radius, -radius) * 0.7).rgb * 0.10;
  sum += texture2D(uReflection, uv + distortion + vec2(-radius, -radius) * 0.7).rgb * 0.10;
  return sum;
}

void main() {
  float distanceToCar = length(vWorldPosition.xz);
  float pool = exp(-distanceToCar * distanceToCar / 14.0);
  vec3 base = uColor * (0.006 + pool * 0.12) * uReveal;

  vec2 textureUv = vWorldPosition.xz * 0.16;
  textureUv.x += uScroll * 0.9;
  textureUv.y += uScroll * 0.3;
  vec3 normal = texture2D(uNormal, textureUv).rgb * 2.0 - 1.0;
  float roughness = texture2D(uRoughness, textureUv).r;

  vec4 projected = uTextureMatrix * vec4(vWorldPosition, 1.0);
  vec2 mirrorUv = projected.xy / max(projected.w, 0.0001);
  float blur = 0.085;
  vec2 distortion = normal.xy * 0.0004;

  vec3 reflection = sampleReflection(mirrorUv, distortion, blur);
  vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
  float fresnel = pow(1.0 - clamp(viewDirection.y, 0.0, 1.0), 4.0);
  float strength = mix(0.3, 1.0, fresnel) * uReflect * uReveal;
  float distanceFade = 1.0 - smoothstep(9.0, 25.0, distanceToCar);
  float reflectFade = exp(-distanceToCar * 0.07);

  vec3 color = (base + reflection * strength * reflectFade) * distanceFade;
  float dither = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
  color += (dither - 0.5) / 255.0;
  gl_FragColor = vec4(color, 1.0);
  #include <colorspace_fragment>
}
`;

export function VehicleShowcase(props: VehicleShowcaseProps) {
  const frame = useCurrentFrame();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<SceneState | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    let disposed = false;
    const handle = delayRender('加载 SU7 影棚场景', {timeoutInMilliseconds: 180_000});
    const cleanups: Array<() => void> = [];

    const build = async () => {
      const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false});
      rendererRef.current = renderer;
      cleanups.push(() => renderer.dispose());
      renderer.setSize(props.width, props.height, false);
      renderer.setPixelRatio(1);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.CineonToneMapping;
      renderer.toneMappingExposure = 1.21;
      renderer.setClearColor(0x000000, 1);

      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#000000');
      // 环境图下半球偏黑；补一层很弱的半球光，让车身下沿不糊成纯黑。
      RectAreaLightUniformsLib.init();
      scene.add(new THREE.HemisphereLight('#a9c4d2', '#2b3338', 0.1));
      // 两块大面积柔光：给车漆提供参考站那种宽幅、连续的反射带。
      const overheadArea = new THREE.RectAreaLight('#cfeef7', 0.45, 6.5, 3.2);
      overheadArea.position.set(0, 4.6, 0);
      overheadArea.lookAt(0, 0.8, 0);
      scene.add(overheadArea);
      const areaLights = [{light: overheadArea, base: 0.55}];

      const camera = new THREE.PerspectiveCamera(35, props.width / props.height, 0.1, 160);
      camera.position.set(0, props.showcase.camera.height, props.showcase.camera.distance);
      camera.lookAt(0, 0.72, 0);

      // 影棚环境：参考仓库的 HDR 柔光箱，PMREM 后作为唯一的 PBR 环境光。
      const hdr = await new RGBELoader().loadAsync(props.studio.environment);
      hdr.mapping = THREE.EquirectangularReflectionMapping;
      const pmrem = new THREE.PMREMGenerator(renderer);
      const environment = pmrem.fromEquirectangular(hdr).texture;
      scene.environment = environment;
      hdr.dispose();
      cleanups.push(() => {
        environment.dispose();
        pmrem.dispose();
      });

      const textureLoader = new THREE.TextureLoader();
      const loadTexture = async (uri: string, colorSpace: THREE.ColorSpace) => {
        const texture = await textureLoader.loadAsync(uri);
        texture.colorSpace = colorSpace;
        texture.flipY = false;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
        cleanups.push(() => texture.dispose());
        return texture;
      };
      const bodyAo = await loadTexture(props.studio.bodyAo, THREE.NoColorSpace);
      bodyAo.minFilter = THREE.LinearFilter;
      bodyAo.magFilter = THREE.LinearFilter;
      const floorNormal = await loadTexture(props.studio.floorNormal, THREE.NoColorSpace);
      const floorRoughness = await loadTexture(props.studio.floorRoughness, THREE.NoColorSpace);

      // 顶部柔光板：只作为可见发光体与辉光来源，不参与直接照明。
      const panelMap = panelTexture();
      const panelMaterial = new THREE.MeshBasicMaterial({
        map: panelMap, transparent: true, depthWrite: false, toneMapped: false,
        color: new THREE.Color(0, 0, 0), side: THREE.FrontSide,
      });
      const panel = new THREE.Mesh(new THREE.CircleGeometry(3.2, 64), panelMaterial);
      panel.rotation.x = Math.PI / 2;
      panel.position.y = 2.9;
      scene.add(panel);
      cleanups.push(() => {
        panel.geometry.dispose();
        panelMaterial.dispose();
        panelMap.dispose();
      });

      // 平面反射目标：每帧从镜像相机重渲染，供地面着色器采样。
      const reflectionTarget = new THREE.WebGLRenderTarget(REFLECTION_WIDTH, REFLECTION_HEIGHT, {
        type: THREE.HalfFloatType,
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        depthBuffer: true,
        stencilBuffer: false,
      });
      reflectionTarget.texture.generateMipmaps = false;
      cleanups.push(() => reflectionTarget.dispose());
      const reflectionCamera = new THREE.PerspectiveCamera();

      const floorMaterial = new THREE.ShaderMaterial({
        uniforms: {
          uReflection: {value: reflectionTarget.texture},
          uNormal: {value: floorNormal},
          uRoughness: {value: floorRoughness},
          uTextureMatrix: {value: new THREE.Matrix4()},
          uColor: {value: new THREE.Color('#6f7c82')},
          uScroll: {value: 0},
          uReflect: {value: 0},
          uReveal: {value: 0},
        },
        vertexShader: FLOOR_VERTEX,
        fragmentShader: FLOOR_FRAGMENT,
        depthWrite: true,
      });
      cleanups.push(() => floorMaterial.dispose());
      const floor = new THREE.Mesh(new THREE.CircleGeometry(FLOOR_RADIUS, 160), floorMaterial);
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = 0;
      scene.add(floor);
      cleanups.push(() => floor.geometry.dispose());

      // 接触阴影：车底椭圆渐变，弥补资产轮拱阴影偏弱。
      const contactTexture = contactShadowTexture();
      cleanups.push(() => contactTexture.dispose());
      const contactMaterial = new THREE.MeshBasicMaterial({
        map: contactTexture, transparent: true, depthWrite: false, toneMapped: false, opacity: 0,
      });
      const contact = new THREE.Mesh(new THREE.PlaneGeometry(5.4, 2.6), contactMaterial);
      contact.rotation.x = -Math.PI / 2;
      contact.position.y = 0.006;
      scene.add(contact);
      const axleContacts = [-1.5, 1.5].map((x) => {
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 1.6), contactMaterial);
        mesh.rotation.x = -Math.PI / 2;
        mesh.position.set(x, 0.007, 0);
        scene.add(mesh);
        return mesh;
      });
      cleanups.push(() => {
        contact.geometry.dispose();
        axleContacts.forEach((mesh) => mesh.geometry.dispose());
        contactMaterial.dispose();
      });

      const composer = new EffectComposer(renderer, {multisampling: 4});
      composer.addPass(new RenderPass(scene, camera));
      const bloom = new BloomEffect({
        blendFunction: BlendFunction.ADD,
        mipmapBlur: true,
        luminanceThreshold: 0.82,
        luminanceSmoothing: 0.55,
        intensity: 0,
        radius: 0.72,
      });
      const grade = new HueSaturationEffect({saturation: 0.1, hue: 0});
      composer.addPass(new EffectPass(camera, bloom, grade));
      cleanups.push(() => composer.dispose());

      // 模型：缩放、落地、材质与车轮解析。
      const loader = new GLTFLoader();
      loader.setMeshoptDecoder(MeshoptDecoder);
      const gltf = await new Promise<GLTF>(
        (resolve, reject) => {
          loader.parse(props.modelGltf, '', resolve, (error) => reject(error));
        });
      if (disposed) return;
      const model = gltf.scene;
      const bounds = new THREE.Box3().setFromObject(model);
      const size = bounds.getSize(new THREE.Vector3());
      const center = bounds.getCenter(new THREE.Vector3());
      const scale = 5.4 / Math.max(size.x, size.z);
      model.scale.setScalar(scale);
      model.position.set(-center.x * scale, -bounds.min.y * scale, -center.z * scale);
      scene.add(model);
      model.updateWorldMatrix(true, true);

      const litMaterials: Array<{material: THREE.MeshStandardMaterial; base: number}> = [];
      model.traverse((item) => {
        if (!(item instanceof THREE.Mesh)) return;
        const materials = Array.isArray(item.material) ? item.material : [item.material];
        const next = materials.map((material) => {
          if (!(material instanceof THREE.MeshStandardMaterial)) return material;
          if (material.name === 'Car_body') {
            // 车漆：深青底色 + 清漆层，让柔光板以湿润的宽幅高光出现在车身。
            const paint = new THREE.MeshPhysicalMaterial({
              name: material.name,
              color: new THREE.Color('#007a7a'),
              roughness: 0.28,
              metalness: 0.0,
              clearcoat: 0.6,
              clearcoatRoughness: 0.12,
              envMap: environment,
              envMapIntensity: 1.4,
              aoMap: bodyAo,
              aoMapIntensity: 1.0,
            });
            if (paint.aoMap) paint.aoMap.channel = 1;
            litMaterials.push({material: paint, base: 2.6});
            return paint;
          }
          material.aoMap = bodyAo;
          material.aoMap.channel = 1;
          material.aoMapIntensity = 1.0;
          material.envMap = environment;
          material.envMapIntensity = 1.4;
          if (material.name === 'Car_window') {
            material.color.set('#05080a');
            material.opacity = 0.45;
            material.roughness = 0.02;
            material.envMapIntensity = 3.0;
            litMaterials.push({material, base: 3.0});
          } else {
            litMaterials.push({material, base: 1.4});
          }
          if (material.name === 'Car_ight') material.emissiveIntensity = 2.0;
          material.needsUpdate = true;
          return material;
        });
        item.material = Array.isArray(item.material) ? next : next[0];
      });

      const wheels = props.showcase.wheelNodes.map((name) => findWheel(model, name));
      if (wheels.some((wheel) => wheel === null)) {
        throw new Error(`车轮节点解析失败：${props.showcase.wheelNodes.join('、')}`);
      }

      const reflectionMatrix = new THREE.Matrix4();
      const state: SceneState = {
        renderer, scene, camera, composer, bloom, floor, floorMaterial,
        panelMaterial, panel, contact, axleContacts, contactMaterial,
        wheels: wheels as THREE.Object3D[],
        reflectionCamera, reflectionTarget, reflectionMatrix, litMaterials, areaLights,
      };
      if (disposed) return;
      stateRef.current = state;
      setReady(true);
    };

    build().then(() => {
      if (!disposed) continueRender(handle);
    }).catch((error: unknown) => {
      if (!disposed) cancelRender(error instanceof Error ? error : new Error(String(error)));
    });

    return () => {
      disposed = true;
      cleanups.forEach((cleanup) => cleanup());
      stateRef.current = null;
      rendererRef.current = null;
    };
  }, [props.modelGltf, props.studio.environment, props.studio.bodyAo,
    props.studio.floorNormal, props.studio.floorRoughness, props.width, props.height,
    props.showcase.wheelNodes]);

  useEffect(() => {
    const state = stateRef.current;
    if (!ready || !state) return;
    const handle = delayRender('渲染 SU7 当前帧');
    drawFrame(state, frame, props);
    continueRender(handle);
  }, [frame, ready, props]);

  return <AbsoluteFill style={{background: '#000000'}}>
    <canvas ref={canvasRef} width={props.width} height={props.height}
      data-m2v-vehicle-canvas="su7" style={{width: '100%', height: '100%'}} />
  </AbsoluteFill>;
}

function drawFrame(state: SceneState, frame: number, props: VehicleShowcaseProps): void {
  const {camera, scene, renderer, composer, bloom, floorMaterial, panelMaterial,
    contactMaterial, wheels} = state;
  const spec = props.showcase;
  const effects = spec.effects;
  const seconds = frame / props.fps;
  const duration = spec.durationSeconds;

  const orbit = smooth((seconds - 4) / 12);
  const angle = THREE.MathUtils.degToRad(
    spec.camera.orbitStartDegrees
      + (spec.camera.orbitEndDegrees - spec.camera.orbitStartDegrees) * orbit)
    + THREE.MathUtils.degToRad(3) * smooth((seconds - effects.speedStartSeconds)
      / Math.max(0.01, effects.speedEndSeconds - effects.speedStartSeconds));
  const speed = smooth((seconds - effects.speedStartSeconds)
    / Math.max(0.01, effects.speedEndSeconds - effects.speedStartSeconds));
  const push = 1 - smooth(seconds / 4);
  const reveal = smooth((seconds - 0.8) / 2.8);
  const settle = smooth((seconds - (duration - effects.fadeOutSeconds)) / effects.fadeOutSeconds);
  const rush = speed * (1 - settle * 0.6);

  // 侧视角看到车长、前后视角只看到车宽；按视角收放距离，保持主体占比稳定。
  const sideFactor = Math.abs(Math.sin(angle));
  const distance = spec.camera.distance * (0.8 + 0.2 * sideFactor) + push * 1.9 - rush * 0.1;
  const height = spec.camera.height + push * 0.45 + rush * 0.04;
  const shake = rush * 0.032;
  camera.position.set(
    Math.sin(angle) * distance + Math.sin(seconds * 31) * shake,
    height + Math.sin(seconds * 17) * shake,
    Math.cos(angle) * distance + Math.cos(seconds * 23) * shake,
  );
  camera.lookAt(0, 0.76, 0);
  camera.fov = 34 + push * 5 - rush * 0.5;
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();

  const rotation = wheelAngle(seconds, effects.speedStartSeconds, effects.speedEndSeconds, duration);
  wheels.forEach((wheel) => {
    wheel.rotation.z = -rotation;
  });

  scene.environmentIntensity = 0.012 + reveal * (1.0 + speed * 1.1);
  const revealScale = reveal * (1 + speed * 0.3);
  state.litMaterials.forEach(({material, base}) => {
    material.envMapIntensity = base * revealScale;
  });
  state.areaLights.forEach(({light, base}) => {
    light.intensity = base * reveal * (1 + speed * 0.25);
  });
  panelMaterial.color.setScalar(reveal * (1 - speed * 0.12) * 0.85);
  contactMaterial.opacity = reveal * 0.85;
  const uniforms = floorMaterial.uniforms;
  uniforms.uReveal.value = reveal;
  uniforms.uReflect.value = 0.3 + speed * 0.15;
  uniforms.uScroll.value = 0;
  bloom.intensity = 0.1 + reveal * 1.05 + speed * 0.95;

  const fade = seconds > duration - effects.fadeOutSeconds
    ? 1 - smooth((seconds - (duration - effects.fadeOutSeconds)) / effects.fadeOutSeconds)
    : 1;

  updateReflection(state);
  composer.render(0);

  renderer.domElement.style.opacity = String(fade);
}

/** 把主相机按 y=0 镜像，斜裁剪后渲染到反射目标；地面与接触阴影不参与反射。 */
function updateReflection(state: SceneState): void {
  const {renderer, scene, camera, floor, panel, contact, axleContacts, reflectionCamera,
    reflectionTarget, reflectionMatrix} = state;
  const normal = new THREE.Vector3(0, 1, 0);
  const reflectorWorldPosition = new THREE.Vector3(0, floor.position.y, 0);
  const cameraWorldPosition = new THREE.Vector3();
  camera.getWorldPosition(cameraWorldPosition);

  const view = reflectorWorldPosition.clone().sub(cameraWorldPosition);
  if (view.dot(normal) > 0) return;
  view.reflect(normal).negate().add(reflectorWorldPosition);

  const rotationMatrix = new THREE.Matrix4().extractRotation(camera.matrixWorld);
  const lookAtPosition = new THREE.Vector3(0, 0, -1)
    .applyMatrix4(rotationMatrix).add(cameraWorldPosition);
  const target = reflectorWorldPosition.clone().sub(lookAtPosition);
  target.reflect(normal).negate().add(reflectorWorldPosition);

  reflectionCamera.position.copy(view);
  reflectionCamera.up.set(0, 1, 0).applyMatrix4(rotationMatrix).reflect(normal);
  reflectionCamera.lookAt(target);
  reflectionCamera.far = camera.far;
  reflectionCamera.updateMatrixWorld();
  reflectionCamera.projectionMatrix.copy(camera.projectionMatrix);

  reflectionMatrix.set(
    0.5, 0, 0, 0.5,
    0, 0.5, 0, 0.5,
    0, 0, 0.5, 0.5,
    0, 0, 0, 1,
  );
  reflectionMatrix.multiply(reflectionCamera.projectionMatrix);
  reflectionMatrix.multiply(reflectionCamera.matrixWorldInverse);

  const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(normal, reflectorWorldPosition);
  plane.applyMatrix4(reflectionCamera.matrixWorldInverse);
  const clipPlane = new THREE.Vector4(plane.normal.x, plane.normal.y, plane.normal.z, plane.constant);
  const projection = reflectionCamera.projectionMatrix;
  const q = new THREE.Vector4();
  q.x = (Math.sign(clipPlane.x) + projection.elements[8]) / projection.elements[0];
  q.y = (Math.sign(clipPlane.y) + projection.elements[9]) / projection.elements[5];
  q.z = -1.0;
  q.w = (1.0 + projection.elements[10]) / projection.elements[14];
  clipPlane.multiplyScalar(2.0 / clipPlane.dot(q));
  projection.elements[2] = clipPlane.x;
  projection.elements[6] = clipPlane.y;
  projection.elements[10] = clipPlane.z + 1.0;
  projection.elements[14] = clipPlane.w;

  const floorVisible = floor.visible;
  const contactVisible = contact.visible;
  const axleVisible = axleContacts.map((mesh) => mesh.visible);
  const panelVisible = panel.visible;
  floor.visible = false;
  contact.visible = false;
  axleContacts.forEach((mesh) => { mesh.visible = false; });
  panel.visible = false;
  const currentTarget = renderer.getRenderTarget();
  renderer.setRenderTarget(reflectionTarget);
  renderer.clear();
  renderer.render(scene, reflectionCamera);
  renderer.setRenderTarget(currentTarget);
  floor.visible = floorVisible;
  contact.visible = contactVisible;
  axleContacts.forEach((mesh, index) => { mesh.visible = axleVisible[index]; });
  panel.visible = panelVisible;
}
