/** 建筑构件的 three.js 几何与材质：墙洞、屋面、楼梯与轮廓线。 */
import * as THREE from 'three';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type {BoxSpec, House, MaterialKey, WallSide} from './model';

export type MaterialMap = Record<MaterialKey, THREE.Material>;

export function createMaterials(): MaterialMap {
  const standard = (color: string, roughness: number, metalness = 0): THREE.MeshStandardMaterial =>
    new THREE.MeshStandardMaterial({color, roughness, metalness});
  return {
    site: standard('#6d7a5b', 0.98),
    soil: standard('#5a4635', 1),
    foundation: standard('#8d867a', 0.92),
    concrete: standard('#cfc9bd', 0.86),
    'concrete-dark': standard('#b1aa9e', 0.9),
    wall: standard('#f2ede3', 0.94),
    wood: standard('#b57d4b', 0.72),
    glass: new THREE.MeshPhysicalMaterial({
      color: '#9cc7d8', roughness: 0.08, metalness: 0, transparent: true,
      opacity: 0.42, depthWrite: false,
    }),
    roof: standard('#5a615c', 0.82, 0.08),
    yard: standard('#8d9a76', 0.96),
    ink: standard('#1f2225', 0.9),
  };
}

export function baseOpacity(material: MaterialKey): number {
  return material === 'glass' ? 0.42 : 1;
}

function wallShape(box: BoxSpec): THREE.Shape {
  const [width, height] = [box.size[0], box.size[1]];
  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, -height / 2);
  shape.lineTo(width / 2, -height / 2);
  shape.lineTo(width / 2, height / 2);
  shape.lineTo(-width / 2, height / 2);
  shape.closePath();
  for (const hole of box.holes ?? []) {
    const path = new THREE.Path();
    const left = hole.u - hole.width / 2;
    const right = hole.u + hole.width / 2;
    const bottom = hole.v - hole.height / 2;
    const top = hole.v + hole.height / 2;
    // 洞口反向绕行，ExtrudeGeometry 才会把它挖空。
    path.moveTo(left, bottom);
    path.lineTo(left, top);
    path.lineTo(right, top);
    path.lineTo(right, bottom);
    path.closePath();
    shape.holes.push(path);
  }
  return shape;
}

function gableShape(box: BoxSpec): THREE.Shape {
  const [width, height] = [box.size[0], box.size[1]];
  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, -height / 2);
  shape.lineTo(width / 2, -height / 2);
  shape.lineTo(0, height / 2);
  shape.closePath();
  return shape;
}

export function geometryFor(box: BoxSpec): THREE.BufferGeometry {
  const [w, h, d] = box.size;
  if (box.slabHole) {
    const hole = box.slabHole;
    const shape = new THREE.Shape();
    shape.moveTo(-w / 2, -d / 2);
    shape.lineTo(w / 2, -d / 2);
    shape.lineTo(w / 2, d / 2);
    shape.lineTo(-w / 2, d / 2);
    shape.closePath();
    const path = new THREE.Path();
    const left = hole.x - hole.width / 2;
    const right = hole.x + hole.width / 2;
    const near = hole.z - hole.depth / 2;
    const far = hole.z + hole.depth / 2;
    path.moveTo(left, near);
    path.lineTo(left, far);
    path.lineTo(right, far);
    path.lineTo(right, near);
    path.closePath();
    shape.holes.push(path);
    const geometry = new THREE.ExtrudeGeometry(shape, {
      depth: h, bevelEnabled: false, curveSegments: 1,
    });
    geometry.rotateX(-Math.PI / 2);
    geometry.translate(0, -h / 2, 0);
    return geometry;
  }
  if (box.border) {
    const b = box.border;
    const shape = new THREE.Shape();
    shape.moveTo(-w / 2, -h / 2);
    shape.lineTo(w / 2, -h / 2);
    shape.lineTo(w / 2, h / 2);
    shape.lineTo(-w / 2, h / 2);
    shape.closePath();
    const hole = new THREE.Path();
    hole.moveTo(-w / 2 + b, -h / 2 + b);
    hole.lineTo(-w / 2 + b, h / 2 - b);
    hole.lineTo(w / 2 - b, h / 2 - b);
    hole.lineTo(w / 2 - b, -h / 2 + b);
    hole.closePath();
    shape.holes.push(hole);
    const geometry = new THREE.ExtrudeGeometry(shape, {
      depth: d, bevelEnabled: false, curveSegments: 1,
    });
    geometry.translate(0, 0, -d / 2);
    return geometry;
  }
  if (box.frame) {
    const {innerWidth: iw, innerDepth: id} = box.frame;
    const depth = (d - id) / 2;
    const side = (w - iw) / 2;
    const pieces = [
      new THREE.BoxGeometry(w, h, depth).translate(0, 0, (id + d) / 4),
      new THREE.BoxGeometry(w, h, depth).translate(0, 0, -(id + d) / 4),
      new THREE.BoxGeometry(side, h, id).translate(-(iw + w) / 4, 0, 0),
      new THREE.BoxGeometry(side, h, id).translate((iw + w) / 4, 0, 0),
    ];
    const merged = mergeGeometries(pieces, false);
    pieces.forEach((piece) => piece.dispose());
    if (!merged) throw new Error('场地框几何合并失败');
    return merged;
  }
  if (box.holes && box.holes.length > 0) {
    const geometry = new THREE.ExtrudeGeometry(wallShape(box), {
      depth: d, bevelEnabled: false, curveSegments: 1,
    });
    geometry.translate(0, 0, -d / 2);
    return geometry;
  }
  if (box.triangular) {
    const geometry = new THREE.ExtrudeGeometry(gableShape(box), {
      depth: d, bevelEnabled: false, curveSegments: 1,
    });
    geometry.translate(0, 0, -d / 2);
    return geometry;
  }
  return new THREE.BoxGeometry(w, h, d);
}

