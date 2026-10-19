/**
 * 深空元件：星空、粒子带、大气、日面、日冕、日珥、行星环、奥尔特云与彗星。
 *
 * 所有形状都由「固定种子 + 帧号」算出：静态元件不随时间变化，会动的元件
 * （粒子带自转、日面颗粒、日珥脉动、彗尾呼吸）只读 `elapsedSeconds`。
 */
import {useMemo} from 'react';
import * as THREE from 'three';
import {useSceneContext} from '../context';
import {hashSeed, seededRandom, type Vec3} from './camera';

// ------------------------------------------------------------------ 深空元件

const FRESNEL_VERTEX = `
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormal = normalize(mat3(modelMatrix) * normal);
  vView = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const FRESNEL_FRAGMENT = `
uniform vec3 glowColor;
uniform float intensity;
uniform float power;
uniform float bias;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  float rim = pow(clamp(bias - dot(vNormal, vView), 0.0, 1.0), power);
  gl_FragColor = vec4(glowColor * rim * intensity, rim * intensity);
}`;

function fresnelMaterial(color: string, intensity: number, power: number, bias: number, side: THREE.Side) {
  return new THREE.ShaderMaterial({
    uniforms: {
      glowColor: {value: new THREE.Color(color)},
      intensity: {value: intensity},
      power: {value: power},
      bias: {value: bias},
    },
    vertexShader: FRESNEL_VERTEX,
    fragmentShader: FRESNEL_FRAGMENT,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side,
  });
}

/**
 * 圆形点精灵：默认的 `PointsMaterial` 在没有贴图时画的是方形，远景星点会变成
 * 「雪花」。共享一张 64×64 的径向渐变即可得到圆形点，且完全确定性。
 */
let dotTexture: THREE.DataTexture | null = null;
function softDot(): THREE.DataTexture {
  if (dotTexture) return dotTexture;
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = (x + 0.5) / size * 2 - 1;
      const dy = (y + 0.5) / size * 2 - 1;
      const falloff = Math.max(0, 1 - Math.hypot(dx, dy));
      const index = (y * size + x) * 4;
      data[index] = 255; data[index + 1] = 255; data[index + 2] = 255;
      data[index + 3] = Math.round(255 * falloff * falloff);
    }
  }
  dotTexture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  dotTexture.needsUpdate = true;
  return dotTexture;
}

/** 星空：固定种子的球壳点云，不随时间变化，作为深空的静态参照。 */
export function Starfield({count = 1400, radius = 1200, seed = 'stars', color = '#ffffff',
                           size = 2.4, opacity = 0.85}: {
  count?: number; radius?: number; seed?: string; color?: string; size?: number; opacity?: number;
}) {
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const distance = radius * (0.85 + random() * 0.3);
      positions[index * 3] = distance * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = distance * Math.cos(phi);
      positions[index * 3 + 2] = distance * Math.sin(phi) * Math.sin(theta);
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, radius, seed]);
  return (
    <points geometry={geometry}>
      <pointsMaterial map={softDot()} color={color} size={size} sizeAttenuation transparent
        opacity={opacity} depthWrite={false} alphaTest={0.01}/>
    </points>
  );
}

/** 粒子带：小行星带、柯伊伯带这类环形粒子；自转由帧号驱动。 */
export function ParticleBelt({count = 900, innerRadius = 8, outerRadius = 12, thickness = 0.6,
                              seed = 'belt', color = '#cbb79a', size = 0.9, spin = 0.03, opacity = 0.9}: {
  count?: number; innerRadius?: number; outerRadius?: number; thickness?: number;
  seed?: string; color?: string; size?: number; spin?: number; opacity?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = random() * Math.PI * 2;
      const distance = innerRadius + random() * (outerRadius - innerRadius);
      positions[index * 3] = Math.cos(angle) * distance;
      positions[index * 3 + 1] = (random() - 0.5) * thickness;
      positions[index * 3 + 2] = Math.sin(angle) * distance;
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, innerRadius, outerRadius, thickness, seed]);
  return (
    <points geometry={geometry} rotation={[0, elapsedSeconds * spin, 0]}>
      <pointsMaterial map={softDot()} color={color} size={size} sizeAttenuation transparent
        opacity={opacity} depthWrite={false} alphaTest={0.01}/>
    </points>
  );
}

/** 大气：外层菲涅尔边缘光，加法混合，从背面绘制。 */
export function Atmosphere({radius, color = '#4b9dff', intensity = 1.1, power = 2.6, bias = 0.85}: {
  radius: number; color?: string; intensity?: number; power?: number; bias?: number;
}) {
  const material = useMemo(() => fresnelMaterial(color, intensity, power, bias, THREE.BackSide),
    [color, intensity, power, bias]);
  return <mesh material={material}><sphereGeometry args={[radius * 1.045, 64, 48]}/></mesh>;
}

/**
 * 日冕：面向相机的径向辉光。
 *
 * 之前的球壳菲涅尔在轮廓处形成一圈硬边橙色圆环（像描边而不是辉光）。改成
 * 始终朝向相机的径向渐变后，外缘连续衰减到零；渐变峰值落在日面轮廓外侧。
 */
export function Corona({radius, color = '#ff9a3c', intensity = 0.9, power = 3.2, bias = 0.95}: {
  radius: number; color?: string; intensity?: number; power?: number; bias?: number;
}) {
  const texture = useMemo(() => {
    const size = 256;
    const data = new Uint8Array(size * size * 4);
    const tint = new THREE.Color(color);
    // 日面占精灵半宽的 1/2.2；峰值落在轮廓外，向内快速归零，向外按幂衰减。
    const limb = 1 / 2.2;
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        const dx = (x + 0.5) / size * 2 - 1;
        const dy = (y + 0.5) / size * 2 - 1;
        const r = Math.hypot(dx, dy);
        const rise = Math.min(1, Math.max(0, (r - limb * 0.82) / (limb * 0.28)));
        const fall = Math.pow(Math.max(0, 1 - r), power);
        const alpha = rise * fall * bias;
        const index = (y * size + x) * 4;
        data[index] = Math.round(tint.r * 255);
        data[index + 1] = Math.round(tint.g * 255);
        data[index + 2] = Math.round(tint.b * 255);
        data[index + 3] = Math.round(255 * alpha);
      }
    }
    const map = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
    map.needsUpdate = true;
    return map;
  }, [color, power, bias]);
  return <sprite scale={[radius * 4.4, radius * 4.4, 1]}>
    <spriteMaterial map={texture} transparent opacity={intensity} depthWrite={false}
      blending={THREE.AdditiveBlending} toneMapped={false}/>
  </sprite>;
}

/** 日面：临边昏暗 + 帧驱动的颗粒噪声，不需要贴图也能有表面细节。 */
const SUN_VERTEX = `
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormal = normalize(mat3(modelMatrix) * normal);
  vView = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const SUN_FRAGMENT = `
uniform vec3 baseColor;
uniform vec3 hotColor;
uniform float time;
uniform float granulation;
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vView;
float noise(vec2 point) {
  return fract(sin(dot(point, vec2(41.13, 289.7))) * 43758.5453123);
}
void main() {
  vec2 cell = floor(vUv * 220.0);
  float grain = noise(cell + floor(time * 6.0));
  float limb = pow(clamp(dot(vNormal, vView), 0.0, 1.0), 0.55);
  vec3 color = mix(baseColor, hotColor, grain * granulation);
  gl_FragColor = vec4(color * (0.55 + 0.45 * limb), 1.0);
}`;

