import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it} from 'vitest';
import {chartLinePath, chartAreaPath} from './chart-geometry';
import {layoutDiagram, Diagram} from './diagram';
import {MathFormula} from './math';
import {Atom} from './icons';

describe('共享几何与外部表达工具', () => {
  it('保留均匀 Catmull-Rom 的端点与首段切线，并切断无效数据', () => {
    const path = chartLinePath([[0, 0], [60, 60], [120, 0]], 'catmull-rom');
    expect(path).toMatch(/^M0,0C10,10,40,60,60,60/);
    expect(path).toMatch(/120,0$/);
    expect(chartLinePath([[0, 0], [NaN, 2], [3, 4]])).not.toContain('NaN');
    expect(chartAreaPath([[0, 1], [3, 4]], 10)).toContain('10');
  });

  it('ELK 重复/重排输入得到相同布局，输入不变，绘制不再求布局', async () => {
    const nodes = [{id: 'b', label: '结果'}, {id: 'a', label: '原因'}];
    const edges = [{id: 'ab', source: 'a', target: 'b'}];
    const before = JSON.stringify({nodes, edges});
    const layout = await layoutDiagram(nodes, edges);
    expect(await layoutDiagram([...nodes].reverse(), edges)).toEqual(layout);
    expect(JSON.stringify({nodes, edges})).toBe(before);
    expect(layout.nodes.find(n => n.id === 'a')!.x).toBeLessThan(layout.nodes.find(n => n.id === 'b')!.x);
    expect(layout.edges[0].points.length).toBeGreaterThanOrEqual(2);
    const draw = (progress: number) => renderToStaticMarkup(<Diagram layout={layout} progress={progress}/>);
    expect(draw(.5)).toBe(draw(.5));
    expect(draw(1)).toContain('结果');
    expect(draw(0)).toContain('opacity="0"');
    const unicode = [{id: 'é', label: '组合'}, {id: 'e\u0301', label: '分解'}];
    expect(await layoutDiagram(unicode, [])).toEqual(await layoutDiagram([...unicode].reverse(), []));
  });

  it('拒绝布局尺寸、重复节点和未知连接，孤立节点可布局', async () => {
    await expect(layoutDiagram([{id: 'a', label: '', width: 0}], [])).rejects.toThrow('尺寸');
    await expect(layoutDiagram([{id: 'a', label: ''}, {id: 'a', label: ''}], [])).rejects.toThrow('重复');
    await expect(layoutDiagram([{id: 'a', label: ''}], [{id: 'ab', source: 'a', target: 'b'}])).rejects.toThrow('未知');
    expect((await layoutDiagram([{id: 'a', label: '独立'}], [])).nodes).toHaveLength(1);
  });

  it('公式复用 KaTeX 排版并拒绝无效输入，图标继承尺寸颜色', () => {
    const formula = renderToStaticMarkup(<MathFormula tex={String.raw`\frac{1}{2}+\sqrt{x^2}`} />);
    expect(formula).toContain('katex-mathml');
    expect(formula).toContain('mfrac');
    expect(() => renderToStaticMarkup(<MathFormula tex={String.raw`\notARealCommand`}/>)).toThrow();
    const icon = renderToStaticMarkup(<Atom size={72} color="#ffcc00"/>);
    expect(icon).toContain('width="72"');
    expect(icon).toContain('stroke="#ffcc00"');
  });
});
