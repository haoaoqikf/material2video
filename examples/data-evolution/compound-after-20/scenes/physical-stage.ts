import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {macroGlance, type Block, type Glass} from './compound-model';

function environmentMap(renderer: THREE.WebGLRenderer) {
  const room = new THREE.Scene();
  room.background = new THREE.Color('#1a2837');
  const panels = [
    {width: 5.4, height: 2.2, xyz: [-4, 5, 6], rgb: [4.2, 3.7, 3.2]},
    {width: 2.8, height: 7, xyz: [6, 2, -2], rgb: [1.6, 2.35, 4.3]},
    {width: 4.2, height: 2.2, xyz: [-3.1, 2.3, -6.4], rgb: [2.72, 1.46, .66]},
    {width: .38, height: 6, xyz: [3.8, 3.4, 5.6], rgb: [4.4, 4.7, 5.4]},
    {width: 2.8, height: 4.4, xyz: [-4.2, -1.45, 7.3], rgb: [2.83, 1.59, .72]},
    {width: 1.4, height: 3.4, xyz: [3.5, -2.25, -6.8], rgb: [1.9, 2.8, 4.1]},
    {width: .42, height: 2.9, xyz: [-4.5, -1.75, 6.5], rgb: [8.0, 5.9, 3.1]},
    {width: .58, height: 1.95, xyz: [-4.8, 2.6, -6.4], rgb: [4.8, 4.62, 4.1]},
    {width: 3.5, height: .3, xyz: [-1, -.8, 5.4], rgb: [1.05, .81, .57]},
  ];
  for (const panel of panels) {
    const geometry = new THREE.PlaneGeometry(panel.width, panel.height);
    const fill = new THREE.Color().setRGB(panel.rgb[0], panel.rgb[1], panel.rgb[2]);
    const material = new THREE.ShaderMaterial({
      side: THREE.DoubleSide, uniforms: {radiance: {value: fill}},
      vertexShader: `
        varying vec2 localUV;
        void main() {
          localUV = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
        }
      `,
      fragmentShader: `
        uniform vec3 radiance;
        varying vec2 localUV;
        void main() {
          vec2 area = (localUV - vec2(.49,.55)) * vec2(1.86,1.55);
          float shape = .16 + .94 * exp(-2.4 * dot(area,area));
          gl_FragColor = vec4(radiance * shape, 1.);
        }
      `,
    });
    const light = new THREE.Mesh(geometry, material);
    light.position.set(panel.xyz[0], panel.xyz[1], panel.xyz[2]);
    light.lookAt(0, 0, 0);
    room.add(light);
  }
  const generator = new THREE.PMREMGenerator(renderer);
  const target = generator.fromScene(room, .036);
  generator.dispose();
  for (const element of room.children as THREE.Mesh<THREE.PlaneGeometry, THREE.Material>[]) {
    element.geometry.dispose();
    element.material.dispose();
  }
  return target;
}

