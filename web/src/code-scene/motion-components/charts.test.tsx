import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it} from 'vitest';
import {AreaPlot, Axis, LinePlot, Sparkline} from './index';

describe('pure-time chart components', () => {
  it('reveals a line from the start of the path', () => {
    const start = renderToStaticMarkup(<LinePlot series={[{values: [1, 2, 3]}]} progress={0}
      width={400} height={200}/>);
    const end = renderToStaticMarkup(<LinePlot series={[{values: [1, 2, 3]}]} progress={1}
      width={400} height={200}/>);
    expect(start).not.toContain('stroke-dashoffset="0"');
    expect(end).toContain('stroke-dashoffset="0"');
    expect(start).toEqual(renderToStaticMarkup(<LinePlot series={[{values: [1, 2, 3]}]} progress={0}
      width={400} height={200}/>));
  });

  it('clips area fill to the progress width', () => {
    const markup = renderToStaticMarkup(<AreaPlot series={[{values: [1, 3, 2]}]} progress={0.5}
      width={400} height={200}/>);
    expect(markup).toContain('clipPath');
    expect(markup).toContain('width="184"');
  });

  it('renders a sparkline with an optional fill', () => {
    const markup = renderToStaticMarkup(<Sparkline values={[1, 3, 2]} fill="rgba(0, 0, 0, 0.2)"/>);
    expect(markup).toContain('rgba(0, 0, 0, 0.2)');
    expect(markup).toContain('<clipPath');
  });

  it('reveals axis ticks in order with progress', () => {
    const props = {orientation: 'x' as const, domain: [0, 2] as const, range: [0, 100] as const,
      at: 50, ticks: 2};
    const hidden = renderToStaticMarkup(<Axis {...props} progress={0}/>);
    const shown = renderToStaticMarkup(<Axis {...props} progress={1}/>);
    expect(hidden.match(/<text/g)).toHaveLength(1);
    expect(shown.match(/<text/g)).toHaveLength(3);
    expect(shown).toContain('>2</text>');
  });
});
