import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it} from 'vitest';
import {
  ChapterTrack, MaskReveal, PathMorph, Pictogram, Timeline, Waveform, resamplePeaks,
} from './index';

describe('path morph component', () => {
  it('changes geometry with progress and is repeatable', () => {
    const props = {from: 'M0 0 L100 0', to: 'M0 0 L0 100'};
    const start = renderToStaticMarkup(<PathMorph {...props} progress={0}/>);
    const end = renderToStaticMarkup(<PathMorph {...props} progress={1}/>);
    expect(start).not.toEqual(end);
    expect(start).toEqual(renderToStaticMarkup(<PathMorph {...props} progress={0}/>));
  });
});

describe('mask reveal', () => {
  it('computes wipe and iris clip paths from progress', () => {
    const linear = (value: number) => value;
    expect(renderToStaticMarkup(<MaskReveal progress={0.5} easing={linear}>x</MaskReveal>))
      .toContain('inset(0 50% 0 0)');
    expect(renderToStaticMarkup(
      <MaskReveal progress={0.5} easing={linear} direction="left">x</MaskReveal>,
    )).toContain('inset(0 0 0 50%)');
    expect(renderToStaticMarkup(
      <MaskReveal progress={0.5} easing={linear} mode="iris" at={{x: 0, y: 0}} radius={100}>x</MaskReveal>,
    )).toContain('circle(50px at 0px 0px)');
  });

  it('accepts a custom clip function', () => {
    expect(renderToStaticMarkup(
      <MaskReveal progress={1} clip={() => 'polygon(0 0, 100% 0, 100% 100%)'}>x</MaskReveal>,
    )).toContain('polygon(0 0, 100% 0, 100% 100%)');
  });
});

describe('timeline and chapter track', () => {
  it('reveals events in timeline order', () => {
    const items = [{at: 0, label: '开始'}, {at: 50, label: '中段'}, {at: 100, label: '结束'}];
    const hidden = renderToStaticMarkup(<Timeline items={items} progress={0}/>);
    const shown = renderToStaticMarkup(<Timeline items={items} progress={1}/>);
    expect(hidden.match(/<text/g)).toHaveLength(1);
    expect(shown.match(/<text/g)).toHaveLength(3);
    expect(shown).toContain('结束');
  });

  it('marks the active chapter by progress', () => {
    const markup = renderToStaticMarkup(
      <ChapterTrack chapters={['一', '二', '三']} progress={0.5}/>,
    );
    expect(markup).toContain('二');
    expect(markup).toContain('#F8D893');
  });
});

describe('pictogram and waveform', () => {
  it('fills whole and partial cells from a value', () => {
    const whole = renderToStaticMarkup(<Pictogram count={10} value={5} progress={1}/>);
    const partial = renderToStaticMarkup(<Pictogram count={10} value={4.5} progress={1}/>);
    expect(whole.match(/fill="#F8D893"/g)).toHaveLength(5);
    expect(partial.match(/fill="#F8D893"/g)).toHaveLength(5);
    expect(partial).toContain('opacity="0.5"');
  });

  it('resamples peaks and reveals bars by progress', () => {
    expect(resamplePeaks([0, 1, -1, 0.5], 2)).toEqual([1, 1]);
    const markup = renderToStaticMarkup(
      <Waveform samples={[0, 1, -1, 0.5]} bars={2} progress={1}/>,
    );
    expect(markup.match(/<rect/g)).toHaveLength(2);
    expect(markup).toEqual(renderToStaticMarkup(
      <Waveform samples={[0, 1, -1, 0.5]} bars={2} progress={1}/>,
    ));
  });
});
