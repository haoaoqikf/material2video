/** 深空舞台：近黑背景、透视相机、look、灯光、星场与克制后期；作品把世界作为 children。 */
import type {ReactNode} from 'react';
import {
  Canvas, LookProvider, PerspectiveCamera, PostFX, Starfield,
  type Look, type Shot,
} from 'm2v/code-scene';
import {T} from './kit';

export type SpaceStageProps = {
  look?: Look;
  shots?: Shot[];
  fov?: number;
  near?: number;
  far?: number;
  position?: [number, number, number];
  background?: string;
  starfield?: boolean;
  starCount?: number;
  starSeed?: string;
  postfx?: boolean;
  dpr?: number;
  children?: ReactNode;
};

export default function SpaceStage({
  look, shots, fov = T.motion.fov, near = 0.02, far = 4000,
  position = [3.4, 0.35, 1.0], background = T.canvas.background,
  starfield = true, starCount = 900, starSeed = 'deep-journey',
  postfx = true, dpr = 1, children,
}: SpaceStageProps) {
  return (
    <Canvas dpr={dpr} gl={{antialias: false, alpha: false, powerPreference: 'high-performance'}}>
      <color attach="background" args={[background]}/>
      <PerspectiveCamera makeDefault fov={fov} near={near} far={far} position={position}/>
      <LookProvider look={look} shots={shots}>
        <ambientLight intensity={0.4}/>
        {/* 光源来自世界中心；强度与衰减保持稳定，避免远处天体被照成白盘。 */}
        <pointLight position={[0, 0, 0]} intensity={1.9} decay={0} color="#fff0d7"/>
        {starfield && (
          <Starfield
            count={starCount}
            radius={900}
            seed={starSeed}
            size={0.9}
            opacity={T.canvas.starOpacity}
          />
        )}
        {children}
        {postfx && <PostFX/>}
      </LookProvider>
    </Canvas>
  );
}
