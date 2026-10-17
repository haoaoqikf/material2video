import {useEffect, useMemo, useRef, useState} from 'react';
import {Billboard} from '@react-three/drei/core/Billboard.js';
import {THREE, useFrame, useMediaAsset, useThree} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {smooth} from './clock';

export type EarthUniforms = {
  uSunView: {value: THREE.Vector3};
  uClouds: {value: THREE.Texture | null};
  uNight: {value: number};
  uCloudShadow: {value: number};
};

/**
 * 地球 hero 的表面细节：夜面城市灯光、海面高光（按陆地/海洋改粗糙度）与云影。
 *
 * 三点都由材质自身的贴图与**视空间太阳方向**算出：太阳方向每帧从相机矩阵更新，
 * 因此昼夜分界永远与场景里的点光源一致；没有引入新的时间或随机源。
 */
export function earthSurface(shader: Parameters<THREE.MeshStandardMaterial['onBeforeCompile']>[0],
                             uniforms: EarthUniforms) {
  Object.assign(shader.uniforms, uniforms);
  // 城市点阵锚在**物体空间**法线上：用视空间法线会让灯光随相机游动。
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', '#include <common>\n      varying vec3 vObjectNormal;')
    .replace('#include <beginnormal_vertex>',
             '#include <beginnormal_vertex>\n      vObjectNormal = normalize(objectNormal);');
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <common>', `#include <common>
      uniform vec3 uSunView;
      uniform sampler2D uClouds;
      uniform float uNight;
      uniform float uCloudShadow;
      varying vec3 vObjectNormal;
      float m2vCityHash(vec3 p) {
        return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453123);
      }`)
    // 陆地哑光、海洋高光：直接改标准材质的粗糙度，不另写一套光照。
    .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
      float m2vLand = smoothstep(0.02, 0.16, diffuseColor.r + diffuseColor.g - diffuseColor.b);
      roughnessFactor = mix(0.14, 0.86, m2vLand);`)
    .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
      {
        // GLSL 未定义 edge0 >= edge1 的 smoothstep；反转结果保证跨 GPU 一致。
        float m2vNight = 1.0 - smoothstep(-0.24, 0.06, dot(normalize(vNormal), normalize(uSunView)));
        float cluster = m2vCityHash(floor(vObjectNormal * 46.0));
        float lights = smoothstep(0.86, 0.97, cluster) * m2vLand * m2vNight;
        totalEmissiveRadiance += vec3(1.0, 0.74, 0.46) * lights * uNight;
        // 云图是灰度 JPEG，没有 alpha；与云层 alphaMap 一样读取绿色通道。
        float cloud = texture2D(uClouds, vMapUv).g;
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
      texture.colorSpace = id === 'clouds' ? THREE.NoColorSpace : THREE.SRGBColorSpace;
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
  float rim = pow(1.0 - max(dot(normalize(vNormal), normalize(vView)), 0.0), 3.8);
  gl_FragColor = vec4(tint, rim * 0.52);
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
    vec3 toCenter = solarCenter - solarPosition;
    float along = dot(toCenter, rayToSun);
    float distance2 = dot(toCenter, toCenter) - along * along;
    if (along > 0.0 && distance2 < solarRadius * solarRadius) outgoingLight *= 0.16;`;
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

function Corona({radius, clock}: {radius: number; clock: TimeSource}) {
  const material = useMemo(() => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: {time: {value: 0}},
    vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `varying vec2 vUv; uniform float time;
      void main(){vec2 p=vUv*2.0-1.0; float r=length(p); float a=atan(p.y,p.x);
      float rays=0.6+0.22*sin(a*37.0+time*0.24)+0.12*sin(a*79.0-time*0.17);
      float glow=exp(-max(0.0,r-0.49)*13.0)*smoothstep(0.46,0.53,r);
      glow*=1.0-smoothstep(0.82,1.0,r);
      gl_FragColor=vec4(1.0,0.34+0.18*glow,0.055,glow*rays*0.64);}`,
  }), []);
  useFrame(() => {material.uniforms.time.value = clock.current.seconds;});
  useEffect(() => () => material.dispose(), [material]);
  return <Billboard><mesh position={[0, 0, -0.2]} material={material}>
      <planeGeometry args={[radius * 4, radius * 4]}/>
    </mesh></Billboard>;
}

function proceduralSurface(id: string): THREE.DataTexture | undefined {
  if (id !== 'ceres' && id !== 'titan') return undefined;
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
      if (id === 'ceres') for (let i = 0; i < 28; i++) {
        const cy = 1 - 2 * (i + 0.5) / 28;
        const angle = i * 2.399963;
        const s = Math.sqrt(1 - cy * cy);
        const d = Math.hypot(px - Math.cos(angle) * s, py - cy, pz - Math.sin(angle) * s);
        const r = 0.045 + (i % 4) * 0.02;
        value -= Math.exp(-(d * d) / (r * r)) * 0.18;
        value += Math.exp(-Math.pow((d - r * 1.3) / (r * 0.18), 2)) * 0.10;
      }
      const index = (y * width + x) * 4;
      const rgb = id === 'titan' ? [212, 155, 74] : [173, 168, 156];
      const shade = id === 'titan' ? 0.95 + value * 0.08 : 0.55 + value;
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

export function Planet({id, textures, clock, radius = 2.35, phase = 0, detail = true}: {
  id: string; textures: Textures; clock: TimeSource; radius?: number; phase?: number; detail?: boolean;
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
    uNight: {value: 1.8},
    uCloudShadow: {value: 0.38},
  }), [textures.clouds]);
  useFrame(() => {
    const rotation = clock.current.seconds * (id === 'venus' ? -0.018 : 0.026);
    if (sphere.current) sphere.current.rotation.y = 2.8 + rotation;
    if (clouds.current) clouds.current.rotation.y = 2.8 + rotation * 1.12;
    if (id === 'earth' && sphere.current) {
      // 太阳在世界原点：把「从星球指向太阳」的方向转到视空间，与 vNormal 同一空间。
      const world = sphere.current.getWorldPosition(new THREE.Vector3());
      earthUniforms.uSunView.value.copy(world.negate().normalize())
        .transformDirection(camera.matrixWorldInverse);
    }
  });
  return <group rotation={[id === 'saturn' ? 0.38 + smooth(phase) * 0.28 : 0.1, 0, -(body.tilt ?? 8) * Math.PI / 180]}>
    {id === 'sun' && <Corona radius={radius} clock={clock}/>}
    <mesh ref={sphere} rotation={[0, 2.8, 0]}>
      <sphereGeometry args={[radius, detail ? 96 : 24, detail ? 64 : 16]}/>
      {id === 'sun' ? <meshBasicMaterial map={textures.sun} color="#ffc078" toneMapped={false}/> :
        <meshStandardMaterial map={map}
          customProgramCacheKey={() => id === 'saturn' ? 'solar-sphere-ring-shadow-v1'
            : id === 'earth' ? 'solar-earth-cinematic-v1' : 'solar-planet-v1'}
          onBeforeCompile={shader => {
            if (id === 'saturn') saturnShadow(shader, radius, textures.rings);
            if (id === 'earth') earthSurface(shader, earthUniforms);
          }}
          color={map ? '#ffffff' : body.color} roughness={id === 'earth' ? 0.62 : 0.96}
          metalness={0} bumpMap={body.rocky ? map : undefined}
          bumpScale={body.rocky ? 0.045 : 0} />}
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
