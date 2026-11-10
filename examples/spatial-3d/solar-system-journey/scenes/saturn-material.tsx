import {useMemo} from 'react';
import * as THREE from 'three';
import model from './data/saturn.json';

/** NASA VTAD的专属UV扁球；来源、原包与数值提取均在JSON及SOURCES登记。 */
export const SATURN_POLAR_RATIO = model.polarRatio;

export function createSaturnGeometry(radius: number) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(
    model.positions.flat().map(value => value * radius), 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(model.normals.flat(), 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(model.uv.flat(), 2));
  geometry.setIndex(model.triangles.flat());
  geometry.computeBoundingSphere();
  return geometry;
}

const DUST_VERTEX = `
varying vec3 dustWorld;
varying vec3 dustCenter;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  dustWorld = world.xyz;
  dustCenter = (modelMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}`;
const DUST_FRAGMENT = `
uniform float radius;
varying vec3 dustWorld;
varying vec3 dustCenter;
void main() {
  float r = length(dustWorld - dustCenter) / radius;
  // 三个尺度的固定低密度层；不是对真实F/G/E环半径、密度或辐射的拟合。
  float pixel = max(fwidth(r), 0.001);
  // GLSL的pow对负底数未定义，整数指数也不能依赖驱动恰好给出平方。
  float fineOffset = (r - 2.33) / max(0.008, pixel * 0.7);
  float middleOffset = (r - 2.68) / max(0.014, pixel * 0.7);
  float wideOffset = (r - 3.12) / 0.48;
  float fine = exp(-(fineOffset * fineOffset));
  float middle = exp(-(middleOffset * middleOffset));
  float wide = exp(-(wideOffset * wideOffset))
    * smoothstep(2.35, 2.65, r) * (1.0 - smoothstep(3.7, 4.2, r));
  vec3 sun = normalize(-dustWorld);
  vec3 viewer = normalize(cameraPosition - dustWorld);
  // 入射传播方向为-sun；g与归一化系数是受控艺术权重，不宣称实测散射。
  float cosine = clamp(-dot(sun, viewer), -1.0, 1.0);
  float phase = clamp(0.026 * (1.0 - 0.88 * 0.88)
    / pow(max(0.012, 1.0 + 0.88 * 0.88 - 2.0 * 0.88 * cosine), 1.5), 0.08, 1.5);
  float lod = 1.0 - smoothstep(18.0, 35.0, length(cameraPosition - dustCenter) / radius);
  float alpha = clamp((fine * 0.12 + middle * 0.10 + wide * 0.055)
    * (0.55 + phase * 0.45) * lod, 0.0, 0.25);
  vec3 tint = mix(vec3(0.20, 0.29, 0.48), vec3(0.65, 0.56, 0.39), fine);
  gl_FragColor = vec4(tint, alpha);
}`;

/** 同一环面内的固定弱尘层；逐帧只读机位，不累计状态、不切换天体可见性。 */
export function SaturnDust({radius}: {radius: number}) {
  const uniforms = useMemo(() => ({radius: {value: radius}}), [radius]);
  return <mesh rotation={[-Math.PI / 2, 0, 0]}>
    <ringGeometry args={[radius * 2.29, radius * 4.2, 192, 1]}/>
    <shaderMaterial uniforms={uniforms} vertexShader={DUST_VERTEX} fragmentShader={DUST_FRAGMENT}
      transparent depthWrite={false} side={THREE.DoubleSide} blending={THREE.AdditiveBlending}/>
  </mesh>;
}