function makeBackdrop() {
  const image = document.createElement('canvas');
  image.width = 960;
  image.height = 540;
  const painting = image.getContext('2d', {alpha: false});
  if (!painting) throw new Error('暗场纹理无法初始化');
  const context = painting;
  context.scale(.5, .5);
  const texture = new THREE.CanvasTexture(image);
  texture.colorSpace = THREE.SRGBColorSpace;

  function ellipse(x: number, y: number, radiusX: number, radiusY: number, stops: [number, string][]) {
    context.save();
    context.translate(x, y);
    context.scale(radiusX, radiusY);
    const falloff = context.createRadialGradient(0, 0, 0, 0, 0, 1);
    stops.forEach(([offset, color]) => falloff.addColorStop(offset, color));
    context.fillStyle = falloff;
    context.fillRect(-1, -1, 2, 2);
    context.restore();
  }

  function caustic(support: Block, floor: number, strength: number) {
    const halfWidth = support.width / 2;
    const beam = context.createLinearGradient(support.x - halfWidth, floor, support.x + halfWidth * 1.7, floor + 24);
    beam.addColorStop(0, '#ffcc8900');
    beam.addColorStop(.3, '#ffbd7274');
    beam.addColorStop(.59, '#ffe1a791');
    beam.addColorStop(.84, '#c87d4334');
    beam.addColorStop(1, '#ffcc8900');
    context.save();
    context.strokeStyle = beam;
    context.globalAlpha *= strength;
    for (let ray = 0; ray < 6; ray++) {
      const spread = ray / 5;
      const focusX = support.x + support.depth * (.20 + .15 * spread);
      const focusY = floor + 3 + spread ** 1.46 * 15;
      context.lineWidth = 2.3 - spread;
      context.beginPath();
      context.moveTo(support.x - halfWidth * (1.08 + spread * .24), floor + 5 + spread * 9);
      context.quadraticCurveTo(focusX - halfWidth * .55, focusY - 9, focusX, focusY);
      context.quadraticCurveTo(focusX + halfWidth * .79, focusY + 7, focusX + halfWidth * (1.12 + spread * .28), floor + 15 + spread * 8);
      context.stroke();
    }
    context.restore();
  }

  function reflectedWave(support: Block, floor: number, strength: number) {
    const focusX = support.x + support.depth * .56;
    const radiusX = support.width * .88;
    const color = context.createLinearGradient(focusX - radiusX, 0, focusX + radiusX, 0);
    color.addColorStop(0, '#ac632800');
    color.addColorStop(.24, '#f6ab5c30');
    color.addColorStop(.51, '#ffdba595');
    color.addColorStop(.68, '#ffe9c59b');
    color.addColorStop(1, '#ffb85c00');
    context.save();
    context.globalAlpha *= strength;
    context.strokeStyle = color;
    const apertures = [0, .14, .32, .52, .79, 1];
    for (const aperture of apertures) {
      context.lineWidth = 2.8 - aperture * 1.4;
      context.beginPath();
      context.moveTo(focusX - radiusX, floor + 9 + aperture * 11);
      context.bezierCurveTo(
        focusX - radiusX * .46, floor + 11 + aperture * 36,
        focusX - radiusX * .14, floor + 48 + aperture * 19,
        focusX + radiusX * .25, floor + 20 + aperture * 25,
      );
      context.quadraticCurveTo(focusX + radiusX * .44, floor + 4 + aperture * 13, focusX + radiusX, floor + 6);
      context.stroke();
    }
    context.restore();
  }

  function opticalField(isMacro: boolean, center: number, floor: number, strength: number) {
    const left = isMacro ? center - 351 : 530;
    const right = isMacro ? center + 480 : 1820;
    const baseY = isMacro ? 560 : floor - 43;
    const color = context.createLinearGradient(left, 0, right, 0);
    color.addColorStop(0, '#8cabc000');
    color.addColorStop(.26, '#a1c9ee24');
    color.addColorStop(.49, '#eef7ff95');
    color.addColorStop(.64, '#99c8f366');
    color.addColorStop(.81, '#a7cae123');
    color.addColorStop(1, '#a6c9e800');
    context.save();
    context.globalAlpha = strength * (isMacro ? .29 : .34);
    context.strokeStyle = color;
    for (const [offset, width] of [[0, 3.1], [8, 1.35], [22, 1.7], [40, .9], [56, 1.8]]) {
      context.lineWidth = width;
      context.beginPath();
      context.moveTo(left, baseY + 36 + offset);
      context.bezierCurveTo(
        left + (right - left) * .47, baseY + 51 + offset * .52,
        left + (right - left) * .47, baseY - (isMacro ? 151 : 199) + offset,
        right, baseY - (isMacro ? 152 : 198) + offset * 1.35,
      );
      context.stroke();
    }
    context.restore();
  }

  return {
    texture,
    update(blocks: Block[], floor: number, landed: number, isMacro: boolean, graphFill: number) {
      const origin = isMacro ? blocks[0].x + 53 : 1460;
      const base = context.createLinearGradient(200, 200, 1730, 1070);
      base.addColorStop(0, '#070d17');
      base.addColorStop(.67, '#0d1927');
      base.addColorStop(1, '#060b13');
      context.fillStyle = base;
      context.fillRect(0, 0, 1920, 1080);
      ellipse(origin + 35, floor - 300, 740, 650,
        [[0, '#38526c'], [.41, '#25384bb5'], [1, '#172c4500']]);
      ellipse(origin + 70, floor - 205, 410, 430,
        [[0, '#3d526677'], [.63, '#26384f30'], [1, '#19284200']]);
      ellipse(origin + 100, floor - 450, 138, 535,
        [[0, '#8eabc54f'], [.23, '#5175983c'], [1, '#26476500']]);
      if (graphFill > .001) {
        context.globalAlpha = graphFill;
        ellipse(815, floor - 14, 895, 135,
          [[0, '#4b5c723c'], [.54, '#33455a27'], [1, '#18212a00']]);
        context.globalAlpha = 1;
      }
      if (isMacro || graphFill > .001) opticalField(isMacro, blocks[0].x, floor, isMacro ? 1 : graphFill);
      const plinths = isMacro ? [blocks[0]] : [blocks[0], blocks[20]];
      let coupling = landed;
      if (isMacro) {
        const interestIndex = blocks.findIndex(block => block.glass !== 'ink');
        const capital = blocks[interestIndex - 1];
        const interest = blocks[interestIndex];
        const gap = capital.y - capital.height / 2 - interest.y - interest.height / 2;
        coupling = Math.max(0, 1 - gap / 146);
      }
      context.globalAlpha = isMacro ? .93 : landed;
      for (const base of plinths) {
        ellipse(base.x + base.depth * .24, floor + 12, base.width * .88, 25,
          [[0, '#ca8b4c97'], [.38, '#91603655'], [1, '#27223100']]);
        ellipse(base.x + base.depth * .25, floor + 3, base.width * .63, 10,
          [[0, '#05070bdd'], [.65, '#05070b9b'], [1, '#04070a00']]);
        reflectedWave(base, floor, coupling * (isMacro ? .57 : base === blocks[20] ? .62 : .26));
        if (!isMacro) caustic(base, floor, base === blocks[20] ? .97 : .61);
      }
      context.globalAlpha = 1;
      texture.needsUpdate = true;
    },
  };
}

