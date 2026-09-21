import { describe, expect, it } from 'vitest';
import { isLocalUrl } from './offline-guard';

describe('运行期断网守卫的 URL 判定', () => {
  it('允许相对路径与非网络协议', () => {
    expect(isLocalUrl('/videos/a/storyboard.json')).toBe(true);
    expect(isLocalUrl('./local.png')).toBe(true);
    expect(isLocalUrl('data:image/png;base64,AAAA')).toBe(true);
    expect(isLocalUrl('blob:https://localhost/uuid')).toBe(true);
  });
  it('允许本机环回地址', () => {
    expect(isLocalUrl('http://localhost:5178/x')).toBe(true);
    expect(isLocalUrl('http://127.0.0.1:8000/media.json')).toBe(true);
  });
  it('拒绝外部地址', () => {
    expect(isLocalUrl('https://example.com/a.png')).toBe(false);
    expect(isLocalUrl('http://cdn.example.com/x.js')).toBe(false);
    expect(isLocalUrl('ftp://host/file')).toBe(false);
  });
});
