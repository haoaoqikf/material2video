import {useEffect, useMemo, useRef, useState} from 'react';
import {THREE, useFrame, useMediaAsset, useThree} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {smooth} from './clock';

export type EarthUniforms = {
  uSunView: {value: THREE.Vector3};
  uClouds: {value: THREE.Texture | null};
  uNightMap: {value: THREE.Texture | null};
  uCloudOffset: {value: number};
  uNight: {value: number};
  uCloudShadow: {value: number};
};

/**
 * 地球 hero 的表面细节：已登记的夜景地图、海面粗糙度遮罩与逐帧云影。
 *
 * 昼夜遮罩由材质贴图与**视空间太阳方向**算出：太阳方向每帧从相机矩阵更新，
 * 因此昼夜分界永远与场景里的点光源一致；没有引入新的时间或随机源。
 */
export function earthSurface(shader: Parameters<THREE.MeshStandardMaterial['onBeforeCompile']>[0],
                             uniforms: EarthUniforms) {
  Object.assign(shader.uniforms, uniforms);
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <common>', `#include <common>
      uniform vec3 uSunView;
      uniform sampler2D uClouds;
      uniform sampler2D uNightMap;
      uniform float uCloudOffset;
      uniform float uNight;
      uniform float uCloudShadow;
      `)
    .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
      {
        // GLSL 未定义 edge0 >= edge1 的 smoothstep；反转结果保证跨 GPU 一致。
        float m2vNight = 1.0 - smoothstep(-0.24, 0.06, dot(normalize(vNormal), normalize(uSunView)));
        vec3 lights = texture2D(uNightMap, vMapUv).rgb;
        totalEmissiveRadiance += lights * m2vNight * uNight;
        // 云图是灰度 JPEG，没有 alpha；与云层 alphaMap 一样读取绿色通道。
        float cloud = texture2D(uClouds, vMapUv + vec2(uCloudOffset, 0.0)).g;
        diffuseColor.rgb *= 1.0 - cloud * uCloudShadow;
      }`);
}

/** 逐项通过素材 ID 解析；固定钩子顺序，来源清单中的全部素材均实际用于本作品。 */
export function useTextureSources() {
  return {
    sun: useMediaAsset('sun').src, mercury: useMediaAsset('mercury').src,
    venus: useMediaAsset('venus').src, earth: useMediaAsset('earth').src,
    moon: useMediaAsset('moon').src, mars: useMediaAsset('mars').src,
    jupiter: useMediaAsset('jupiter').src, europa: useMediaAsset('europa').src,
    saturn: useMediaAsset('saturn').src, uranus: useMediaAsset('uranus').src,
    neptune: useMediaAsset('neptune').src, pluto: useMediaAsset('pluto').src,
    clouds: useMediaAsset('clouds').src, rings: useMediaAsset('rings').src,
    titan: useMediaAsset('titan').src,
    'earth-normal': useMediaAsset('earth-normal').src,
    'earth-roughness': useMediaAsset('earth-roughness').src,
    'earth-emissive': useMediaAsset('earth-emissive').src,
    'sun-normal': useMediaAsset('sun-normal').src,
    'sun-roughness': useMediaAsset('sun-roughness').src,
    'sun-emissive': useMediaAsset('sun-emissive').src,
    'saturn-normal': useMediaAsset('saturn-normal').src,
    'saturn-roughness': useMediaAsset('saturn-roughness').src,
    'saturn-emissive': useMediaAsset('saturn-emissive').src,
    'jupiter-normal': useMediaAsset('jupiter-normal').src,
    'jupiter-roughness': useMediaAsset('jupiter-roughness').src,
    'jupiter-emissive': useMediaAsset('jupiter-emissive').src,
    'pluto-normal': useMediaAsset('pluto-normal').src,
    'pluto-roughness': useMediaAsset('pluto-roughness').src,
    'pluto-emissive': useMediaAsset('pluto-emissive').src,
    'titan-normal': useMediaAsset('titan-normal').src,
    'titan-roughness': useMediaAsset('titan-roughness').src,
    'titan-emissive': useMediaAsset('titan-emissive').src,
  };
}
export type Textures = Record<string, THREE.Texture>;
export type TimeSource = {readonly current: {seconds: number}};