type Optics = Record<'opticalRise' | 'graphFill' | 'opticalContrast' | 'stripCenter' | 'split', {value: number}>;

function material(
  tone: number, attenuation: number, distance: number, transmission: number, surfaceCurve: number,
  optics: Optics, layerContrast: number, etching = 0,
) {
  const glass = new THREE.MeshPhysicalMaterial({
    color: tone, attenuationColor: attenuation, attenuationDistance: distance, transmission,
    roughness: .20, ior: 1.46, thickness: .45, metalness: 0,
    clearcoat: .58, clearcoatRoughness: .18, envMapIntensity: .86,
  });
  if (transmission > .5) {
    glass.transparent = true;
    glass.opacity = .53;
    glass.depthWrite = false;
    glass.side = THREE.DoubleSide;
    glass.iridescence = .15;
    glass.iridescenceIOR = 1.35;
    glass.dispersion = .075;
  } else {
    glass.color.set('#244865');
    glass.transmission = .25;
    glass.metalness = .38;
    glass.roughness = .27;
    glass.clearcoat = .55;
    glass.specularIntensity = .62;
    glass.specularColor.set('#b4d4ee');
    glass.envMapIntensity = .79;
  }
  glass.onBeforeCompile = shader => {
    shader.uniforms.surfaceCurve = {value: surfaceCurve};
    Object.assign(shader.uniforms, optics);
    shader.uniforms.layerContrast = {value: layerContrast};
    shader.uniforms.etching = {value: etching};
    shader.vertexShader = 'varying vec3 glassPoint; varying vec3 glassFace;\n' + shader.vertexShader.replace(
      '#include <begin_vertex>',
      '#include <begin_vertex>\nglassPoint = (modelMatrix * vec4(position, 1.)).xyz; glassFace = position;',
    );
    const ray = 'normalize(vec3(.56, opticalRise, 1.))';
    shader.fragmentShader = 'varying vec3 glassPoint; varying vec3 glassFace; uniform float surfaceCurve; uniform float opticalRise; uniform float graphFill; uniform float opticalContrast; uniform float stripCenter; uniform float split; uniform float layerContrast; uniform float etching;\n' + shader.fragmentShader.replace(
      '#include <normal_fragment_begin>',
      `#include <normal_fragment_begin>
      // Small optical variations follow the world position, so a studio highlight is not copied onto each layer.
      float broadTurn = sin(glassPoint.x * .009 - glassPoint.y * .010 + glassPoint.z * .007);
      float fineTurn = sin(glassPoint.y * .019 + glassPoint.x * .008);
      vec2 shape = vec2(broadTurn * .63 + glassFace.x * .30, fineTurn * .35 + glassFace.y * .14);
      normal = normalize(normal + vec3(shape * surfaceCurve, 0.));`,
    ).replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
      float cap = smoothstep(.30, .495, glassFace.y);
      float ridgeX = (glassFace.x + .24 + .028 * sin(glassPoint.y * .021)) / .081;
      float ridge = exp(-ridgeX * ridgeX);
      float coolEdgeX = (glassFace.x - .38) / .065;
      float coolEdge = exp(-coolEdgeX * coolEdgeX);
      totalEmissiveRadiance += vec3(.055, .019, .006) * graphFill * (.55 + cap * 1.26 + ridge * .61);
      totalEmissiveRadiance += vec3(.029, .055, .099) * graphFill * coolEdge;`,
    ).replace(
      '#include <lights_fragment_begin>',
      THREE.ShaderChunk.lights_fragment_begin.replace('vec3( 0, 0, 1 )', ray),
    ).replace(
      '#include <transmission_fragment>',
      THREE.ShaderChunk.transmission_fragment.replace('normalize( cameraPosition - pos )', ray),
    ).replace(
      '#include <opaque_fragment>',
      `#include <opaque_fragment>
      #ifdef USE_IRIDESCENCE
        vec3 facets = abs(glassFace);
        float bevel = max(min(facets.x, facets.y), max(min(facets.x, facets.z), min(facets.y, facets.z)));
        float rim = smoothstep(.36, .486, bevel);
        float glassClear = opticalContrast * (1. - .86 * rim);
        gl_FragColor.a *= 1. - .64 * glassClear;
        float stripeOffset = glassPoint.x - glassPoint.z * .50 + glassPoint.y * .19;
        float broadBand = (stripeOffset - stripCenter) / 26.;
        float narrowBand = (stripeOffset - stripCenter - 27.) / 5.8;
        float reflectedBand = (stripeOffset - stripCenter - 269.) / 33.;
        float stripA = exp(-broadBand * broadBand);
        float stripB = exp(-narrowBand * narrowBand);
        float stripC = exp(-reflectedBand * reflectedBand);
        float warmRim = rim * (.13 + .52 * stripA + .42 * stripB + .28 * stripC * graphFill);
        float cleanWhite = (stripA * .53 + stripB * .47) * (1. - .68 * graphFill);
        float reflectedWhite = rim * stripC * graphFill * .41;
        gl_FragColor.a += opticalContrast * rim * (.12 * stripB + .10 * stripC);
        gl_FragColor.rgb += opticalContrast * (warmRim * vec3(1.0, .60, .27) + (cleanWhite + reflectedWhite) * vec3(.69, .81, 1.));
        if (!gl_FrontFacing) gl_FragColor.a *= 1. - split * .78;
        float layerTop = smoothstep(.29, .485, glassFace.y);
        float layerBottom = smoothstep(.27, .49, -glassFace.y);
        gl_FragColor.rgb = gl_FragColor.rgb * (1. - layerContrast * (1. - graphFill) * layerBottom * .52)
          + layerTop * layerContrast * (1. - graphFill) * vec3(.12, .102, .062);
        // Group separators are differences in the finish of existing layers, so their geometry is unchanged.
        gl_FragColor.rgb *= 1. - etching * (1. - graphFill) * (.45 + .38 * layerTop);
        float macroLight = opticalContrast * (1. - graphFill);
        gl_FragColor.rgb = gl_FragColor.rgb * mix(vec3(1.), vec3(1.16, .83, .53), macroLight)
          + vec3(.34, .145, .032) * rim * macroLight;
      #else
        float stone = dot(gl_FragColor.rgb, vec3(.20, .63, .17));
        vec3 blue = vec3(.025, .065, .113) + stone * vec3(.28, .56, .91);
        gl_FragColor.rgb = mix(gl_FragColor.rgb, blue, .84 * opticalContrast);
      #endif`,
    );
  };
  return glass;
}

