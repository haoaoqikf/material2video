/** 本作品天体外观与显示口径的唯一真源；日距均为平均值，卫星显示母星日距。 */
export type Body = {
  name: string; english: string; kind: string; distance: string; feature: string;
  texture?: string; color: string; tilt?: number; atmosphere?: string;
  rocky?: boolean; parent?: string;
};
export const BODIES: Record<string, Body> = {
  sun: {name: '太阳', english: 'THE SUN', kind: '恒星', distance: '我们的旅程起点', feature: '核心聚变，照亮整个太阳系', texture: 'sun', color: '#ffb44d'},
  mercury: {name: '水星', english: 'MERCURY', kind: '岩质行星', distance: '平均日距 0.39 AU', feature: '古老陨坑，极端昼夜温差', texture: 'mercury', color: '#b6aaa0', rocky: true},
  venus: {name: '金星', english: 'VENUS', kind: '岩质行星', distance: '平均日距 0.72 AU', feature: '厚重大气，强烈温室效应', texture: 'venus', color: '#e9be7d', atmosphere: '#e6b268'},
  earth: {name: '地球', english: 'EARTH', kind: '岩质行星', distance: '平均日距 1 AU', feature: '液态海洋，流动的云与生命', texture: 'earth', color: '#6c9dd4', tilt: 23.4, atmosphere: '#4b9dff'},
  moon: {name: '月球', english: 'THE MOON', kind: '地球的天然卫星', distance: '母星平均日距 1 AU', feature: '古老撞击，保存在寂静表面', texture: 'moon', color: '#b7b6b2', rocky: true, parent: 'earth'},
  mars: {name: '火星', english: 'MARS', kind: '岩质行星', distance: '平均日距 1.52 AU', feature: '红色尘土，曾经流动的水', texture: 'mars', color: '#d78559', rocky: true},
  ceres: {name: '谷神星', english: 'CERES / MAIN BELT', kind: '主小行星带中的矮行星', distance: '平均日距 2.77 AU', feature: '小行星带很空旷，并非碎石墙', color: '#aaa79f', rocky: true},
  jupiter: {name: '木星', english: 'JUPITER', kind: '气态巨行星', distance: '平均日距 5.20 AU', feature: '巨大的云带，持续翻涌的风暴', texture: 'jupiter', color: '#d3af85', tilt: 3.1},
  europa: {name: '木卫二', english: 'EUROPA', kind: '木星的冰质卫星', distance: '母星平均日距 5.20 AU', feature: '交错冰纹下，可能藏着全球海洋', texture: 'europa', color: '#dad0b6', rocky: true, parent: 'jupiter'},
  saturn: {name: '土星', english: 'SATURN', kind: '气态巨行星', distance: '平均日距 9.58 AU', feature: '无数冰粒，组成纤薄而辽阔的环', texture: 'saturn', color: '#d9c19a', tilt: 26.7},
  titan: {name: '土卫六', english: 'TITAN', kind: '土星的浓雾卫星', distance: '母星平均日距 9.58 AU', feature: '甲烷与乙烷，形成另一种河湖', texture: 'titan', color: '#d2a05d', atmosphere: '#d9a054', parent: 'saturn'},
  uranus: {name: '天王星', english: 'URANUS', kind: '冰巨星', distance: '平均日距 19.2 AU', feature: '几乎侧躺着自转的世界', texture: 'uranus', color: '#b1dddf', tilt: 97.8, atmosphere: '#8ed5df'},
  neptune: {name: '海王星', english: 'NEPTUNE', kind: '冰巨星', distance: '平均日距 30.1 AU', feature: '遥远的阳光，猛烈的大气运动', texture: 'neptune', color: '#6394c9', tilt: 28.3, atmosphere: '#649be3'},
  pluto: {name: '冥王星', english: 'PLUTO / KUIPER BELT', kind: '柯伊伯带中的矮行星', distance: '平均日距 39.5 AU', feature: '心形区域，铺展着氮冰平原', texture: 'pluto', color: '#c6b3a0', rocky: true},
  heliopause: {name: '日球层顶', english: 'THE HELIOPAUSE', kind: '太阳风与星际介质的交界', distance: '边界位置随方向与太阳活动变化', feature: '进入星际空间，仍可受太阳引力束缚', color: '#6bbaca'},
  oort: {name: '奥尔特云', english: 'THE OORT CLOUD', kind: '推测性结构 · 艺术示意', distance: '推测外缘约 100000 AU', feature: '尚未直接观测证实的遥远冰天体群', color: '#b4c8e0'},
};
export const CHAPTERS = ['太阳', '内行星', '地月', '小行星带', '木星', '土星', '冰巨星', '柯伊伯带', '边缘'];
export const CHAPTER_IDS = ['sun', 'inner', 'home', 'rock', 'giant', 'rings', 'ice', 'kuiper', 'edge'];
