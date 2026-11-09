import {expect, it} from 'vitest';
import {createCapitalGeometry} from './components/capital-geometry';
import {CAPITAL_STYLE} from './capital-style';

it('受光凸面的正面朝向镜头，不能被背面剔除而退化为平圆', () => {
  const geometry = createCapitalGeometry();
  try {
    const normals = geometry.face.getAttribute('normal');
    for (let i = 0; i < normals.count; i++) expect(normals.getZ(i)).toBeGreaterThan(.5);
    geometry.face.computeBoundingBox();
    const box = geometry.face.boundingBox!;
    expect(box.max.z - box.min.z).toBeGreaterThan(2);
    expect(box.max.z).toBeCloseTo(CAPITAL_STYLE.faceHeight);
    geometry.body.computeBoundingBox();
    expect(geometry.body.boundingBox!.min.z).toBeCloseTo(-CAPITAL_STYLE.backDepth);
    expect(box.max.x - box.min.x).toBeLessThanOrEqual(42);
  } finally {Object.values(geometry).forEach(value => value.dispose());}
});