/** 纹理在正式开录前预加载并上传 GPU，避免首帧缺纹理；卸载释放显存。 */
export function useTextures(sources: Record<string, string>) {
  const key = JSON.stringify(sources);
  const [textures, setTextures] = useState<Textures | null>(null);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => {
    let cancelled = false;
    const loaded: THREE.Texture[] = [];
    const loader = new THREE.TextureLoader();
    Promise.all(Object.entries(JSON.parse(key) as Record<string, string>).map(async ([id, url]) => {
      const texture = await loader.loadAsync(url);
      texture.colorSpace = id === 'clouds' || id.endsWith('-normal') || id.endsWith('-roughness')
        ? THREE.NoColorSpace : THREE.SRGBColorSpace;
      texture.anisotropy = 4;
      loaded.push(texture);
      if (cancelled) texture.dispose();
      return [id, texture] as const;
    })).then(entries => {if (!cancelled) setTextures(Object.fromEntries(entries));})
      .catch(reason => {if (!cancelled) setError(new Error(`天体纹理加载失败：${String(reason)}`));});
    return () => {cancelled = true; loaded.forEach(texture => texture.dispose());};
  }, [key]);
  if (error) throw error;
  return textures;
}

const ATMOSPHERE_VERTEX = `
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vec4 p = modelViewMatrix * vec4(position, 1.0);
  vNormal = normalize(normalMatrix * normal);
  vView = -p.xyz;
  gl_Position = projectionMatrix * p;
}`;
const ATMOSPHERE_FRAGMENT = `
uniform vec3 tint;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  float rim = pow(1.0 - max(dot(normalize(vNormal), normalize(vView)), 0.0), 4.6);
  gl_FragColor = vec4(tint, rim * 0.32);
}`;

function Atmosphere({color, radius, detail}: {color: string; radius: number; detail: boolean}) {
  const uniforms = useMemo(() => ({tint: {value: new THREE.Color(color)}}), [color]);
  return <mesh scale={1.025}>
    <sphereGeometry args={[radius, detail ? 64 : 24, detail ? 40 : 16]}/>
    <shaderMaterial vertexShader={ATMOSPHERE_VERTEX} fragmentShader={ATMOSPHERE_FRAGMENT}
      uniforms={uniforms} transparent depthWrite={false} blending={THREE.AdditiveBlending}/>
  </mesh>;
}

