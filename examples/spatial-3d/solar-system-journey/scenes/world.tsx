import {useEffect, useMemo, useRef, useState} from 'react';
import * as THREE from 'three';
import {useFrame, useThree} from '@react-three/fiber';
import {useMediaAsset} from '../src/code-scene/media';
import {BODIES} from './bodies';
import {positionOf} from './layout';
import {createSaturnGeometry, SATURN_POLAR_RATIO, SaturnDust} from './saturn-material';

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
    .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
      // 保留海陆粗糙度差异，同时抑制压缩贴图中的近零值产生的镜面白点。
      roughnessFactor = max(0.62, roughnessFactor);`)
    .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
      {
        // GLSL 未定义 edge0 >= edge1 的 smoothstep；反转结果保证跨 GPU 一致。
        float m2vNight = 1.0 - smoothstep(-0.24, 0.06, dot(normalize(vNormal), normalize(uSunView)));
        vec3 lights = texture2D(uNightMap, vMapUv).rgb;
        totalEmissiveRadiance += lights * m2vNight * uNight;
        // 云图是灰度 JPEG，没有 alpha；与云层 alphaMap 一样读取绿色通道。
        float cloud = texture2D(uClouds, vMapUv + vec2(uCloudOffset, 0.0)).g;
        diffuseColor.rgb *= 1.0 - cloud * uCloudShadow;
        float grey = dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722));
        diffuseColor.rgb = max(vec3(0.0), mix(vec3(grey), diffuseColor.rgb, 1.10));
      }`)
    .replace('#include <opaque_fragment>', `
      // 只调整地球日面的展示曝光，夜景与同一世界里的其他天体不随之提亮。
      float daylight = smoothstep(0.0, 0.42, dot(normalize(vNormal), normalize(uSunView)));
      outgoingLight *= mix(1.0, 1.65, daylight);
      #include <opaque_fragment>`);
}

