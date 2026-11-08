/* 在作品及动画库加载前注入。只顺序推进；截图和 I/O 不消耗动画时间。 */
(() => {
  const nativeRAF = window.requestAnimationFrame.bind(window);
  const nativeTimeout = window.setTimeout.bind(window), nativeClearTimeout = window.clearTimeout.bind(window);
  const NativeDate = window.Date;
  const epoch = 1700000000000;
  let now = 0, serial = 0, origin = 0, started = false, bootstrapped = false;
  const rafs = new Map(), timers = new Map();
  const date = function (...args) {
    if (!new.target) return new NativeDate(epoch + now).toString();
    return Reflect.construct(NativeDate, args.length ? args : [epoch + now], new.target);
  };
  Object.setPrototypeOf(date, NativeDate);
  date.prototype = NativeDate.prototype;
  date.now = () => epoch + now;
  window.Date = date;
  Object.defineProperty(performance, 'now', {value: () => now});
  Object.defineProperty(performance, 'timeOrigin', {value: epoch});
  window.requestAnimationFrame = callback => {const id = ++serial; rafs.set(id, callback); return id;};
  window.cancelAnimationFrame = id => rafs.delete(id);
  const schedule = (callback, delay, repeat, args) => {
    if (typeof callback !== 'function') throw new Error('录制时钟只支持函数定时器');
    const id = ++serial;
    timers.set(id, {callback, due: now + Math.max(0, Number(delay) || 0), repeat, args});
    return id;
  };
  window.setTimeout = (fn, delay, ...args) => schedule(fn, delay, 0, args);
  window.setInterval = (fn, delay, ...args) => schedule(fn, delay, Math.max(1, Number(delay) || 0), args);
  window.clearTimeout = window.clearInterval = id => timers.delete(id);

  // 原生 RAF 仅作 compositor 绘制屏障；永远不用于作品时间。
  const paint = () => new Promise(resolve => nativeRAF(() => nativeRAF(resolve)));
  const task = () => new Promise(resolve => {
    const channel = new MessageChannel();
    channel.port1.onmessage = () => {channel.port1.close(); channel.port2.close(); resolve();};
    channel.port2.postMessage(null);
  });
  function callbacks() {
    let count = 0;
    while (true) {
      const next = [...timers].filter(([, timer]) => timer.due <= now + 1e-7)
        .sort((a, b) => a[1].due - b[1].due || a[0] - b[0])[0];
      if (!next) break;
      if (++count > 10000) throw new Error('录制时钟定时器未收敛');
      const [id, timer] = next;
      if (timer.repeat) timer.due += timer.repeat;
      else timers.delete(id);
      timer.callback(...timer.args);
    }
    const batch = [...rafs.keys()];
    for (const id of batch) {
      const callback = rafs.get(id);
      rafs.delete(id);
      if (callback) callback(now);
    }
  }

  const animations = new WeakMap();
  function syncAnimations() {
    // 先量测以创建由本帧样式变更触发的 CSS transition。
    document.documentElement.getBoundingClientRect();
    for (const animation of document.getAnimations()) {
      let state = animations.get(animation);
      if (!state) {
        state = {start: now};
        animations.set(animation, state);
        animation.pause();
      }
      animation.currentTime = now - state.start;
    }
  }

  const media = new WeakMap();
  const proto = HTMLMediaElement.prototype;
  const time = Object.getOwnPropertyDescriptor(proto, 'currentTime');
  const rate = Object.getOwnPropertyDescriptor(proto, 'playbackRate');
  const nativePause = proto.pause;
  function stateOf(element) {
    let state = media.get(element);
    if (!state) {
      state = {base: time.get.call(element), start: now, playing: element.autoplay};
      media.set(element, state);
      nativePause.call(element);
    }
    return state;
  }
  function position(element, state) {
    return state.base + (state.playing ? (now - state.start) / 1000 * element.playbackRate : 0);
  }
  proto.play = async function () {
    const s = stateOf(this);
    if (!s.playing) {
      s.start = now; s.playing = true;
      this.dispatchEvent(new Event('play'));
    }
    if (this.readyState < 2) {
      await new Promise((resolve, reject) => {
        const done = () => {cleanup(); resolve();};
        const failed = () => {cleanup(); reject(new Error('视频播放资源加载失败'));};
        const cleanup = () => {this.removeEventListener('loadeddata', done); this.removeEventListener('error', failed);};
        this.addEventListener('loadeddata', done);
        this.addEventListener('error', failed);
      });
    }
    if (s.playing) this.dispatchEvent(new Event('playing'));
  };
  proto.pause = function () {
    const s = stateOf(this), wasPlaying = s.playing;
    s.base = position(this, s); s.start = now; s.playing = false;
    nativePause.call(this);
    if (wasPlaying) this.dispatchEvent(new Event('pause'));
  };
  Object.defineProperty(proto, 'paused', {configurable: true, get() {return !stateOf(this).playing;}});
  Object.defineProperty(proto, 'currentTime', {...time,
    set(value) {const s = stateOf(this); s.base = Number(value); s.start = now; time.set.call(this, value);},
  });
  Object.defineProperty(proto, 'playbackRate', {...rate,
    set(value) {const s = stateOf(this); s.base = position(this, s); s.start = now; rate.set.call(this, value);},
  });
  async function syncMedia() {
    await Promise.all([...document.querySelectorAll('video')].map(async element => {
      const s = stateOf(element);
      nativePause.call(element);
      if (!Number.isFinite(element.duration) || element.readyState < 1) {
        throw new Error('视频元数据未就绪，不能逐帧采集');
      }
      let target = Math.max(0, position(element, s));
      target = element.loop && element.duration > 0 ? target % element.duration : Math.min(target, element.duration);
      if (Math.abs(time.get.call(element) - target) > 0.000001 || element.seeking) {
        await new Promise((resolve, reject) => {
          const done = () => {cleanup(); resolve();};
          const failed = () => {cleanup(); reject(new Error('视频逐帧解码失败'));};
          const cleanup = () => {element.removeEventListener('seeked', done); element.removeEventListener('error', failed);};
          element.addEventListener('seeked', done);
          element.addEventListener('error', failed);
          time.set.call(element, target);
        });
      }
      if (element.readyState < 2) throw new Error('视频目标帧未解码');
    }));
  }
  window.__M2V_CAPTURE_CLOCK__ = {
    async deadline(promise, milliseconds) {
      let timer;
      try {
        return await Promise.race([promise, new Promise((_, reject) => {
          timer = nativeTimeout(() => reject(new Error('逐帧绘制超时')), milliseconds);
        })]);
      } finally {nativeClearTimeout(timer);}
    },
    begin(atMilliseconds) {origin = Number.isFinite(atMilliseconds) ? atMilliseconds : now;
      if (Number.isFinite(atMilliseconds)) now = atMilliseconds;
      started = true;},
    setTime(value) {
      value += origin;
      if (!Number.isFinite(value) || value < now) throw new Error('录制时钟禁止倒序推进');
      now = value;
    },
    // 纯时间场景专用：绝对定位，允许跳帧与倒序。顺序模式不暴露给 host 调用。
    seek(milliseconds) {
      if (!started) throw new Error('录制开始前不能 seek');
      if (!Number.isFinite(milliseconds) || milliseconds < 0) throw new Error('seek 时间必须是非负有限数');
      now = milliseconds;
    },
    async flush() {
      callbacks();
      await task();
      // 同一时间再刷新：使 React effect 创建的动画和 R3F 看到本帧已提交状态。
      callbacks();
      await task();
      syncAnimations();
      await syncMedia();
      await paint();
    },
    // 异步GPU/Bitmap完成后的合成屏障；不推进时钟，也不重新触发用户RAF。
    paint,
    async bootstrap() {
      if (started) throw new Error('录制开始后禁止执行就绪泵');
      // 纯场景的块首采集必须在挂载前就处于块首时间；否则从 0 跳到块首时，
      // 挂载期间创建的定时器会集中触发，污染状态。
      if (!bootstrapped) {
        const config = window.__M2V_CODE_CONFIG__;
        if (config?.captureMode === 'pure-time') {
          const frame = Number(config.captureStartFrame);
          const fps = Number(config.fps);
          if (Number.isFinite(frame) && frame >= 0 && Number.isFinite(fps) && fps > 0)
            now = frame * 1000 / fps;
        }
        bootstrapped = true;
      }
      // 布局观测和组件挂载也可能依赖 debounce 定时器；就绪时顺序推进，
      // begin 后以此处时间为起点，场景口播时钟仍精确从零开始。
      now += 1000 / 60;
      callbacks(); await task(); syncAnimations(); await paint();
    },
  };
})();
