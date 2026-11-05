"""规范示例编排（R6）：事件是画面、字幕和拟音的共同时间源。"""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
FPS=30
SECTIONS=[('hook',330),('proof',540),('resolution',330)]
EVENTS={
 'hook':{'number-lock':81,'title-start':90,'title-land':110,'ball-hop':152,'snow-start':210,'snow-hit-1':238,'snow-hit-2':272,'snow-impact':288,'snow-wipe':300},
 'proof':{'row-1':20,'row-2':64,'row-3':108,'table-flight':150,'curve-start':180,'curve-run':194,'curve-result':320,'bars-start':360,'bar-10':378,'bar-50':426,'bar-100':474,'bar-flash':494,'exponent-flight':522},
 'resolution':{'formula-base':12,'formula-rate':40,'exponent-land':67,'answer-count':78,'answer-lock':123,'answer-release':168,'closing-land':192,'closing-settle':218}}
CAPTIONS={
 'hook':[(0,78,'从100开始，100轮后会怎样？'),(222,300,'雪球越大，下一次卷起的雪越多。')],
 'proof':[(8,144,'多出来的，也留给下一轮。'),(190,304,'开始差不多，后来逐渐拉开。'),(310,352,'差距出现了。'),(388,474,'差距，正在放大。'),(482,530,'从0.46，扩大到70.48。')],
 'resolution':[(8,163,'每一轮，都站在上一轮之上。')]}
SOUND={
 'number-lock':('spark',-9),'title-start':('travel',-12),'title-land':('contact',-8),'ball-hop':('contact',-14),
 'snow-start':('contact',-12),'snow-hit-1':('contact',-11),'snow-hit-2':('contact',-9),'snow-impact':('release',-5),'snow-wipe':('travel',-9),
 'row-1':('tick',-16),'row-2':('tick',-14),'row-3':('tick',-12),'table-flight':('travel',-13),'curve-start':('spark',-15),
 'curve-result':('contact',-12),'bars-start':('travel',-12),'bar-10':('contact',-12),'bar-50':('contact',-10),'bar-100':('contact',-8),'bar-flash':('release',-6),'exponent-flight':('travel',-12),
 'formula-base':('contact',-12),'formula-rate':('spark',-12),'exponent-land':('contact',-10),'answer-count':('rolling',-20),
 'answer-lock':('release',-3),'answer-release':('travel',-13),'closing-land':('spark',-8),'closing-settle':('contact',-12)}

