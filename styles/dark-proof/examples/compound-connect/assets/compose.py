"""复利效应《接》：唯一时序源，生成分镜与合同；不改媒体、评审或人工设计记录。"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FPS=30
BEATS={
    'seed-drop':.5,'seed-land':2,'mother-grow':5,'mother-ready':12,
    'mother-fruit':14,'first-release':16,'first-land':19,'child-grow':19.8,'child-ready':25.8,
    'child-fruit':27,'second-release':30.5,'second-land':33.5,'third-grow':34.3,'third-ready':37.5,
    'third-fruit':39,'grove-reveal':41,'learning-first':45.5,'learning-reuse':49,
    'learning-extend':52.5,'closing-return':56,'title-arrive':62,'finish':68,
}
SECTIONS=[('opening',0,12),('core',12,38),('grove',38,45),('learning',45,56),('closing',56,68)]
CAPTIONS=[
    (.2,4.7,'为什么有些积累，后来会越来越快？'),
    (5.2,11.7,'一颗种子，先长成一棵树。'),
    (12.3,16,'树，结出了新的种子。'),
    (16.3,21.5,'其中一颗，落地、生根。'),
    (22,26.5,'它长成了另一棵树。'),
    (27,32,'新长出的树，也结出了种子。'),
    (32.3,37.8,'新增的部分，也开始创造。'),
    (38.3,44.7,'增长的来源，变多了。'),
    (45.2,48.7,'学会一个方法。'),
    (49.1,52.2,'下一题，用上它。'),
    (52.6,55.8,'它又帮你，理解新的问题。'),
    (56.3,61.7,'让积累，推动新的积累。'),
    (62.2,68,'这，就是复利效应。'),
]
SOUNDS={'seed-land':'land','mother-fruit':'emit','first-release':'travel','first-land':'land',
        'child-ready':'merge','child-fruit':'reveal','second-release':'travel','second-land':'land',
        'third-fruit':'emit','grove-reveal':'reveal','learning-reuse':'emit','learning-extend':'merge','title-arrive':'close'}

def compose()->dict:
    beats={k:round(v*FPS) for k,v in BEATS.items()}
    scenes=[];contract_scenes=[];effects=[]
    for sid,a,b in SECTIONS:
        start,end=round(a*FPS),round(b*FPS);duration=end-start
        captions=[{'startFrame':round(x*FPS)-start,'endFrame':round(y*FPS)-start,'text':text}
                  for x,y,text in CAPTIONS if a<=x<b]
        events=[{'id':k,'frame':v-start} for k,v in beats.items() if start<=v<end]
        scenes.append({'id':sid,'template':'code','keywords':['复利效应','成果复用','种子生长'],
            'durationFrames':duration,'transition':'cut','narrationSegments':[],
            'content':{'title':'让积累生长','entry':f'scenes/{sid}.tsx','props':{
                'beats':beats,'screenSubtitles':captions,'capture':{'mode':'pure-time','timebase':'global','jobs':2}}},
            'events':events})
        shot={'id':sid+'-shot','tier':'A' if sid in ('core','grove','closing') else 'B',
              'window':[0,duration],'core':sid=='core'}
        if sid=='core':
            shot['timeStructure']={
              key:{'window':window,'audience':'跟随主体及它带来的后续变化','visible':visible,
                   'attention':'当前动作主体','toleranceFrames':2,'failure':'种子来源或新增部分作用无法认回'}
              for key,window,visible in [
                ('establish',[0,120],'母株及其种子'),('change',[120,450],'种子脱离落地，新株生长'),
                ('reveal',[450,600],'新株再次结种并释放'),('result',[600,780],'第三株生长，原株保留')]}
        cp={'id':'cp-'+sid,'shotId':shot['id'],'frame':min(duration-1,round(duration*.87)),
            'window':[0,duration],'expected':[{'role':'mother-tree','count':1}] if sid=='core' else [],
            'textPlan':[{'role':'screen-subtitle','text':x['text'],'window':[x['startFrame'],x['endFrame']]} for x in captions],
            'claims':[],'forbidden':['投资收益','年化收益','保证成功'],
            'measurement':{'subtitleRoles':['screen-subtitle'],'thresholdSource':'当前画幅安全区及手机阅读观察，不设注释手机门槛'}}
        if sid=='opening':
            cp['measurement']['allowedOverlaps']=[['opening-seed','mother-tree']]
        if sid=='core':cp['minEventFrames']=2
        if sid=='core':
            cp['measurement']['allowedOverlaps']=[['mother-tree','first-seed'],['child-tree','first-seed'],
                                                   ['child-tree','second-seed'],['third-tree','second-seed']]
        contract_scenes.append({'id':sid,'durationFrames':duration,'shots':[shot],'checkpoints':[cp]})
        effects.extend({'sourceRef':f'assets/media/{SOUNDS[e["id"]]}-v2.wav','sceneId':sid,
                        'eventId':e['id'],'gainDb':-7} for e in events if e['id'] in SOUNDS)
    project={'schemaVersion':1,'id':'compound-connect','type':'general','materials':{'storyboard':'storyboard.json'},
             'output':{'width':1920,'height':1080,'fps':FPS,'audio':'required'},'style':{'id':'dark-proof'}}
    board={'version':8,'schemaVersion':8,'title':'接：让积累生长','fps':FPS,'width':1920,'height':1080,
           'targetSeconds':68,'input':{'kind':'topic','topic':'非金融复利效应：过去的成果参与后续创造，新增成果也成为新的增长来源。原创种子机制寓言与凑十法复用，不承诺现实固定增速。'},
           'scenes':scenes,'soundtrack':{'effects':effects}}
    c={'version':2,'cycleId':'compound-effect-growth-20261104','fps':FPS,'width':1920,'height':1080,
       'reviewPlan':{'basis':'试制完整覆盖母株结种、新株生长与新株再次结种；用户目标优先，方案可经证据调整。',
       'risks':[
        {'id':'growth-appearance','kind':'static-expression','scope':{'checkpointIds':['cp-core']},
         'reason':'outputs/style-reference.md：具体主体、清楚轮廓与新增长来源须先以独立目标验证。',
         'requiredEvidence':['design/keyframes/growth-establish.png','design/keyframes/growth-result.png']},
        {'id':'growth-sequence','kind':'structure-timing','scope':{'checkpointIds':['cp-core']},
         'reason':'先看见种子来源及落地，再生长，再由新增植株结种；禁止字幕解释代替过程。',
         'requiredEvidence':['production/checkpoints/cp-core/window.mp4']},
        {'id':'new-source','kind':'core-event','scope':{'checkpointIds':['cp-core']},
         'reason':'完整试制必须呈现新增部分参与后续创造，可因此退回设计。',
         'requiredEvidence':['production/checkpoints/cp-core/window.mp4']} ]},'scenes':contract_scenes}
    for name,value in [('project.json',project),('storyboard.json',board)]:
        (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    design=ROOT/'DESIGN.md';text=design.read_text(encoding='utf8') if design.exists() else '# 制作设计\n'
    block='```m2v-checkpoints\n'+json.dumps(c,ensure_ascii=False,indent=2)+'\n```'
    text=re.sub(r'```m2v-checkpoints\s*\n.*?```',lambda _:block,text,flags=re.S) if '```m2v-checkpoints' in text else text+'\n'+block+'\n'
    design.write_text(text,encoding='utf8')
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    report={'mode':'effects-only','durationFrames':68*FPS,'beats':beats,'captions':CAPTIONS}
    (out/'screen-timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    result=compose();print(f'已编排 {result["durationFrames"]} 帧；分镜与试制合同已同步')
