/** 通用球体表面：颜色/贴图/自发光；复杂 shader 与天体特例由作品实现。 */
import {useMemo} from 'react';
import {THREE} from 'm2v/code-scene';

export type PlanetSurfaceProps = {
  radius: number;
  color?: string;
  map?: THREE.Texture | null;
  emissive?: string;
  emissiveIntensity?: number;
  opacity?: number;
  transparent?: boolean;
  roughness?: number;
  metalness?: number;
  segments?: number;
  rotation?: [number, number, number];
};

export default function PlanetSurface({
  radius, color = '#cfe0f2', map = null, emissive = '#000000',
  emissiveIntensity = 0, opacity = 1, transparent = false,
  roughness = 0.9, metalness = 0.02, segments = 64, rotation = [0, 0, 0],
}: PlanetSurfaceProps) {
  const geometry = useMemo(
    () => new THREE.SphereGeometry(radius, segments, Math.max(16, Math.floor(segments / 2))),
    [radius, segments],
  );
  return (
    <mesh geometry={geometry} rotation={rotation}>
      <meshStandardMaterial
        color={color}
        map={map ?? undefined}
        emissive={emissive}
        emissiveIntensity={emissiveIntensity}
        opacity={opacity}
        transparent={transparent}
        roughness={roughness}
        metalness={metalness}
      />
    </mesh>
  );
}
