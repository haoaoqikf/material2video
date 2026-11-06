/** 本作品唯一数学定义；雪球是类比，不能把它的体积当成这个模型。 */
export const MODEL={initial:100,rate:.01,rounds:100} as const;
export const compounded=(n:number)=>MODEL.initial*Math.pow(1+MODEL.rate,n);
export const constant=(n:number)=>MODEL.initial+MODEL.initial*MODEL.rate*n;
export const increment=(n:number)=>compounded(n-1)*MODEL.rate;
export const CHART={left:230,right:1650,bottom:790,top:345,min:100,max:300} as const;
export const chartPoint=(n:number,v:number):[number,number]=>[
  CHART.left+(CHART.right-CHART.left)*n/MODEL.rounds,
  CHART.bottom-(v-CHART.min)/(CHART.max-CHART.min)*(CHART.bottom-CHART.top),
];
export const BAR={centers:[450,960,1470],rounds:[10,50,100],bottom:790,scale:1.65} as const;