export function SunSurface({radius, color = '#ffb44d', hotColor = '#fff1c2', granulation = 0.6, speed = 0.35}: {
  radius: number; color?: string; hotColor?: string; granulation?: number; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      baseColor: {value: new THREE.Color(color)},
      hotColor: {value: new THREE.Color(hotColor)},
      time: {value: 0},
      granulation: {value: granulation},
    },
    vertexShader: SUN_VERTEX, fragmentShader: SUN_FRAGMENT,
  }), [color, hotColor, granulation]);
  material.uniforms.time.value = elapsedSeconds * speed;
  return <mesh material={material}><sphereGeometry args={[radius, 96, 64]}/></mesh>;
}

/**
 * 日珥：从日面升起的热等离子弧。
 *
 * 旧实现把部分圆环（torus）随机旋转后贴在球面上，圆环平面常常侧对镜头，
 * 在画面里表现为几片孤立的长方形。这里改成**两根落脚点之间的拱形管**：
 * 拱面包含表面法线，从任何角度看都是从日面长出来的弧。
 */
export function Prominence({radius, color = '#ff7a3c', count = 5, seed = 'prominence',
                            height = 0.9, speed = 0.25}: {
  radius: number; color?: string; count?: number; seed?: string; height?: number; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const arcs = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const up = new THREE.Vector3(0, 1, 0);
    return Array.from({length: count}, () => {
      const theta = random() * Math.PI * 2;
      const phi = (random() - 0.5) * Math.PI * 0.7;
      const spread = 0.12 + random() * 0.2;
      const lift = 0.2 + random() * height;
      const normal = new THREE.Vector3(Math.cos(phi) * Math.cos(theta), Math.sin(phi),
        Math.cos(phi) * Math.sin(theta)).normalize();
      let tangent = new THREE.Vector3().crossVectors(normal, up);
      if (tangent.lengthSq() < 1e-4) tangent = new THREE.Vector3(1, 0, 0);
      tangent.normalize();
      const footA = normal.clone().addScaledVector(tangent, -spread).normalize()
        .multiplyScalar(radius * 0.995);
      const footB = normal.clone().addScaledVector(tangent, spread).normalize()
        .multiplyScalar(radius * 0.995);
      const apex = normal.clone().multiplyScalar(radius * (1.12 + lift * 1.1));
      const curve = new THREE.QuadraticBezierCurve3(footA, apex, footB);
      const geometry = new THREE.TubeGeometry(curve, 48, radius * 0.026, 10, false);
      return {geometry, phase: random() * Math.PI * 2};
    });
  }, [count, seed, radius, height]);
  return (
    <group>
      {arcs.map((item, index) => {
        const pulse = 0.55 + 0.25 * Math.sin(elapsedSeconds * speed * Math.PI * 2 + item.phase);
        return (
          <mesh key={index} geometry={item.geometry}>
            <meshBasicMaterial color={color} transparent opacity={pulse}
              blending={THREE.AdditiveBlending} depthWrite={false}/>
          </mesh>
        );
      })}
    </group>
  );
}