function makeMirror(color: number) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: {
      color: {value: new THREE.Color(color)},
      floor: {value: 0},
      glancing: {value: 0},
      amount: {value: 0},
    },
    vertexShader: `
      varying vec3 spot;
      varying vec3 direction;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.);
        spot = world.xyz;
        direction = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: `
      uniform vec3 color;
      uniform float floor;
      uniform float glancing;
      uniform float amount;
      varying vec3 spot;
      varying vec3 direction;
      void main() {
        float drop = floor - (spot.y - spot.z * glancing);
        if (drop < 1. || drop > 80.) discard;
        float tone = .28 + abs(normalize(direction).z) * .22;
        gl_FragColor = vec4(color * tone, amount * (1. - smoothstep(3., 80., drop)));
        #include <colorspace_fragment>
      }
    `,
  });
}

export function makePhysicalStage(canvas: HTMLCanvasElement, width: number, height: number, density: number, capacity: number) {
  const renderer = new THREE.WebGLRenderer({canvas, alpha: false, antialias: true});
  renderer.setPixelRatio(density);
  renderer.setSize(width, height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.04;
  renderer.transmissionResolutionScale = .65;

  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(0, 1920, 1080, 0, 1, 3500);
  const distance = 1200;
  camera.position.z = distance;
  const projection = camera.projectionMatrix.elements;
  projection[8] = -.56 * projection[0];
  projection[12] = -1 + projection[8] * distance;

  const environment = environmentMap(renderer);
  scene.environment = environment.texture;
  const backdrop = makeBackdrop();
  scene.background = backdrop.texture;
  const fill = new THREE.HemisphereLight(0xcde0fa, 0x342536, .42);
  scene.add(fill);
  const warm = new THREE.PointLight(0xffcd94, 81_000, 1500, 2);
  const reflectedFill = new THREE.PointLight(0x9cbded, 250_000, 2100, 2);
  reflectedFill.position.set(1290, 600, 430);
  const warmFloor = new THREE.PointLight(0xffd5a9, 117_000, 1250, 2);
  warmFloor.position.set(1570, 280, 310);
  scene.add(warm, reflectedFill, warmFloor);

  // Orthographic depth shears the projected faces. Reflections and refractions follow the same rays.
  const optics = {
    opticalRise: {value: 0}, graphFill: {value: 0}, opticalContrast: {value: 0},
    stripCenter: {value: 0}, split: {value: 0},
  };
  const {opticalRise, graphFill, opticalContrast, stripCenter, split} = optics;
  const surfaces: Record<Glass, THREE.MeshPhysicalMaterial> = {
    ink: material(0x416684, 0x6296b5, 310, .47, .037, optics, 0),
    amber: material(0xf5b368, 0xe7a94e, 290, .82, .21, optics, .11),
    honey: material(0xffc579, 0xedac54, 335, .81, .20, optics, .86),
    glint: material(0xffd287, 0xffba69, 350, .79, .22, optics, .09),
    etched: material(0xfac175, 0xebac54, 320, .81, .20, optics, .22, .5),
  };
  const mirrorSurfaces: Record<Glass, THREE.ShaderMaterial> = {
    ink: makeMirror(0x647e9c), amber: makeMirror(0xdc9e60), honey: makeMirror(0xeab171), glint: makeMirror(0xf4bc71),
    etched: makeMirror(0xcd965b),
  };
  const box = new RoundedBoxGeometry(1, 1, 1, 3, .092);
  const shapes = Array.from({length: capacity}, () => {
    const face = new THREE.Mesh(box, surfaces.amber);
    const mirror = new THREE.Mesh(box, mirrorSurfaces.amber);
    scene.add(face, mirror);
    return {face, mirror};
  });

  return {
    draw(blocks: Block[], {sweep, floor, reflection, landed, glancing, isMacro}: {
      sweep: number; floor: number; reflection: number; landed: number; glancing: number; isMacro: boolean;
    }) {
      opticalRise.value = glancing;
      graphFill.value = isMacro ? 0 : Math.max(0, 1 - glancing / macroGlance);
      opticalContrast.value = isMacro ? 1 : graphFill.value * .86;
      stripCenter.value = isMacro ? 1090 + (sweep - 1040) * .139 : 1354;
      split.value = isMacro ? .30 : Math.sin(Math.PI * graphFill.value) * (1 - landed);
      backdrop.update(blocks, floor, landed, isMacro, graphFill.value);
      for (const tint of ['amber', 'honey', 'glint', 'etched'] as const) {
        surfaces[tint].roughness = .155 - .062 * opticalContrast.value + .075 * graphFill.value;
      }
      reflectedFill.intensity = 250_000 - graphFill.value * 164_000;
      warmFloor.intensity = 117_000 - graphFill.value * 73_000;
      projection[9] = -projection[5] * glancing;
      projection[13] = -1 + projection[9] * distance;
      camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
      warm.position.set(sweep - 173, 644, 170);
      for (const surface of Object.values(mirrorSurfaces)) {
        surface.uniforms.floor.value = 1080 - floor;
        surface.uniforms.glancing.value = glancing;
        surface.uniforms.amount.value = reflection * .74;
      }
      shapes.forEach(({face, mirror}, index) => {
        const block = blocks[index];
        face.visible = !!block && block.height > .06;
        mirror.visible = face.visible && reflection > .001 && block.y + block.height / 2 > floor - 108;
        if (!face.visible) return;
        const seam = Math.min(.42 + .26 * landed, block.height * (.08 + .08 * landed));
        face.material = surfaces[block.glass];
        face.scale.set(block.width, block.height - seam, block.depth);
        face.position.set(block.x, 1080 - block.y, (block.z ?? 0) - block.depth / 2);
        face.renderOrder = index;
        if (mirror.visible) {
          mirror.material = mirrorSurfaces[block.glass];
          mirror.scale.set(face.scale.x, -face.scale.y, face.scale.z);
          mirror.position.set(face.position.x, 1080 - 2 * floor + block.y, face.position.z);
          mirror.renderOrder = index - capacity;
        }
      });
      renderer.render(scene, camera);
    },
    dispose() {
      box.dispose();
      environment.dispose();
      backdrop.texture.dispose();
      Object.values(surfaces).forEach(surface => surface.dispose());
      Object.values(mirrorSurfaces).forEach(surface => surface.dispose());
      renderer.dispose();
    },
  };
}
