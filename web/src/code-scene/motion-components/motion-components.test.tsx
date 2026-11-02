import type {ReactElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it} from 'vitest';
import {
  BarGrowth, Blur, Callout, DrawLine, FadeIn, Glow, MarkerHighlight, RollingNumber,
  SlideIn, Typewriter, ZoomIn, pathDrawProps, styleAt,
} from './index';

const markup = (node: ReactElement) => renderToStaticMarkup(node);

describe('shared motion components', () => {
  it('fades from the requested opacity and clamps out-of-range progress', () => {
    expect(markup(<FadeIn progress={0}>x</FadeIn>)).toContain('opacity:0');
    expect(markup(<FadeIn progress={2}>x</FadeIn>)).toContain('opacity:1');
  });

  it('slides and zooms with a transform', () => {
    expect(markup(<SlideIn progress={1} from="bottom" distance={24}>x</SlideIn>))
      .toContain('translateY(0px)');
    expect(markup(<ZoomIn progress={1} fromScale={0.92} toScale={1}>x</ZoomIn>))
      .toContain('scale(1, 1)');
  });

  it('renders blur and glow filters', () => {
    expect(markup(<Blur progress={1} from={12} to={0}>x</Blur>)).toContain('blur(0px)');
    expect(markup(<Glow progress={1} radius={18} color="#fff">x</Glow>))
      .toContain('drop-shadow(0 0 18px #fff)');
  });

  it('draws a path deterministically', () => {
    const path = 'M0 0 L100 0';
    expect(pathDrawProps(path, 0.5)).toEqual(pathDrawProps(path, 0.5));
    expect(markup(<DrawLine d={path} progress={1}/>)).toContain('stroke-dashoffset="0"');
  });

  it('rolls and types with explicit progress', () => {
    expect(markup(<RollingNumber from={0} to={100} progress={0.5}/>)).toContain('50');
    expect(markup(<RollingNumber from={0} to={100} progress={1}/>)).toContain('100');
    expect(markup(<Typewriter text="abcd" progress={1}/>)).toContain('d');
  });

  it('grows bars from zero', () => {
    const zero = markup(<BarGrowth values={[10, 20]} progress={0}/>);
    const full = markup(<BarGrowth values={[10, 20]} progress={1}/>);
    expect(zero).toContain('height="0"');
    expect(full).not.toContain('height="0"');
  });

  it('generates deterministic sketch geometry with a seed', () => {
    const props = {box: {x: 10, y: 10, width: 120, height: 40}, progress: 1, seed: 7};
    expect(markup(<MarkerHighlight {...props}/>)).toEqual(markup(<MarkerHighlight {...props}/>));
    expect(markup(<MarkerHighlight {...props}/>)).toContain('<path');
  });

  it('draws a deterministic callout leader', () => {
    expect(markup(<Callout text="note" at={{x: 0, y: 0}} label={{x: 100, y: 40}} progress={1}/>))
      .toContain('<path');
  });

  it('interpolates CSS styles purely', () => {
    expect(styleAt(0.5, {opacity: 0}, {opacity: 1}, t => t)).toEqual({opacity: 0.5});
  });
});