/** 行星环：确定性径向条纹生成 alpha，展开时不糊；也可换成已登记素材。 */
export function Rings({innerRadius, outerRadius, color = '#d9c19a', opacity = 0.92,
                       seed = 'rings', tilt = 0}: {
  innerRadius: number; outerRadius: number; color?: string; opacity?: number; seed?: string; tilt?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const texture = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const width = 1024;
    const data = new Uint8Array(width * 4);
    let band = 0.6 + random() * 0.4;
    for (let index = 0; index < width; index += 1) {
      if (index % Math.max(2, Math.floor(6 + random() * 40)) === 0) band = 0.25 + random() * 0.75;
      const cassini = Math.abs(index / width - 0.62) < 0.012 ? 0.08 : 1;
      const alpha = Math.max(0, Math.min(1, band * cassini));
      data[index * 4] = 255; data[index * 4 + 1] = 255; data[index * 4 + 2] = 255;
      data[index * 4 + 3] = Math.round(alpha * 255);
    }
    const map = new THREE.DataTexture(data, width, 1, THREE.RGBAFormat);
    map.wrapS = map.wrapT = THREE.RepeatWrapping;
    map.needsUpdate = true;
    return map;
  }, [seed]);
  return (
    <mesh rotation={[Math.PI / 2 + THREE.MathUtils.degToRad(tilt), elapsedSeconds * 0.01, 0]}>
      <ringGeometry args={[innerRadius, outerRadius, 160, 1]}/>
      <meshStandardMaterial map={texture} color={color} transparent opacity={opacity}
        alphaMap={texture} side={THREE.DoubleSide} depthWrite={false}/>
    </mesh>
  );
}

