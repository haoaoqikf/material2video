import {THREE} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {LAYOUT, positionOf, type Pose} from './layout';

/** 标签投影与相机读取同一个姿态；不为每个标签创建独立 React 根。 */
export function Labels({pose, width, height, target}: {pose: Pose; width: number; height: number; target: string}) {
  if (pose.overview <= 0.5) return null;
  const camera = new THREE.PerspectiveCamera(40, width / height, 0.02, 2000);
  camera.position.copy(pose.eye);
  camera.lookAt(pose.target);
  camera.updateMatrixWorld();
  return <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
    {Object.entries(LAYOUT).filter(([, item]) => !item.parent).map(([id, item]) => {
      const p = positionOf(id).add(new THREE.Vector3(0, item.radius + 1.2, 0)).project(camera);
      const x = (p.x + 1) * width / 2, y = (1 - p.y) * height / 2;
      if (p.z < -1 || p.z > 1 || x < 550 || x > width - 60 || y < 170 || y > 790) return null;
      return <div key={id} style={{position: 'absolute', left: x, top: y, transform: 'translate(-50%, -100%)',
        color: id === target ? '#f3d39f' : '#c5d2de', fontSize: 17, whiteSpace: 'nowrap',
        padding: '3px 8px', background: 'rgba(2,5,10,0.7)', borderRadius: 3,
        opacity: Math.min(1, (pose.overview - 0.5) * 2)}}>{BODIES[id].name}</div>;
    })}
  </div>;
}
