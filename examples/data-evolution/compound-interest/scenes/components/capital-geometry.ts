import * as THREE from 'three';
import {CAPITAL_STYLE} from '../capital-style';

/** 圆面轮廓必须从外向内，Lathe的正面法线才朝向镜头；否则凸面会被背面剔除。 */
export function createCapitalGeometry() {
  const shape = new THREE.Shape();
  shape.absarc(0, 0, CAPITAL_STYLE.radius - 1.5, 0, Math.PI * 2, false);
  const body = new THREE.ExtrudeGeometry(shape, {depth: 6, bevelEnabled: true,
    bevelSegments: 4, steps: 1, bevelSize: 1.5, bevelThickness: 1.5, curveSegments: 40});
  body.translate(0, 0, -3);
  const face = new THREE.LatheGeometry([
    new THREE.Vector2(19.3, 4.4), new THREE.Vector2(18.5, 5.3),
    new THREE.Vector2(16, 6.2), new THREE.Vector2(11, 6.95),
    new THREE.Vector2(5, 7.35), new THREE.Vector2(0, CAPITAL_STYLE.faceHeight),
  ], 96);
  face.rotateX(Math.PI / 2);
  // 成熟Cylinder几何的径向参数化，齿缘只改变厚边，不改变圆面金额面积。
  const edge = new THREE.CylinderGeometry(20.8, 20.8, 5.5, 384, 1, true);
  const positions = edge.getAttribute('position');
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i), z = positions.getZ(i);
    const radius = 20.72 + .22 * Math.cos(Math.atan2(z, x) * 96);
    const scale = radius / Math.hypot(x, z);
    positions.setXYZ(i, x * scale, positions.getY(i), z * scale);
  }
  edge.computeVertexNormals();
  edge.rotateX(Math.PI / 2);
  return {body, face, edge};
}