/** 奥尔特云：极稀疏的远距离点云，可选日球层顶气泡边界。 */
export function OortCloud({count = 2000, radius = 1800, thickness = 420, seed = 'oort',
                           color = '#8fb6ff', size = 1.8, bubble, bubbleColor = '#6fa8ff',
                           bubbleOpacity = 0.12}: {
  count?: number; radius?: number; thickness?: number; seed?: string; color?: string;
  size?: number; bubble?: number; bubbleColor?: string; bubbleOpacity?: number;
}) {
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const distance = radius + (random() - 0.5) * thickness;
      positions[index * 3] = distance * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = distance * Math.cos(phi) * 0.6;
      positions[index * 3 + 2] = distance * Math.sin(phi) * Math.sin(theta);
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, radius, thickness, seed]);
  // 日球层顶是**边界**而不是一层均匀的雾：用菲涅尔壳让轮廓亮、内部近乎透明。
  // 只画正面：相机在气泡内部时整面背面会把画面染蓝，而边界本来就该在飞出后回望时可见。
  const shell = useMemo(() => fresnelMaterial(bubbleColor, bubbleOpacity, 2.4, 0.92, THREE.FrontSide),
    [bubbleColor, bubbleOpacity]);
  return (
    <group>
      <points geometry={geometry}>
        <pointsMaterial map={softDot()} color={color} size={size} sizeAttenuation transparent
          opacity={0.7} depthWrite={false} alphaTest={0.01}/>
      </points>
      {bubble ? <mesh material={shell}><sphereGeometry args={[bubble, 64, 48]}/></mesh> : null}
    </group>
  );
}

/** 彗星：核 + 尾迹；尾巴始终背向 `sunPosition`，长度随帧号呼吸。 */
export function Comet({position = [0, 0, 0] as Vec3, radius = 0.5, tailLength = 14, tailRadius = 0.9,
                       color = '#bfe6ff', sunPosition = [0, 0, 0] as Vec3, seed = 'comet', speed = 0.4}: {
  position?: Vec3; radius?: number; tailLength?: number; tailRadius?: number;
  color?: string; sunPosition?: Vec3; seed?: string; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const random = useMemo(() => seededRandom(hashSeed(seed)), [seed]);
  const jitter = useMemo(() => [(random() - 0.5) * 0.2, (random() - 0.5) * 0.2], [random]);
  const nucleus = useMemo(() => new THREE.Vector3(...position), [position]);
  const sun = useMemo(() => new THREE.Vector3(...sunPosition), [sunPosition]);
  const direction = useMemo(() => nucleus.clone().sub(sun).normalize(), [nucleus, sun]);
  const quaternion = useMemo(() => new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), direction), [direction]);
  const breathe = 0.85 + 0.15 * Math.sin(elapsedSeconds * speed * Math.PI * 2);
  return (
    <group>
      <mesh position={position}>
        <sphereGeometry args={[radius, 24, 16]}/>
        <meshBasicMaterial color={color}/>
      </mesh>
      <mesh position={[position[0] + jitter[0], position[1] + jitter[1], position[2]]}
        quaternion={quaternion}>
        <coneGeometry args={[tailRadius * breathe, tailLength * breathe, 24, 1, true]}/>
        <meshBasicMaterial color={color} transparent opacity={0.28} side={THREE.DoubleSide}
          depthWrite={false} blending={THREE.AdditiveBlending}/>
      </mesh>
    </group>
  );
}