/** 逐项通过素材 ID 解析；固定钩子顺序，来源清单中的全部素材均实际用于本作品。 */
export function useTextureSources() {
  return {
    sun: useMediaAsset('sun').src, mercury: useMediaAsset('mercury').src,
    venus: useMediaAsset('venus').src, earth: useMediaAsset('earth').src,
    moon: useMediaAsset('moon').src, mars: useMediaAsset('mars').src,
    ceres: useMediaAsset('ceres').src,
    'ceres-normal': useMediaAsset('ceres-normal').src,
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
uniform vec3 uSunView;
uniform float softRim;
uniform float rimPower;
uniform float featherRim;
uniform float rimStrength;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  // 归一化点积仍可能因浮点舍入超过1；小数次幂不能接收负底数。
  float mu = clamp(dot(normalize(vNormal), normalize(vView)), 0.0, 1.0);
  float rim = pow(1.0 - mu, rimPower);
  // 地球外缘在轮廓处归零，避免把球壳边界画成硬蓝描边；照明与日面方向一致。
  float feather = mix(1.0, smoothstep(0.0, 0.16, mu), featherRim);
  float daylight = mix(1.0, 0.18 + 0.82 * smoothstep(-0.25, 0.45,
    dot(normalize(vNormal), normalize(uSunView))), softRim);
  gl_FragColor = vec4(tint, rim * feather * daylight * rimStrength);
}`;

function Atmosphere({color, radius, detail, sunView, thin = false}: {color: string; radius: number; detail: boolean;
  sunView?: EarthUniforms['uSunView']; thin?: boolean}) {
  const uniforms = useMemo(() => ({tint: {value: new THREE.Color(color)},
    uSunView: sunView ?? {value: new THREE.Vector3(0, 0, 1)},
    softRim: {value: sunView ? 1 : 0}, featherRim: {value: sunView && !thin ? 1 : 0},
    rimPower: {value: thin ? 14 : 4.6},
    rimStrength: {value: thin ? 1.8 : 0.32}}), [color, sunView, thin]);
  return <mesh scale={thin ? [1.0062, 1.0062 * SATURN_POLAR_RATIO, 1.0062] : sunView ? 1.018 : 1.012}>
    <sphereGeometry args={[radius, detail ? 96 : 24, detail ? 64 : 16]}/>
    <shaderMaterial vertexShader={ATMOSPHERE_VERTEX} fragmentShader={ATMOSPHERE_FRAGMENT}
      uniforms={uniforms} transparent depthWrite={false} blending={THREE.AdditiveBlending}/>
  </mesh>;
}

/** 解析式日光遮挡：避免点光源六面阴影贴图在完整模型中重复渲染全部天体。 */
function saturnShadow(shader: Parameters<THREE.MeshStandardMaterial['onBeforeCompile']>[0],
  radius: number, ringTexture?: THREE.Texture) {
  // 球体所在组的Y轴是环面法线；RingGeometry的局部法线是Z，mesh另有X旋转。
  const ringNormal = ringTexture ? '0.0, 1.0, 0.0' : '0.0, 0.0, 1.0';
  shader.vertexShader = shader.vertexShader.replace('#include <common>', `#include <common>
    varying vec3 solarPosition; varying vec3 solarCenter; varying vec3 solarRingNormal;`)
    .replace('#include <begin_vertex>', `#include <begin_vertex>
      solarPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      solarCenter = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
      solarRingNormal = normalize(mat3(modelMatrix) * vec3(${ringNormal}));`);
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
    }
    // 环反照光的局部艺术近似：保留源图的暗金带状层次，不把夜面压成纯黑剪影。
    // 纬向权重只服务展示，不宣称由源图求得真实辐射量；太阳侧仍由世界方向决定。
    vec3 radialNormal = normalize(solarPosition - solarCenter);
    vec3 toViewer = normalize(cameraPosition - solarPosition);
    float litLimb = pow(1.0 - clamp(dot(radialNormal, toViewer), 0.0, 1.0), 18.0)
      * smoothstep(-0.06, 0.22, dot(radialNormal, rayToSun));
    float nightSide = 1.0 - smoothstep(-0.15, 0.2, dot(radialNormal, rayToSun));
    vec3 ringShine = diffuseColor.rgb * vec3(1.0, 0.76, 0.48) * 0.025
      * (0.10 + 0.9 * smoothstep(-0.35, 0.8, dot(radialNormal, normalize(solarRingNormal)))) * nightSide;
    outgoingLight = outgoingLight * 0.85 + ringShine + vec3(0.95, 0.78, 0.50) * litLimb * 1.5;` : `
    vec3 rayToSun = normalize(-solarPosition);
    // 冰粒前向散射的艺术近似：太阳在环背后时增强透光，仍受母星遮挡。
    vec3 rayToViewer = normalize(cameraPosition - solarPosition);
    float cosineScatter = clamp(-dot(rayToSun, rayToViewer), -1.0, 1.0);
    // HG形状加有界基底，既保受光方向，也保近侧缘及手机下的完整环形。
    float forwardScatter = 0.35 + 0.65 * clamp(0.026 * (1.0 - 0.88 * 0.88)
      / pow(max(0.012, 1.0 + 0.88 * 0.88 - 2.0 * 0.88 * cosineScatter), 1.5), 0.08, 1.5);
    float density = texture2D(map, vMapUv).a;
    // 源图alpha仅作相对密度，不是实测光学厚度。用入射/出射路径的消光
    // 形成疏环透亮、密环较暗的层级，代替把所有环条纹统一加亮的灰片。
    float incidence = max(abs(dot(normalize(solarRingNormal), rayToSun)), 0.12);
    float emergence = max(abs(dot(normalize(solarRingNormal), rayToViewer)), 0.12);
    float opticalDepth = density * density * 2.2;
    float transmitted = opticalDepth * exp(-opticalDepth * 0.5 * (1.0 / incidence + 1.0 / emergence));
    vec3 iceTint = mix(vec3(0.95, 0.72, 0.40), diffuseColor.rgb * 2.2, 0.45);
    float edgeDensity = abs(texture2D(map, vMapUv + vec2(0.0015, 0.0)).a
      - texture2D(map, vMapUv - vec2(0.0015, 0.0)).a);
    outgoingLight = outgoingLight * 0.3 + iceTint * forwardScatter * transmitted * 18.0
      + vec3(1.0, 0.82, 0.55) * min(edgeDensity * 3.0, 1.0) * forwardScatter * 0.13;
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
      customProgramCacheKey={() => 'solar-ring-transmission-v6'}
      onBeforeCompile={shader => saturnShadow(shader, radius)}
      emissiveMap={texture} emissive="#b9ac8a" emissiveIntensity={0.03}
      side={THREE.DoubleSide} roughness={0.96} metalness={0} depthWrite={false}/>
  </mesh>;
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

export function Planet({id, textures, clock, radius = 2.35, detail = true, faceFeature = false, ceresFocus = 0}: {
  id: string; textures: Textures; clock: TimeSource; radius?: number; detail?: boolean; ceresFocus?: number;
  /** 展示性朝向：让该天体的纹理地标（大红斑/心形）在镜头里正对机位。 */
  faceFeature?: boolean;
}) {
  const body = BODIES[id];
  const map = body.texture ? textures[body.texture] : undefined;
  const sphere = useRef<THREE.Mesh>(null);
  const clouds = useRef<THREE.Mesh>(null);
  const camera = useThree(state => state.camera);
  const saturnGeometry = useMemo(() => id === 'saturn' ? createSaturnGeometry(radius) : null, [id, radius]);
  useEffect(() => () => saturnGeometry?.dispose(), [saturnGeometry]);
  const saturnCenter = useMemo(() => positionOf('saturn'), []);
  const contextGain = useMemo(() => ({value: 1}), []);
  const jovian = id === 'jupiter' || body.parent === 'jupiter';
  const ceres = id === 'ceres';
  const earthUniforms = useMemo<EarthUniforms>(() => ({
    uSunView: {value: new THREE.Vector3(1, 0, 0)},
    uClouds: {value: textures.clouds ?? null},
      uNightMap: {value: textures['earth-emissive'] ?? null},
      uCloudOffset: {value: 0},
    uNight: {value: 0.55},
    uCloudShadow: {value: 0.12},
  }), [textures.clouds, textures['earth-emissive']]);
  useFrame(() => {
    // 土星附近仅压低远处木星系的光量，保留同一世界的实际形体；平滑变化避免跳暗。
    const distance = camera.position.distanceTo(saturnCenter);
    const t = Math.max(0, Math.min(1, (distance - 20) / 18));
    contextGain.value = jovian
      ? (0.4 + 0.6 * t * t * (3 - 2 * t)) * (1 - 0.9 * ceresFocus)
      : ceresFocus;
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
    if ((id === 'earth' || id === 'saturn') && sphere.current) {
      // 太阳在世界原点：把「从星球指向太阳」的方向转到视空间，与 vNormal 同一空间。
      const world = sphere.current.getWorldPosition(new THREE.Vector3());
      earthUniforms.uSunView.value.copy(world.negate().normalize())
        .transformDirection(camera.matrixWorldInverse);
    }
  });
  return <group rotation={[id === 'saturn' ? 0.4 : 0.1, 0, -(body.tilt ?? 8) * Math.PI / 180]}>
    <mesh ref={sphere} rotation={[0, 2.8, 0]}>
      {saturnGeometry ? <primitive object={saturnGeometry} attach="geometry"/>
        : <sphereGeometry args={[radius, detail ? 96 : 24, detail ? 64 : 16]}/>}
        <meshStandardMaterial map={map}
          // 每个天体的 onBeforeCompile 不同，缓存键必须带 id；共用键会让先编译的
          // 程序覆盖后来天体的着色器改动。
          customProgramCacheKey={() => id === 'saturn' ? 'solar-sphere-ring-shadow-v5'
            : id === 'earth' ? 'solar-earth-cinematic-v3' : id === 'sun' ? 'solar-limb-v1'
              : jovian || ceres ? `solar-depth-v2-${id}` : `solar-planet-v2-${id}`}
          onBeforeCompile={shader => {
            if (jovian) {
              shader.uniforms.m2vContextGain = contextGain;
              shader.fragmentShader = shader.fragmentShader
                .replace('#include <common>', '#include <common>\nuniform float m2vContextGain;')
                .replace('#include <opaque_fragment>', 'outgoingLight *= m2vContextGain;\n#include <opaque_fragment>');
            }
            if (ceres) {
              shader.uniforms.m2vContextGain = contextGain;
              shader.fragmentShader = shader.fragmentShader
                .replace('#include <common>', '#include <common>\nuniform float m2vContextGain;')
                .replace('#include <opaque_fragment>', `
                  // 轻微填光保留暗缘上的坑面，并让日照侧仍明显更亮。
                  outgoingLight *= 1.0 + m2vContextGain * 0.8;
                  outgoingLight += diffuseColor.rgb * (m2vContextGain * 0.16);
                  #include <opaque_fragment>`);
            }
            if (id === 'saturn') saturnShadow(shader, radius, textures.rings);
            if (id === 'earth') earthSurface(shader, earthUniforms);
            if (id === 'jupiter') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              // 只增强源纹理里已有的大红斑局部对比，不另画贴图地标。
              float m2vSpot = 1.0 - smoothstep(0.015, 0.045, distance(vMapUv, vec2(0.354, 0.390)));
              outgoingLight = mix(outgoingLight, outgoingLight * vec3(0.78, 0.42, 0.30),
                m2vSpot * 0.85);
              #include <opaque_fragment>`);
            if (id === 'pluto') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              // 心形氮冰平原在深空曝光下偏暗，按源图 UV 做局部提亮。
              float m2vHeart = 1.0 - smoothstep(0.02, 0.06, distance(vMapUv, vec2(0.459, 0.512)));
              outgoingLight = mix(outgoingLight,
                min(vec3(1.0), outgoingLight * 1.22 + 0.015), m2vHeart * 0.6);
              #include <opaque_fragment>`);
            if (id === 'sun') shader.fragmentShader = shader.fragmentShader.replace(
              '#include <opaque_fragment>', `
              float limb = pow(clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), 0.55);
              outgoingLight *= 0.55 + 0.45 * limb;
              #include <opaque_fragment>`);
          }}
          color={map ? '#ffffff' : body.color} roughness={textures[`${id}-roughness`] ? 1.0 : 0.96}
          roughnessMap={textures[`${id}-roughness`]}
          normalMap={textures[`${id}-normal`]} normalScale={new THREE.Vector2(id === 'earth' ? 0.12 : 0.35, id === 'earth' ? 0.12 : 0.35)}
          emissiveMap={id === 'titan' ? map : id === 'earth' ? undefined : textures[`${id}-emissive`]}
          // 没有 emissiveMap 的天体必须保持黑色自发光；否则白 emissive 会把月球、
          // 水星、金星、火星整颗渲染成没有纹理的白盘。
          emissive={id === 'earth' ? '#000000' : id === 'titan' ? '#ffb066'
            : id === 'sun' || textures[`${id}-emissive`] ? '#ffffff' : '#000000'}
          emissiveIntensity={id === 'sun' ? 0.88 : id === 'titan' ? 0.06 : 1} metalness={0}
          bumpMap={body.rocky && !textures[`${id}-normal`] ? map : undefined}
          bumpScale={body.rocky && !textures[`${id}-normal`] ? 0.045 : 0} />
    </mesh>
    {id === 'earth' && <mesh ref={clouds} rotation={[0, 2.8, 0]}>
      <sphereGeometry args={[radius * 1.008, detail ? 80 : 24, detail ? 48 : 16]}/>
      <meshStandardMaterial color="#ffffff" alphaMap={textures.clouds} transparent
        opacity={1} depthWrite={false} roughness={1}
        customProgramCacheKey={() => 'solar-cloud-density-v1'}
        onBeforeCompile={shader => {
          // 灰度云图重新拉开密度，保留白云与蓝海分离，避免整层半透明灰雾。
          shader.fragmentShader = shader.fragmentShader.replace('#include <alphamap_fragment>', `
            #ifdef USE_ALPHAMAP
              diffuseColor.a *= smoothstep(0.10, 0.90, texture2D(alphaMap, vAlphaMapUv).g);
            #endif`).replace('#include <opaque_fragment>', `
              outgoingLight *= 1.45;
              #include <opaque_fragment>`);
        }}/>
    </mesh>}
    {body.atmosphere && <Atmosphere radius={radius} color={id === 'saturn' ? '#fff4da' : body.atmosphere} detail={detail}
      thin={id === 'saturn'} sunView={id === 'earth' || id === 'saturn' ? earthUniforms.uSunView : undefined}/>}
    {id === 'saturn' && <Rings radius={radius} texture={textures.rings}/>}
    {id === 'saturn' && <SaturnDust radius={radius}/>}
    {id === 'uranus' && <mesh rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius * 1.6, radius * 1.62, 128]}/>
      <meshBasicMaterial color="#b8d9db" transparent opacity={0.18} side={THREE.DoubleSide}/>
    </mesh>}
  </group>;
}
