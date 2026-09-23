import type { SceneNode } from '@/schema/storyboard';
import type { GeometryBox } from './motionPlan';

/** 受控布局的归一化几何；只依赖场景树，不读取浏览器布局。 */
export function sceneGeometry(tree?: SceneNode): ReadonlyMap<string, GeometryBox> {
  const boxes = new Map<string, GeometryBox>();
  const walk = (node: SceneNode, box: GeometryBox): void => {
    boxes.set(node.id, box); const children = node.children ?? []; if (!children.length) return;
    if (node.type === 'radial' || node.type === 'cycle') {
      children.forEach((child, index) => { const angle = (Math.PI * 2 * index) / children.length - Math.PI / 2; const size = .22; walk(child, { x: box.x + box.width * (.5 + .34 * Math.cos(angle)) - size / 2, y: box.y + box.height * (.5 + .34 * Math.sin(angle)) - size / 2, width: size, height: size, radius: .08 }); }); return;
    }
    const horizontal = node.type === 'row' || node.type === 'split' || node.type === 'flow' || node.type === 'timeline' || node.direction === 'horizontal' || node.direction === 'ltr' || node.direction === 'rtl';
    children.forEach((child, index) => { const share = 1 / children.length; walk(child, horizontal ? { x: box.x + box.width * share * index, y: box.y, width: box.width * share, height: box.height, radius: .04 } : { x: box.x, y: box.y + box.height * share * index, width: box.width, height: box.height * share, radius: .04 }); });
  };
  if (tree) walk(tree, { x: 0, y: 0, width: 1, height: 1, radius: 0 }); return boxes;
}
