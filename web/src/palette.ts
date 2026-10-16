/** 讲解画面的主题色板：composition 与代码场景录制页共用同一份真源。 */
export type Palette = {bg: string; ink: string; muted: string; panel: string; border: string; accent: string};
export type Theme = 'dark' | 'light';
export const palettes: Record<Theme, Palette> = {
  dark: {bg: '#111720', ink: '#f3f4f6', muted: '#c8d0da', panel: '#1c2734', border: '#526174', accent: '#f7c85b'},
  light: {bg: '#f7f5f0', ink: '#18212b', muted: '#465363', panel: '#ffffff', border: '#8793a1', accent: '#855800'},
};
