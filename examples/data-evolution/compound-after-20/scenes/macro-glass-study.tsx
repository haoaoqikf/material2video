import {useLayoutEffect, useRef} from 'react';
import {useSceneContext} from '../src/code-scene/context';
import type {macroState} from './compound-model';

export type MacroGlassLook = 'clear' | 'prism' | 'lens';
type Macro = ReturnType<typeof macroState>;

const vertex = `#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2. - 1., 0., 1.);
}
`;

const optics = `#version 300 es
precision highp float;
out vec4 color;
uniform vec2 resolution;
uniform vec4 bodies[13];  // 中心与材质种类，0 表示空，1 表示本金。
uniform vec4 extents[13]; // 三轴半尺寸和沿 X 轴的入射角。
uniform float reveal;
uniform int prism;
uniform int lens;
uniform int firstGainIndex;

const float far = 90.;
const float epsilon = .0015;

vec3 roll(vec3 p, float a) {
  float c = cos(a), s = sin(a);
  return vec3(p.x, c * p.y - s * p.z, s * p.y + c * p.z);
}

float roundBox(vec3 p, vec3 size, float radius) {
  vec3 q = abs(p) - size + radius;
  return length(max(q, 0.)) + min(max(q.x, max(q.y, q.z)), 0.) - radius;
}

float boundary(vec3 p, int body) {
  vec3 size = extents[body].xyz;
  float glass = step(1.5, bodies[body].w);
  float r = min(size.y * .70, mix(.024, lens == 1 ? .035 : .066, glass));
  if (prism == 1 && glass > .5) {
    // 圆角外廓和微拱片面分开定形，保留平的落位底面。
    bool hero = lens == 1 && bodies[body].w > 2.5;
    float corner = min(.24, (lens == 1 ? .29 : .38) * size.z);
    vec2 footprint = abs(p.xz) - size.xz + corner;
    float side = length(max(footprint, 0.)) + min(max(footprint.x, footprint.y), 0.) - corner;
    vec2 uv = clamp(p.xz / size.xz, -1., 1.);
    float firstCurvature = body == firstGainIndex ? .090 * (1. - reveal) : 0.;
    float dome = (lens == 1 ? (hero ? .037 : .022 + firstCurvature) : .055)
      * (1. - uv.x * uv.x) * (1. - uv.y * uv.y);
    vec2 q = vec2(side, max(p.y - size.y - dome, -p.y - size.y)) + r;
    return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r;
  }
  return roundBox(p, size, r);
}

vec3 normalAt(vec3 localPoint, int object) {
  vec2 h = vec2(epsilon, 0.);
  return normalize(vec3(
    boundary(localPoint + h.xyy, object) - boundary(localPoint - h.xyy, object),
    boundary(localPoint + h.yxy, object) - boundary(localPoint - h.yxy, object),
    boundary(localPoint + h.yyx, object) - boundary(localPoint - h.yyx, object)
  ));
}

vec2 slabRange(vec3 ray, vec3 origin, vec3 size) {
  vec3 inverse = mix(vec3(-1.), vec3(1.), step(0., ray)) / max(abs(ray), .00001);
  vec3 a = (-size - origin) * inverse, b = (size - origin) * inverse;
  vec3 nearAxis = min(a, b), farAxis = max(a, b);
  return vec2(max(nearAxis.x, max(nearAxis.y, nearAxis.z)),
    min(farAxis.x, min(farAxis.y, farAxis.z)));
}

struct Hit { float distance; int body; vec3 normal; };

Hit trace(vec3 origin, vec3 ray, int skip) {
  Hit hit = Hit(far, -1, vec3(0.));
  for (int index = 0; index < 13; index++) {
    if (bodies[index].w < .5 || index == skip) continue;
    float angle = extents[index].w;
    vec3 localOrigin = roll(origin - bodies[index].xyz, -angle), localRay = roll(ray, -angle);
    vec3 bounds = extents[index].xyz;
    if (prism == 1 && bodies[index].w > 1.5) {
      bounds.y += lens == 1 ? .038 + (index == firstGainIndex ? .090 * (1. - reveal) : 0.) : .056;
    }
    vec2 range = slabRange(localRay, localOrigin, bounds);
    if (range.x > range.y || range.y < epsilon || range.x >= hit.distance) continue;
    float s = max(0., range.x);
    for (int pass = 0; pass < 16; pass++) {
      vec3 p = localOrigin + localRay * s;
      float stepSize = boundary(p, index);
      if (stepSize < epsilon) {
        hit = Hit(s, index, roll(normalAt(p, index), angle));
        break;
      }
      s += stepSize;
      if (s > min(range.y, hit.distance)) break;
    }
  }
  return hit;
}

vec3 environment(vec3 origin, vec3 ray) {
  float atWall = ray.z < -.001 ? (-5.6 - origin.z) / ray.z : far;
  float atFloor = ray.y < -.001 ? -origin.y / ray.y : far;
  if (atFloor < atWall && atFloor > 0.) {
    vec3 p = origin + ray * atFloor;
    float contact = exp(-dot((p.xz - vec2(.2, -.9)) / vec2(2.9, 1.2), (p.xz - vec2(.2, -.9)) / vec2(2.9, 1.2)));
    float lighting = exp(-length((p.xz - vec2(1., -1.)) / vec2(4.6, 4.7)) * 1.7);
    vec2 shaft = (p.xz - vec2(.36 + .35 * reveal, -.70)) / vec2(3.0, 1.8);
    float envelope = exp(-dot(shaft, shaft) * 1.65);
    float caustic = exp(-abs(sin(p.z * 8.6 - p.x * 2.7 + .87 * sin(p.x * 1.27))) * 4.8);
    float warmPool = exp(-length((p.xz - vec2(1.9, .4)) / vec2(2.3, 2.1)) * 1.7);
    return (vec3(.002, .006, .019) + vec3(.020, .047, .110) * lighting)
      * (1. - .87 * contact) + vec3(.34, .143, .042) * (caustic * envelope + .10 * warmPool) * (1. - .88 * contact);
  }
  if (atWall > 0. && atWall < far) {
    vec2 p = (origin + atWall * ray).xy;
    vec2 field = (p - vec2(-1.44, 2.51)) / vec2(3.38, 2.64);
    float broad = exp(-dot(field, field) * 1.31);
    float direction = p.x + .57 * p.y + .16 * sin(p.y * 2.);
    float vertical = (p.y - 2.9) * .70;
    float glasshouse = (smoothstep(-2.0, -1.86, direction) - smoothstep(-1.52, -1.40, direction))
      * exp(-vertical * vertical * 1.8);
    float darkSlot = smoothstep(-.74, -.65, direction) - smoothstep(-.52, -.43, direction);
    vec3 blue = vec3(.038, .105, .232) * broad * (1. - .44 * darkSlot);
    float key = prism == 1 ? .50 : .66;
    vec3 fieldLight = vec3(.20, .31, .48) * glasshouse * key;
    if (lens == 1) {
      // 背景灯槽和其暗缝也参与透射，给悬片内部留下可辨认的折弯结构。
      vec2 focusField = (p - vec2(-2.44, 2.70)) / vec2(.98, .68);
      float falloff = exp(-dot(focusField, focusField) * .96);
      float slot = p.x - .66 * (p.y - 2.64);
      float aperture = smoothstep(-2.75, -2.66, slot) - smoothstep(-2.43, -2.36, slot);
      float secondEdge = smoothstep(-2.31, -2.23, slot) - smoothstep(-2.15, -2.07, slot);
      vec3 fixture = vec3(.036, .095, .16) + vec3(.29, .42, .57) * (aperture + .44 * secondEdge);
      fieldLight = mix(fieldLight, fixture * falloff, reveal * .92);
    }
    return vec3(.0015, .005, .018) + blue + fieldLight;
  }
  return vec3(.009, .022, .043) + vec3(.025, .053, .083) * clamp(ray.y, 0., 1.);
}

vec3 room(vec3 origin, vec3 ray) {
  vec3 background = environment(origin, ray);
  if (lens == 0 || ray.z >= -.001) return background;
  // 两个悬片后方的同一块棚面随揭示移焦。亮面和暗隔从体外连续进入折射路径。
  float atAperture = (-2.02 - origin.z) / ray.z;
  if (atAperture <= 0.) return background;
  vec2 center = mix(vec2(-.49, 3.07), vec2(-.62, 3.50), reveal);
  vec2 uv = ((origin + atAperture * ray).xy - center) / mix(vec2(1.83, .60), vec2(1.09, .59), reveal);
  float footprint = exp(-dot(uv, uv) * 1.75);
  float across = uv.y + .41 * uv.x - .20 * uv.x * uv.x;
  float pane = smoothstep(-.48, -.42, across) - smoothstep(.07, .15, across);
  float secondPane = smoothstep(.24, .28, across) - smoothstep(.34, .44, across);
  vec2 lowerPanel = ((origin + atAperture * ray).xy - vec2(-.38, 2.17)) / vec2(2.6, .50);
  float lowerBand = lowerPanel.y + lowerPanel.x * .18;
  float fill = exp(-dot(lowerPanel, lowerPanel) * 1.6)
    * (1. - .47 * exp(-68. * lowerBand * lowerBand));
  vec3 first = bodies[firstGainIndex].xyz;
  vec2 sweep = ((origin + atAperture * ray).xy - vec2(first.x - .42, first.y - .36)) / vec2(2.12, .49);
  float curvedBand = sweep.y + .46 * sweep.x - .36 * sweep.x * sweep.x;
  float sweepFocus = exp(-sweep.x * sweep.x * 1.08) * smoothstep(.18, 1., first.y - 2.1) * (1. - reveal);
  // 宽片把棚灯的亮窗与暗隔折弯。直接视线也能看见同一组边界的延长段。
  float slit = smoothstep(-.72, -.63, curvedBand) - smoothstep(-.19, -.12, curvedBand);
  float fringe = smoothstep(.015, .065, curvedBand) - smoothstep(.15, .24, curvedBand);
  vec3 firstLight = vec3(.36, .51, .64) * slit
    + vec3(.49, .43, .31) * fringe + vec3(.044, .075, .103) * exp(-2.4 * curvedBand * curvedBand);
  return background + (vec3(.26, .42, .43) * pane + vec3(.44, .40, .28) * secondPane)
    * footprint * mix(.56, .91, reveal) + vec3(.125, .150, .163) * fill * reveal
    + firstLight * sweepFocus;
}

vec3 substrate(vec3 point, vec3 ray, vec3 normal) {
  vec3 key = normalize(vec3(-1., 4., 2.));
  float light = max(0., dot(normal, key));
  float edge = pow(1. - abs(dot(normal, ray)), 4.);
  float rim = max(0., dot(normal, normalize(vec3(4., 1., -2.))));
  float gradient = .54 + .46 * smoothstep(-2., 2.5, point.x);
  float faceLift = exp(-dot((point.xz - vec2(1.8, -.40)) / vec2(1.7, 2.8),
    (point.xz - vec2(1.8, -.40)) / vec2(1.7, 2.8)));
  vec3 received = vec3(.008, .022, .079) * (.65 + .84 * light) * gradient
    + vec3(.023, .069, .172) * (edge * .58 + rim * .52 + faceLift * (.23 + .49 * abs(normal.y)));
  if (lens == 1) {
    // 首年窄灯打在本金顶面，收益片沿实际透射路径取到同一受光面。
    float diagonal = point.z + .38 * point.x + .62;
    float band = exp(-9. * diagonal * diagonal - .23 * point.x * point.x);
    received += vec3(.10, .20, .31) * band * max(0., normal.y) * (1. - .58 * reveal);
    if (1. - reveal > .001) {
      float height = bodies[firstGainIndex].y - 2.1;
      float ribbon = diagonal - .21 - .10 * point.x * point.x;
      float caustic = exp(-60. * ribbon * ribbon - .53 * (point.x - .25) * (point.x - .25));
      received += vec3(.18, .103, .039) * caustic * smoothstep(.18, 1., height) * max(0., normal.y) * (1. - reveal);
    }
  }
  return received;
}

vec3 transmittedScene(vec3 point, vec3 ray, int glass) {
  Hit next = trace(point, ray, glass);
  if (next.body < 0) return room(point, ray);
  vec3 p = point + ray * next.distance;
  if (bodies[next.body].w < 1.5) return substrate(p, ray, next.normal);
  // 两层贴合时需保留穿过下一层的棚色，叠层吸收比单片更深。
  float side = 1. - abs(next.normal.y);
  if (lens == 1) {
    return room(p, ray) * vec3(.70, .55, .38) + vec3(.031, .015, .005) * side;
  }
  return room(p, ray) * vec3(.56, .38, .19)
    + vec3(.103, .039, .012) * (.64 + .34 * side);
}

float reachInterface(vec3 localStart, vec3 localRay, int body, out vec3 exitPoint) {
  float distance = .003;
  for (int stepIndex = 0; stepIndex < 29; stepIndex++) {
    exitPoint = localStart + localRay * distance;
    float s = boundary(exitPoint, body);
    if (abs(s) < epsilon && stepIndex >= 2) break;
    distance += max(.002, -s);
  }
  return distance;
}

vec3 throughGlass(vec3 point, vec3 ray, Hit hit) {
  int body = hit.body;
  bool hero = lens == 1 && bodies[body].w > 2.5;
  const float ior = 1.49;
  float angle = extents[body].w;
  vec3 inside = refract(ray, hit.normal, 1. / ior);
  vec3 start = point - hit.normal * .006;
  vec3 localStart = roll(start - bodies[body].xyz, -angle);
  vec3 exitPoint;
  float distance = reachInterface(localStart, roll(inside, -angle), body, exitPoint);
  vec3 exitNormal = roll(normalAt(exitPoint, body), angle);
  vec3 leaving = refract(inside, -exitNormal, ior);
  if (lens == 1 && dot(leaving, leaving) < .1) {
    // 全内反射仍在片内走，直到遇到第二个截面再尝试出射。
    inside = reflect(inside, exitNormal);
    localStart = exitPoint - roll(exitNormal, -angle) * .008;
    distance += reachInterface(localStart, roll(inside, -angle), body, exitPoint);
    exitNormal = roll(normalAt(exitPoint, body), angle);
    leaving = refract(inside, -exitNormal, ior);
  }
  vec3 bounce = reflect(ray, hit.normal);
  vec3 reflected = room(point + hit.normal * .01, bounce);
  vec2 softbox = vec2((bounce.x + .48) * 6.3, (bounce.y - .22) * 16.);
  float area = exp(-dot(softbox, softbox));
  reflected += vec3(1., .81, .53) * area * .64;
  if (hero) {
    vec2 edgeLamp = vec2((bounce.x + .34) * 3.9, (bounce.y - .93) * 12.5);
    reflected += vec3(1., .83, .57) * exp(-dot(edgeLamp, edgeLamp)) * .76;
  }
  float angleToEye = abs(dot(ray, hit.normal));
  float fresnel = .045 + .45 * pow(1. - angleToEye, 4.);
  float clearFirst = body == firstGainIndex ? (1. - reveal) : 0.;
  float density = lens == 1 ? mix(.95, .54, clearFirst) : prism == 1 ? 1.48 : 1.34;
  vec3 tint = exp(-vec3(.08, .84, 2.85) * density * distance);
  vec3 outputPoint = bodies[body].xyz + roll(exitPoint, angle);
  vec3 through = dot(leaving, leaving) > .1
    ? transmittedScene(outputPoint + leaving * .012, leaving, body)
    : room(outputPoint, reflect(inside, exitNormal)) * vec3(.88, .59, .26);
  if (hero && dot(leaving, leaving) > .1) {
    vec3 red = refract(inside, -exitNormal, ior - .008);
    vec3 blue = refract(inside, -exitNormal, ior + .009);
    if (dot(red, red) > .1) through.r = transmittedScene(outputPoint + red * .012, red, body).r;
    if (dot(blue, blue) > .1) through.b = transmittedScene(outputPoint + blue * .012, blue, body).b;
  }
  float side = 1. - abs(hit.normal.y);
  float sideRim = side * smoothstep(-.58, .86, hit.normal.x + hit.normal.z * .43);
  vec3 hitLocal = roll(point - bodies[body].xyz, -angle) / extents[body].xyz;
  float rimLight = .40 + .60 * exp(-1.8 * (hitLocal.x - .63) * (hitLocal.x - .63));
  float brightEdge = exp(-11. * abs(hitLocal.y - .52)) * sideRim;
  float focus = bodies[body].w > 2.5 ? 1.40 : 1. - .49 * reveal;
  vec3 amber = vec3(3.35, .96, .23);
  vec3 scattering = vec3(.15, .053, .009) * (1. - tint)
    + vec3(.58, .246, .057) * sideRim * rimLight + vec3(.48, .27, .11) * brightEdge;
  if (lens == 1) {
    focus = hero ? 1.29 : 1. - .68 * reveal;
    amber = mix(vec3(2.78, 1.58, .61), vec3(2.17, 1.49, .93), clearFirst);
    scattering *= hero ? .12 : .13;
  }
  return (mix(through * tint * amber, reflected, fresnel) + scattering) * focus;
}

void main() {
  vec2 screen = (2. * gl_FragCoord.xy - resolution) / resolution.y;
  vec3 eye = prism == 1 ? vec3(4.95, 6.14, 9.89) : vec3(4.12, 5.16, 10.3);
  vec3 forward = normalize(vec3(-1.22, 1.72, -.64) - eye);
  vec3 right = normalize(cross(forward, vec3(0., 1., 0.)));
  vec3 up = cross(right, forward);
  vec3 ray = normalize(forward + .308 * (screen.x * right + screen.y * up));
  Hit hit = trace(eye, ray, -1);
  vec3 result;
  if (hit.body < 0) {
    result = room(eye, ray);
  } else {
    vec3 p = eye + hit.distance * ray;
    result = bodies[hit.body].w < 1.5 ? substrate(p, ray, hit.normal) : throughGlass(p, ray, hit);
  }
  float falloff = 1. - .29 * smoothstep(.42, 2.16, length(screen - vec2(.38, .1)));
  result = result * falloff;
  color = vec4(pow(clamp(result / (1. + .69 * result), 0., 1.), vec3(1. / 2.2)), 1.);
}
`;

