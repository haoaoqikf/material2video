/** 大气/边缘光：略大于本体的球壳，克制透明，不遮挡主体细节。 */
import {THREE} from 'm2v/code-scene';

export type AtmosphereProps = {
  radius: number;
  color?: string;
  opacity?: number;
  scale?: number;
  segments?: number;
};

export default function Atmosphere({
  radius, color = '#9fb6cf', opacity = 0.16, scale = 1.08, segments = 64,
}: AtmosphereProps) {
  return (
    <mesh scale={scale}>
      <sphereGeometry args={[radius, segments, Math.max(16, Math.floor(segments / 2))]}/>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.BackSide}
        depthWrite={false}
      />
    </mesh>
  );
}
