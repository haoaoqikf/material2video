import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  createSceneRandom,
  frameStyle,
  hashSeed,
  mulberry32,
  probe,
  type A2VCodeScene,
  type A2VCodeSceneProps,
} from './index';

/** 一个合法的作品代码场景：默认导出、props 全部来自注入。 */
const GoodScene: A2VCodeScene<{ title: string }> = ({ world, stage, objectStates, scene, localFrame, progress, random }) => {
  void world.objects[0]?.id;
  void stage.id;
  void stage.progress;
  void objectStates.player?.state;
  void scene.data.title;
  void localFrame;
  void progress;
  void random('deco');
  return <div>ok</div>;
};

/** 读节拍状态的代码场景：四个必需字段 + 当前 beat 详情与整幕计划。 */
const BeatAwareScene: A2VCodeScene = ({ beats }) => {
  void beats.current;
  void beats.progress;
  void beats.completed;
  void beats.estimated;
  void beats.active?.action;
  void beats.plan.length;
  return <div>{beats.completed.length}</div>;
};

describe('代码场景 API 类型', () => {
  it('作品组件能以注入的 props 编译', () => {
    expectTypeOf(GoodScene).toMatchTypeOf<A2VCodeScene<{ title: string }>>();
  });
  it('节拍状态是注入的只读 props', () => {
    expectTypeOf(BeatAwareScene).toMatchTypeOf<A2VCodeScene>();
    expectTypeOf<A2VCodeSceneProps['beats']['current']>().toEqualTypeOf<string | null>();
    expectTypeOf<A2VCodeSceneProps['beats']['progress']>().toEqualTypeOf<number>();
    expectTypeOf<A2VCodeSceneProps['beats']['completed']>().toEqualTypeOf<readonly string[]>();
    expectTypeOf<A2VCodeSceneProps['beats']['estimated']>().toEqualTypeOf<boolean>();
  });
  it('作品组件不能声明自己的时间轴字段', () => {
    // 分镜是顺序与时长的单一真源：想要 durationInFrames 或相邻幕的组件
    // 在类型层面就编译不过，第二套时间轴无从产生。
    type TimelineProps = A2VCodeSceneProps & { durationInFrames: number; totalFrames: number; nextScene?: unknown };
    // @ts-expect-error durationInFrames / totalFrames / nextScene 不在注入的 props 上
    const BadScene: A2VCodeScene = (_props: TimelineProps) => null;
    expectTypeOf(BadScene).toMatchTypeOf<A2VCodeScene>();
  });
  it('scene.data 通过泛型获得类型', () => {
    expectTypeOf<Parameters<typeof GoodScene>[0]['scene']['data']>().toEqualTypeOf<{ title: string }>();
  });
});

describe('稳定种子随机', () => {
  it('相同种子返回相同序列', () => {
    const a = mulberry32(hashSeed('scene::node'));
    const b = mulberry32(hashSeed('scene::node'));
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });
  it('不同节点序列相互独立', () => {
    const random = createSceneRandom('intro');
    expect(random('a')).not.toBe(random('b'));
  });
  it('求值顺序不影响每个节点的序列', () => {
    const random = createSceneRandom('intro');
    const first = random('a');
    const other = random('b');
    const again = createSceneRandom('intro')('a');
    expect(first).toBe(again);
    expect(other).not.toBe(first);
  });
  it('序列落在 [0, 1)', () => {
    const next = mulberry32(hashSeed('x'));
    for (let i = 0; i < 1000; i += 1) {
      const value = next();
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});

describe('探针协议 helper', () => {
  it('输出稳定 DOM 标记', () => {
    expect(probe({ node: 'headline', role: 'headline' })).toEqual({
      'data-a2v-node': 'headline',
      'data-a2v-role': 'headline',
    });
    expect(probe({ node: 'chart', inside: 'panel', schematic: true })).toEqual({
      'data-a2v-node': 'chart',
      // inside 输出为选择器：K8 容器归属量测用它做 querySelector
      'data-a2v-inside': '[data-a2v-node="panel"]',
      'data-a2v-schematic': '',
    });
  });
  it('frameStyle 只输出确定性属性', () => {
    expect(frameStyle(0.5, { opacity: true, rise: 36 })).toEqual({
      opacity: 0.5,
      transform: 'translateY(18px)',
    });
    expect(frameStyle(2, { opacity: true })).toEqual({ opacity: 1 });
  });
});