function compile(gl: WebGL2RenderingContext, kind: number, code: string) {
  const shader = gl.createShader(kind);
  if (!shader) throw new Error('无法分配玻璃试制着色器');
  gl.shaderSource(shader, code);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const error = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`玻璃试制着色器编译失败：${error}`);
  }
  return shader;
}

function createOptics(canvas: HTMLCanvasElement, look: MacroGlassLook) {
  const gl = canvas.getContext('webgl2', {alpha: false, antialias: false});
  if (!gl) throw new Error('玻璃试制需要 WebGL 2');
  const program = gl.createProgram();
  const mesh = gl.createVertexArray();
  if (!program || !mesh) throw new Error('无法初始化玻璃试制场景');
  for (const [kind, code] of [[gl.VERTEX_SHADER, vertex], [gl.FRAGMENT_SHADER, optics]] as const) {
    const shader = compile(gl, kind, code);
    gl.attachShader(program, shader);
    gl.deleteShader(shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) ?? '玻璃试制着色器链接失败');
  gl.useProgram(program);
  gl.bindVertexArray(mesh);
  gl.viewport(0, 0, canvas.width, canvas.height);
  const location = (name: string) => gl.getUniformLocation(program, name);
  const bodies = location('bodies[0]');
  const size = location('extents[0]');
  const reveal = location('reveal');
  const firstGainIndex = location('firstGainIndex');
  gl.uniform2f(location('resolution'), canvas.width, canvas.height);
  gl.uniform1i(location('prism'), Number(look !== 'clear'));
  gl.uniform1i(location('lens'), Number(look === 'lens'));
  const centers = new Float32Array(13 * 4);
  const extents = new Float32Array(13 * 4);
  return {
    draw(macro: Macro) {
      macro.blocks.forEach((block, index) => {
        const gain = block.glass !== 'ink';
        const small = block.glass === 'glint';
        const floating = block === macro.first ? Math.min(1, (block.pitch ?? 0) / .09) : Number(small);
        const hero = small && look === 'lens';
        const curved = look !== 'clear';
        const width = 1 - floating * (small ? .18 : curved ? .11 : .05);
        const depth = 1 - floating * (small ? curved ? .29 : .20 : curved ? .14 : .09);
        const thickness = block.height / (width * depth);
        const seam = gain ? Math.min(.55, thickness * .1) : 2.2;
        const raise = hero ? macro.reveal * .14 : 0;
        const offset = hero ? macro.reveal * .28 : 0;
        centers.set([(block.x - 1087) * .01 + offset * .43, (790 - block.y + (thickness - block.height) / 2) * .01 + raise,
          ((block.z ?? 0) - block.depth / 2) * .01 + offset, block.height < .05 ? 0 : small ? 3 : gain ? 2 : 1], index * 4);
        extents.set([block.width * width * .005, Math.max(.0002, (thickness - seam) * .005),
          block.depth * depth * .005, (block.pitch ?? 0) * (hero ? 2.47 : small ? .45
            : look === 'lens' && block === macro.first ? 1.42 : 1)], index * 4);
      });
      gl.uniform4fv(bodies, centers);
      gl.uniform4fv(size, extents);
      gl.uniform1f(reveal, macro.reveal);
      gl.uniform1i(firstGainIndex, macro.blocks.indexOf(macro.first));
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.flush();
    },
    dispose() {
      gl.deleteVertexArray(mesh);
      gl.deleteProgram(program);
    },
  };
}

export function MacroGlassCanvas({width, height, macro, look}: {
  width: number; height: number; macro: Macro; look: MacroGlassLook;
}) {
  const {ready} = useSceneContext();
  const canvas = useRef<HTMLCanvasElement>(null);
  const studio = useRef<ReturnType<typeof createOptics> | null>(null);
  useLayoutEffect(() => {
    if (!canvas.current) return;
    const renderer = createOptics(canvas.current, look);
    studio.current = renderer;
    return () => { renderer.dispose(); studio.current = null; };
  }, [height, look, width]);
  useLayoutEffect(() => {
    if (!studio.current) return;
    studio.current.draw(macro);
    ready();
  }, [macro, ready]);
  return <canvas ref={canvas} width={Math.round(width * 1.25)} height={Math.round(height * 1.25)} aria-hidden="true"
    style={{position: 'absolute', inset: 0, width, height, display: 'block'}}/>;
}
