/**
 * 阻尼谐振子的解析解（vendored）
 *
 * 来源：wobble 1.5.1 · MIT · Copyright 2017 Adam Miskiewicz
 *       https://github.com/skevy/wobble （src/index.ts 的振荡解部分）
 *       许可证全文见同目录 wobble-LICENSE。
 *
 * 为什么用外部实现而不是自己写一条「像弹簧」的曲线：
 * 弹簧有唯一的正确解。公式 1 - e^(-kx)·cos(wx) 看着也像，但
 *   - 参数（k、w）与任何物理量无关，没人知道它们变大是变快还是变弹；
 *   - 收敛时间算不出来，只能画出来目测（实测就是这么错的：注释写「0.6 秒收敛」，
 *     真实曲线在 0.1 秒内就走完了）；
 *   - 想要「过冲再小一点」时，只能试。
 * 下面这份是 x'' + 2ζω₀x' + ω₀²x = 0 的闭式解，因此在**任意时刻都能直接求值**——
 * 逐帧渲染正好需要「给帧号就给值」，不必从第 0 帧开始积分（这也是不选
 * 逐帧积分型实现的原因：拖动进度条或随机访问某一帧时，积分型必须重放全过程）。
 *
 * 相对上游的改动（仅此四处）：
 *   1. 只保留位置解，去掉 Spring 类、监听器、定时器与速度解；
 *   2. 时间单位由毫秒改为秒（上游 omega0 = sqrt(k/m)/1000）；
 *   3. 参数改为 response / dampingFraction 两个（Apple 的说法）：
 *      response 是自然周期（秒），dampingFraction 是阻尼比 ζ；
 *      上游的 stiffness/damping/mass 可由 ζ = c/(2√(km))、ω₀ = √(k/m) 换算，
 *      这里不再保留三参数写法——三参数里只有两个自由度是独立的；
 *   4. 起点固定从静止开始（v₀ = 0），x₀ = 1（上游的 x₀ = toValue - fromValue），
 *      返回值直接是 0→1 的进度；
 *      临界阻尼分支用 |ζ-1| < 1e-6 判定，避免浮点相等把临界点漏给欠阻尼分支。
 */
(function (global) {
  'use strict';

  /**
   * @param {number} seconds 距入场起点的秒数（≥0）
   * @param {number} response 自然周期，秒。越小越快，0.5 表示半秒一个周期
   * @param {number} dampingFraction 阻尼比 ζ：<1 欠阻尼（会过冲）、=1 临界、>1 过阻尼
   * @returns {number} 0→1 的进度，欠阻尼时峰值可能略大于 1
   */
  function position(seconds, response, dampingFraction) {
    if (!(seconds > 0)) {
      return 0;
    }
    var zeta = dampingFraction === undefined ? 1 : dampingFraction;
    if (!(zeta >= 0)) {
      zeta = 0;
    }
    var period = response > 0 ? response : 1;
    var omega0 = (2 * Math.PI) / period;
    // x0 是「距目标的初始位移」：从 0 走到 1 时它是 +1。
    // 写成 -1 会让入场从相反方向开始（进度 π 附近到 1.33 再落回），
    // 这个符号错了测试会立刻报出来（实测位移 −14.43px 而不是 +14.4px）。
    var x0 = 1;
    var v0 = 0;

    if (zeta < 1 - 1e-6) {
      // 欠阻尼：衰减的振荡
      var omega1 = omega0 * Math.sqrt(1 - zeta * zeta);
      var envelope = Math.exp(-zeta * omega0 * seconds);
      return (
        1 -
        envelope *
          (((v0 + zeta * omega0 * x0) / omega1) * Math.sin(omega1 * seconds) +
            x0 * Math.cos(omega1 * seconds))
      );
    }
    if (zeta <= 1 + 1e-6) {
      // 临界阻尼：最快且不过冲
      var critical = Math.exp(-omega0 * seconds);
      return 1 - critical * (x0 + (v0 + omega0 * x0) * seconds);
    }
    // 过阻尼：不振荡，慢慢爬到位
    var omega2 = omega0 * Math.sqrt(zeta * zeta - 1);
    var overdamped = Math.exp(-zeta * omega0 * seconds);
    return (
      1 -
      (overdamped *
        ((v0 + zeta * omega0 * x0) * Math.sinh(omega2 * seconds) +
          omega2 * x0 * Math.cosh(omega2 * seconds))) /
        omega2
    );
  }

  /**
   * 曲线进入目标 ±band 带内所需的秒数。
   *
   * 衰减包络是 e^(-ζω₀t)，曲线与目标的距离永远不超过它，所以由
   * e^(-ζω₀t) ≤ band 解出 t = ln(1/band)/(ζω₀) 就是一个稳妥的上界。
   * 有了它，「到位」是一个确切的时刻，而不是永远无限逼近 1——
   * 用「位移小于阈值就返回 1」的写法会把 lively 那种回弹在半途截掉。
   *
   * @param {number} response 自然周期，秒
   * @param {number} dampingFraction 阻尼比 ζ
   * @param {number} [band=0.001] 允许的剩余偏差
   * @returns {number} 秒数；ζ ≤ 0 时返回 Infinity（永不收敛）
   */
  function restSeconds(response, dampingFraction, band) {
    var zeta = dampingFraction === undefined ? 1 : dampingFraction;
    if (!(zeta > 0)) {
      return Infinity;
    }
    var period = response > 0 ? response : 1;
    var omega0 = (2 * Math.PI) / period;
    var tolerance = band === undefined ? 0.001 : band;
    return Math.log(1 / tolerance) / (zeta * omega0);
  }

  global.A2VSpring = {
    position: position,
    restSeconds: restSeconds,
    source: 'wobble@1.5.1',
    license: 'MIT'
  };
})(window);
