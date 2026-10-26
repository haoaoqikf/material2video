/** 由场景打包器注入，参数只读；导入本模块不会自动改变画面。 */
declare module 'm2v/style' {
  type JsonValue = string | number | boolean | null | readonly JsonValue[] | {readonly [key: string]: JsonValue};
  export const identity: Readonly<{id: string; version: string; fingerprint: string}> | null;
  export const tokens: {readonly [key: string]: JsonValue};
}
declare module 'm2v/style/assets/*' {
  const url: string;
  export default url;
}
