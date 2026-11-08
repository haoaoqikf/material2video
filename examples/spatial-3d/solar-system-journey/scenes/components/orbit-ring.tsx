/** 轨道环：稳定空间参照；可高亮当前主体，不表示精确历算。 */
import {useMemo} from 'react';
import * as THREE from 'three';

export type OrbitRingProps = {
  radius: number;
  active?: boolean;
  faint?: boolean;
  color?: string;
  activeColor?: string;
  segments?: number;
  opacity?: number;
  activeOpacity?: number;
  rotation?: [number, number, number];
};

export default function OrbitRing({
  radius, active = false, faint = false,
  color = '#496b82', activeColor = '#ddbd7c',
  segments = 256, opacity = 0.055, activeOpacity = 0.24,
  rotation = [0, 0, 0],
}: OrbitRingProps) {
  const geometry = useMemo(
    () => new THREE.BufferGeometry().setFromPoints(
      Array.from({length: segments + 1}, (_, index) => {
        const angle = (index / segments) * Math.PI * 2;
        return new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
      }),
    ),
    [radius, segments],
  );
  const material = useMemo(
    () => new THREE.LineBasicMaterial({
      color: active ? activeColor : color,
      transparent: true,
      opacity: active ? activeOpacity : faint ? 0.015 : opacity,
    }),
    [active, activeColor, color, faint, opacity, activeOpacity],
  );
  const line = useMemo(() => new THREE.LineLoop(geometry, material), [geometry, material]);
  return <primitive object={line} rotation={rotation}/>;
}
