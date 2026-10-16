import {useRef} from 'react';
import {Canvas, Float, Stars, THREE, useFrame, useSceneContext} from 'm2v/code-scene';

function Object3D() {
  const ref = useRef<THREE.Mesh>(null);
  const {running} = useSceneContext();
  useFrame((_, delta) => {if (running && ref.current) ref.current.rotation.y += delta * .7;});
  return <Float speed={1.2}><mesh ref={ref}>
    <icosahedronGeometry args={[1.4, 2]}/>
    <shaderMaterial vertexShader={`varying vec3 v; void main(){v=normal; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`}
      fragmentShader={`varying vec3 v; void main(){gl_FragColor=vec4(0.3+0.5*abs(v.x),0.5+0.3*abs(v.y),0.85,1.0);}`}/>
  </mesh></Float>;
}
export default function ThreeWorld() {
  const {ready} = useSceneContext();
  return <Canvas camera={{position: [0, 0, 5]}} onCreated={() => ready()}>
    <color attach="background" args={['#111720']}/>
    <ambientLight intensity={.7}/><directionalLight position={[3, 4, 5]}/>
    <Object3D/><Stars radius={12} depth={15} count={400} factor={2}/>
  </Canvas>;
}