def write(p,value):
 p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 scenes=[];checks=[];effects=[]
 for sid,duration in SECTIONS:
  scenes.append({'id':sid,'template':'code','keywords':['复利效应','理想模型','多种信息形式'],'durationFrames':duration,'transition':'cut','narrationSegments':[],
    'content':{'title':'让积累，参与下一次','entry':f'scenes/{sid}.tsx','props':{'capture':{'mode':'pure-time','jobs':2,'blockFrames':30,'verifyFrames':2},'screenSubtitles':[{'startFrame':a,'endFrame':b,'text':t} for a,b,t in CAPTIONS[sid]]}},
    'events':[{'id':k,'frame':v} for k,v in EVENTS[sid].items()]})
  cp={'id':f'cp-{sid}','shotId':f'{sid}-shot','frame':duration-42,'window':[0,duration],
    'expected':[],'textPlan':[{'role':'screen-subtitle','text':t,'window':[a,b]} for a,b,t in CAPTIONS[sid]],
    'claims':[],'forbidden':['年化收益','保证成功','必然成功'],
    'measurement':{'subtitleRoles':['screen-subtitle'],'thresholdSource':'横屏字幕安全区与393宽显示'},'sampleStep':3,'minEventFrames':3}
  if sid=='hook':cp['measurement']['allowedOverlaps']=[['hero-number','hero-number'],['focus-ball','hero-number'],['focus-ball','title-first'],['focus-ball','title-second'],['focus-ball','snowball']]
  shot={'id':f'{sid}-shot','tier':'A' if sid in ('hook','proof') else 'B','window':[0,duration],'core':sid in ('hook','proof')}
  if sid=='hook':
   shot['timeStructure']={key:{'window':window,'audience':'先形成问题再跟随同一焦点','visible':visible,'attention':focus,'toleranceFrames':3,'failure':'焦点丢失或未看清对象变化'} for key,window,visible,focus in [
    ('establish',[0,81],'起点100、1%假设与滚动数值','中心数字'),('change',[81,210],'小数点离开数字，在大字间运动','小球与字间落点'),
    ('reveal',[210,288],'小球接触地面并卷雪增大','雪球与雪面'),('result',[288,330],'局部释放后收拢到表格起点，露出100.00并停留','雪球与100.00') ]}
  if sid=='proof':
   shot['timeStructure']={key:{'window':window,'audience':'观察前后状态并获得新信息','visible':visible,'attention':focus,'toleranceFrames':3,'failure':'前后关系丢失或信息形式只是在重复结论'} for key,window,visible,focus in [
    ('establish',[0,64],'初始100与前两行增长','活动行'),('change',[64,180],'新增量参与后续增长，表格生成坐标','总量与下一行新增'),
    ('reveal',[180,352],'两条线先接近后分开，终点数值可读','金色端点'),('result',[352,522],'10/50/100轮的差距逐次变大','当前柱组'),('hold',[522,540],'100抬向指数位置','100')]}
  checks.append({'id':sid,'durationFrames':duration,'shots':[shot],'checkpoints':[cp]})
  effects.extend({'assetId':SOUND[k][0],'sceneId':sid,'eventId':k,'gainDb':SOUND[k][1]} for k in EVENTS[sid] if k in SOUND)
 # 加速数字的触点使用命名事件，不靠每帧叠加声源。
 for i,fr in enumerate([5,16,28,40,50,59,67,73]):
  event=f'roll-{i}';scenes[0]['events'].append({'id':event,'frame':fr});effects.append({'assetId':'tick','sceneId':'hook','eventId':event,'gainDb':-25+i})
 write(ROOT/'storyboard.json',{'version':8,'schemaVersion':8,'title':'让积累，参与下一次','fps':30,'width':1920,'height':1080,'targetSeconds':40,
  'input':{'kind':'topic','topic':'复利效应：成果参与下一轮。雪球是寓言；数字是初始100、每轮固定增长1%的理想模型，与每轮固定加1比较，不代表任何现实对象必然如此增长。'},
  'scenes':scenes,'soundtrack':{'effects':effects,'silence':[{'startFrame':972,'endFrame':988,'fadeFrames':3}]}})
 contract={'version':2,'cycleId':'compound-connect-r6-example-20261106','fps':30,'width':1920,'height':1080,
  'reviewPlan':{'basis':'R6精修沿用八节拍论证结构，核对图表字阶、数值接棒与释放收敛；开场、图表和公式按当前候选重新观察。',
   'risks':[{'id':'multi-form-rhythm','kind':'structure-timing','scope':{'checkpointIds':['cp-hook','cp-proof']},'reason':'数字滚动、文字互动、跨形式焦点接棒和爆闪强弱须用完整过程确认，关键采用项见style-reference.md与DESIGN逐场表。','requiredEvidence':['production/checkpoints/cp-hook/window.mp4','production/checkpoints/cp-proof/window.mp4']},
    {'id':'retained-model','kind':'core-event','scope':{'checkpointIds':['cp-proof']},'reason':'表格必须说明新增参与下一轮；折线与柱形分别揭示过程和轮次差距，不是同一数字换皮。','requiredEvidence':['production/checkpoints/cp-proof/window.mp4']}]},'scenes':checks}
 p=ROOT/'DESIGN.md';s=p.read_text(encoding='utf-8');block='```m2v-checkpoints\n'+json.dumps(contract,ensure_ascii=False,indent=2)+'\n```'
 s=re.sub(r'```m2v-checkpoints\s*\n.*?```',lambda _:block,s,flags=re.S)
 p.write_text(s,encoding='utf-8')
 print('R6 example: 3 scenes / 8 beats / 1200 frames. Contract, events and effects generated.')
if __name__=='__main__':main()

# 测试和工具可显式重定向ROOT，在空目录验证重建与幂等性。
compose = main