/** 解析式日光遮挡：避免点光源六面阴影贴图在完整模型中重复渲染全部天体。 */
function saturnShadow(shader: Parameters<THREE.MeshStandardMaterial['onBeforeCompile']>[0],
  radius: number, ringTexture?: THREE.Texture) {
  shader.vertexShader = shader.vertexShader.replace('#include <common>', `#include <common>
    varying vec3 solarPosition; varying vec3 solarCenter; varying vec3 solarRingNormal;`)
    .replace('#include <begin_vertex>', `#include <begin_vertex>
      solarPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      solarCenter = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
      solarRingNormal = normalize(mat3(modelMatrix) * vec3(0.0, 1.0, 0.0));`);
  shader.fragmentShader = shader.fragmentShader.replace('#include <common>', `#include <common>
    varying vec3 solarPosition; varying vec3 solarCenter; varying vec3 solarRingNormal;
    uniform float solarRadius; ${ringTexture ? 'uniform sampler2D solarRingMap;' : ''}`);
  shader.uniforms.solarRadius = {value: radius};
  if (ringTexture) shader.uniforms.solarRingMap = {value: ringTexture};
  const calculation = ringTexture ? `
    vec3 rayToSun = normalize(-solarPosition);
    float denom = dot(rayToSun, solarRingNormal);
    if (abs(denom) > 0.001) {
      float t = dot(solarCenter - solarPosition, solarRingNormal) / denom;
      float r = length(solarPosition + t * rayToSun - solarCenter) / solarRadius;
      if (t > 0.0 && r > 1.24 && r < 2.27) {
        float alpha = texture2D(solarRingMap, vec2((r - 1.24) / 1.03, 0.5)).a;
        outgoingLight *= 1.0 - alpha * 0.84;
      }
    }` : `
    vec3 rayToSun = normalize(-solarPosition);
    // 冰粒前向散射的艺术近似：太阳在环背后时增强透光，仍受母星遮挡。
    vec3 rayToViewer = normalize(cameraPosition - solarPosition);
    float forwardScatter = pow(max(0.0, -dot(rayToSun, rayToViewer)), 8.0);
    outgoingLight += diffuseColor.rgb * forwardScatter * 0.55;
    vec3 toCenter = solarCenter - solarPosition;
    float along = dot(toCenter, rayToSun);
    float distance2 = dot(toCenter, toCenter) - along * along;
    // 半影：圆柱判据的硬边会在大环上切出多边形黑楔。用平滑过渡保留影带，去掉直边。
    float shadow = 1.0 - smoothstep(solarRadius * solarRadius * 0.88,
      solarRadius * solarRadius * 1.55, distance2);
    if (along > 0.0) outgoingLight *= 1.0 - 0.84 * shadow;`;
  shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>', calculation + '\n#include <opaque_fragment>');
}

/** 土星环采用径向 UV，不把矩形纹理直接重复贴到圆周；保留原始透明通道。 */
function Rings({radius, texture}: {radius: number; texture: THREE.Texture}) {
  const geometry = useMemo(() => {
    const inner = radius * 1.24, outer = radius * 2.27;
    const ring = new THREE.RingGeometry(inner, outer, 192, 1);
    const positions = ring.attributes.position;
    const uv = ring.attributes.uv;
    for (let i = 0; i < positions.count; i++) {
      const distance = Math.hypot(positions.getX(i), positions.getY(i));
      uv.setXY(i, (distance - inner) / (outer - inner), 0.5);
    }
    return ring;
  }, [radius]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} castShadow receiveShadow>
    <meshStandardMaterial map={texture} transparent opacity={0.96} alphaTest={0.045}
      customProgramCacheKey={() => 'solar-ring-shadow-v1'}
      onBeforeCompile={shader => saturnShadow(shader, radius)}
      side={THREE.DoubleSide} roughness={0.96} metalness={0} depthWrite={false}/>
  </mesh>;
}

function proceduralSurface(id: string): THREE.DataTexture | undefined {
  if (id !== 'ceres') return undefined;
  const width = 512, height = 256;
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const lon = x / width * Math.PI * 2;
      const lat = (y / height - 0.5) * Math.PI;
      const px = Math.cos(lat) * Math.cos(lon), py = Math.sin(lat), pz = Math.cos(lat) * Math.sin(lon);
      let value = 0.52 + Math.sin(px * 43 + Math.sin(pz * 31)) * Math.cos(py * 47) * 0.08;
      value += Math.sin(px * 133 + pz * 117) * Math.sin(py * 109) * 0.035;
      // 球面距离保证经线接缝连续；凹坑只用于解释岩质外观，不对应真实地名。
      for (let i = 0; i < 28; i++) {
        const cy = 1 - 2 * (i + 0.5) / 28;
        const angle = i * 2.399963;
        const s = Math.sqrt(1 - cy * cy);
        const d = Math.hypot(px - Math.cos(angle) * s, py - cy, pz - Math.sin(angle) * s);
        const r = 0.045 + (i % 4) * 0.02;
        value -= Math.exp(-(d * d) / (r * r)) * 0.18;
        value += Math.exp(-Math.pow((d - r * 1.3) / (r * 0.18), 2)) * 0.10;
      }
      const index = (y * width + x) * 4;
      const rgb = [173, 168, 156];
      const shade = 0.55 + value;
      data.set([...rgb.map(c => Math.min(255, Math.round(c * shade))), 255], index);
    }
  }
  const texture = new THREE.DataTexture(data, width, height);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  return texture;
}