export function createComponentObject(box: BoxSpec, materials: MaterialMap,
                                      transparent = false):
{group: THREE.Group; material: THREE.Material; edges: THREE.LineSegments} {
  const group = new THREE.Group();
  const material = (materials[box.material] as THREE.Material).clone();
  material.transparent = transparent || box.material === 'glass';
  const geometry = geometryFor(box);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = box.material !== 'glass';
  mesh.receiveShadow = true;
  group.add(mesh);
  const edgeMaterial = new THREE.LineBasicMaterial({
    color: '#26292c', transparent: true, opacity: 0.12,
  });
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), edgeMaterial);
  edges.renderOrder = 2;
  group.add(edges);
  group.position.set(...box.center);
  group.rotation.set(...box.rotation);
  return {group, material, edges};
}

/** 完工体量的幽灵轮廓：主体盒 + 坡屋顶/女儿墙，低透明度，完工镜头淡出。 */
export function createGhost(house: House): {group: THREE.Group; material: THREE.LineBasicMaterial} {
  const material = new THREE.LineBasicMaterial({
    color: '#c9c2b4', transparent: true, opacity: 0, depthWrite: false,
  });
  const group = new THREE.Group();
  const height = house.floors * house.floorHeight;
  const halfW = house.width / 2;
  const halfD = house.depth / 2;
  const body = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(house.width, height, house.depth)), material);
  body.position.y = height / 2;
  group.add(body);
  if (house.roof.type === 'gable') {
    const points: number[] = [];
    const top = height + house.roof.height;
    const zFront = halfD + house.roof.overhang;
    const zBack = -halfD - house.roof.overhang;
    const reach = halfW + house.roof.overhang;
    for (const z of [zFront, zBack]) {
      points.push(-reach, height, z, 0, top, z);
      points.push(0, top, z, reach, height, z);
    }
    points.push(-reach, height, zFront, -reach, height, zBack);
    points.push(0, top, zFront, 0, top, zBack);
    points.push(reach, height, zFront, reach, height, zBack);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    group.add(new THREE.LineSegments(geometry, material));
  } else {
    const top = height + house.roof.height;
    const reachX = halfW + house.roof.overhang;
    const reachZ = halfD + house.roof.overhang;
    const points: number[] = [];
    for (const y of [height, top]) {
      points.push(-reachX, y, -reachZ, reachX, y, -reachZ);
      points.push(reachX, y, -reachZ, reachX, y, reachZ);
      points.push(reachX, y, reachZ, -reachX, y, reachZ);
      points.push(-reachX, y, reachZ, -reachX, y, -reachZ);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    group.add(new THREE.LineSegments(geometry, material));
  }
  return {group, material};
}

export function contactShadowTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const context = canvas.getContext('2d');
  if (context) {
    const gradient = context.createRadialGradient(256, 256, 24, 256, 256, 250);
    gradient.addColorStop(0, 'rgba(0, 0, 0, 0.55)');
    gradient.addColorStop(0.55, 'rgba(0, 0, 0, 0.28)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 512, 512);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

export function sideLabel(side: WallSide): string {
  return {front: '前', back: '后', left: '左', right: '右'}[side];
}
