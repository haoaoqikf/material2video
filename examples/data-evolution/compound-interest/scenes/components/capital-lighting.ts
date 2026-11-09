import * as THREE from 'three';

/** 摄影棚反光板进入真实PMREM，让曲面反射宽柔光；不是直接贴在圆面上的高光图。 */
export function createStudioEnvironment(renderer: THREE.WebGLRenderer) {
  const studio = new THREE.Scene();
  studio.background = new THREE.Color(.025, .03, .04);
  const resources: {geometry: THREE.PlaneGeometry; material: THREE.MeshBasicMaterial}[] = [];
  const panel = (width: number, height: number, at: [number, number, number], color: THREE.Color) => {
    const geometry = new THREE.PlaneGeometry(width, height);
    const material = new THREE.MeshBasicMaterial({color, side: THREE.DoubleSide, toneMapped: false});
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...at);
    mesh.lookAt(0, 0, 0);
    studio.add(mesh);
    resources.push({geometry, material});
  };
  panel(1.8, 5, [0, 4, -6], new THREE.Color(10, 9.4, 8.5));
  panel(6, 2, [-5, 4, 4], new THREE.Color(1.4, 1.6, 2));
  panel(1, 6, [4, 1, 2], new THREE.Color(3, 3.1, 3.2));
  const generator = new THREE.PMREMGenerator(renderer);
  const target = generator.fromScene(studio, .04);
  return {
    texture: target.texture,
    dispose() {
      target.dispose(); generator.dispose();
      resources.forEach(({geometry, material}) => {geometry.dispose(); material.dispose();});
    },
  };
}