/**
 * 需要「正对镜头」的纹理地标在物体空间里的方向（未归一化）。
 *
 * - 木星大红斑：Solar System Scope 4K 图约在 u=0.366、v=0.605。
 * - 冥王星心形（Tombaugh Regio）：约在 u=0.459、v=0.488。
 *
 * 球面 UV 与 three.js SphereGeometry 的映射一致；这里只用于算朝向，不复制贴图。
 */
const FEATURE_NORMAL: Record<string, [number, number, number]> = {
  // 图像行 0.605 从顶部算起 → 球面极角 0.605π → 南半球 y = cos(0.605π)。
  jupiter: [0.666, -0.323, 0.746],
  pluto: [0.966, 0.037, 0.259],
};

export function Planet({id, textures, clock, radius = 2.35, phase = 0, detail = true, faceFeature = false}: {
  id: string; textures: Textures; clock: TimeSource; radius?: number; phase?: number; detail?: boolean;
  /** 展示性朝向：让该天体的纹理地标（大红斑/心形）在镜头里正对机位。 */
  faceFeature?: boolean;
}) {
  const body = BODIES[id];
  const generated = useMemo(() => proceduralSurface(id), [id]);
  useEffect(() => () => generated?.dispose(), [generated]);
  const map = body.texture ? textures[body.texture] : generated;
  const sphere = useRef<THREE.Mesh>(null);
  const clouds = useRef<THREE.Mesh>(null);
  const camera = useThree(state => state.camera);
  const earthUniforms = useMemo<EarthUniforms>(() => ({
    uSunView: {value: new THREE.Vector3(1, 0, 0)},
    uClouds: {value: textures.clouds ?? null},
      uNightMap: {value: textures['earth-emissive'] ?? null},
      uCloudOffset: {value: 0},
    uNight: {value: 1.8},
    uCloudShadow: {value: 0.38},
  }), [textures.clouds, textures['earth-emissive']]);
  useFrame(() => {
    const rotation = clock.current.seconds * (id === 'venus' ? -0.018 : 0.026);
    if (sphere.current) {
      const feature = FEATURE_NORMAL[id];
      if (feature && faceFeature) {
        // 绘制期间始终把地标转向当前机位：镜头是唯一时钟，同帧可复现。
        // θ = atan2(x,z)；three.js 绕 y 旋转满足 θ' = θ + a，因此 a = θ机位 − θ地标。
        const world = sphere.current.getWorldPosition(new THREE.Vector3());
        const cameraWorld = camera.getWorldPosition(new THREE.Vector3());
        const toCamera = Math.atan2(cameraWorld.x - world.x, cameraWorld.z - world.z);
        const featureAngle = Math.atan2(feature[0], feature[2]);
        sphere.current.rotation.y = toCamera - featureAngle + rotation * 0.05;
      } else {
        sphere.current.rotation.y = 2.8 + rotation;
      }
    }
    if (clouds.current) clouds.current.rotation.y = 2.8 + rotation * 1.12;
    earthUniforms.uCloudOffset.value = -rotation * 0.12 / (Math.PI * 2);
    if (id === 'earth' && sphere.current) {
      // 太阳在世界原点：把「从星球指向太阳」的方向转到视空间，与 vNormal 同一空间。
      const world = sphere.current.getWorldPosition(new THREE.Vector3());
      earthUniforms.uSunView.value.copy(world.negate().normalize())
        .transformDirection(camera.matrixWorldInverse);
    }
  });
  return <group rotation={[id === 'saturn' ? 0.18 + smooth(phase) * 0.55 : 0.1, 0, -(body.tilt ?? 8) * Math.PI / 180]}>
    <mesh ref={sphere} rotation={[0, 2.8, 0]}>
      <sphereGeometry args={[radius, detail ? 96 : 24, detail ? 64 : 16]}/>
        <meshStandardMaterial map={map}
          // 每个天体的 onBeforeCompile 不同，缓存键必须带 id；共用键会让先编译的
          // 程序覆盖后来天体的着色器改动。
          customProgramCacheKey={() => id === 'saturn' ? 'solar-sphere-ring-shadow-v1'
            : id === 'earth' ? 'solar-earth-cinematic-v2' : id === 'sun' ? 'solar-limb-v1'
              : `solar-planet-v2-${id}`}
          onBeforeCompile={shader => {
            if (id === 'saturn') saturnShadow(shader, radius, textures.rings);
            if (id === 'earth') earthSurface(shader, earthUniforms);
            if (id === 'jupiter') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              // 只增强源纹理里已有的大红斑局部对比，不另画贴图地标。
              float m2vSpot = smoothstep(0.045, 0.015, distance(vMapUv, vec2(0.354, 0.390)));
              outgoingLight = mix(outgoingLight, outgoingLight * vec3(0.78, 0.42, 0.30),
                m2vSpot * 0.85);
              #include <opaque_fragment>`);
            if (id === 'pluto') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              // 心形氮冰平原在深空曝光下偏暗，按源图 UV 做局部提亮。
              float m2vHeart = smoothstep(0.06, 0.02, distance(vMapUv, vec2(0.459, 0.512)));
              outgoingLight = mix(outgoingLight,
                min(vec3(1.0), outgoingLight * 1.22 + 0.015), m2vHeart * 0.6);
              #include <opaque_fragment>`);
            if (id === 'sun') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              float limb = pow(clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), 0.55);
              outgoingLight *= 0.55 + 0.45 * limb;
              #include <opaque_fragment>`);
          }}
          color={map ? '#ffffff' : body.color} roughness={textures[`${id}-roughness`] ? 1.3 : 0.96}
          roughnessMap={textures[`${id}-roughness`]}
          normalMap={textures[`${id}-normal`]} normalScale={new THREE.Vector2(0.35, 0.35)}
          emissiveMap={id === 'titan' ? map : id === 'earth' ? undefined : textures[`${id}-emissive`]}
          // 没有 emissiveMap 的天体必须保持黑色自发光；否则白 emissive 会把月球、
          // 水星、金星、火星整颗渲染成没有纹理的白盘。
          emissive={id === 'earth' ? '#000000' : id === 'titan' ? '#ffb066'
            : id === 'sun' || textures[`${id}-emissive`] ? '#ffffff' : '#000000'}
          emissiveIntensity={id === 'sun' ? 1.2 : id === 'titan' ? 0.45 : 1} metalness={0}
          bumpMap={body.rocky && !textures[`${id}-normal`] ? map : undefined}
          bumpScale={body.rocky && !textures[`${id}-normal`] ? 0.045 : 0} />
    </mesh>
    {id === 'earth' && <mesh ref={clouds} rotation={[0, 2.8, 0]}>
      <sphereGeometry args={[radius * 1.008, detail ? 80 : 24, detail ? 48 : 16]}/>
      <meshStandardMaterial color="#ffffff" alphaMap={textures.clouds} transparent
        opacity={0.92} depthWrite={false} roughness={1}/>
    </mesh>}
    {body.atmosphere && <Atmosphere radius={radius} color={body.atmosphere} detail={detail}/>}
    {id === 'saturn' && <Rings radius={radius} texture={textures.rings}/>}
    {id === 'uranus' && <mesh rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius * 1.6, radius * 1.62, 128]}/>
      <meshBasicMaterial color="#b8d9db" transparent opacity={0.18} side={THREE.DoubleSide}/>
    </mesh>}
  </group>;
}
