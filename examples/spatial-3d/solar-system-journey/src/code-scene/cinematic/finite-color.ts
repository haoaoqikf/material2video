import {ShaderMaterial} from 'three';
import {ShaderPass} from 'postprocessing';

/**
 * RGBA16F场景色在进入Bloom前的数值边界。
 * 单像素NaN/Inf会被模糊扩散至全屏；只清除该像素的异常RGB，保留有限HDR值。
 * 必须独立成Pass：若与Bloom合并，Bloom可能先读取尚未保护的输入纹理。
 */
export class FiniteColorPass extends ShaderPass {
  constructor() {
    super(new ShaderMaterial({
      uniforms: {inputBuffer: {value: null}},
      vertexShader: 'void main() { gl_Position = vec4(position, 1.0); }',
      fragmentShader: `
        uniform sampler2D inputBuffer;
        void main() {
          // 与输入一一对应读取，避免额外过滤改变已经量化的有限颜色。
          vec4 color = texelFetch(inputBuffer, ivec2(gl_FragCoord.xy), 0);
          // NaN的有序比较为false；65504是当前HalfFloat缓冲的最大有限值。
          if (!all(lessThanEqual(abs(color.rgb), vec3(65504.0)))) color.rgb = vec3(0.0);
          gl_FragColor = color;
        }`,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    }));
  }
}
