/** 共享组件内部约定：量测代理使用的角色与状态属性。 */
export function dataAttrs(role?: string, state?: string): Record<string, string> {
  return {
    ...(role ? {'data-m2v-role': role} : {}),
    ...(state ? {'data-m2v-state': state} : {}),
  };
}
