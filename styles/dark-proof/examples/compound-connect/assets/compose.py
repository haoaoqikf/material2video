"""《接》的制作源：无旁白、无配乐，以动作和屏幕短句编排事件与观察留白。

运行本文件会重写生成的 storyboard.json/project.json，不覆盖声音媒体。
所有事件、画面 props 与事件音定位均来自这里，避免三份时间表漂移。
"""
from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FPS = 30
MODEL = {'initial': 100, 'rate': .1, 'rounds': 30, 'unit': 10}
SECTIONS = [
    ('question', 0, '重复，就会复利吗？'),
    ('setup', 4, '每轮产出＝当轮投入的10%。'),
    ('take', 10, '产出取走，下一轮仍从100开始。'),
    ('return', 17, '把这10，接回下一轮。'),
    ('again', 24, '110，再产生11，合计121。'),
    ('history', 31, '第10轮、第20轮、第30轮……'),
    ('compare', 41, '同样30轮，400 对 1,745。'),
    ('reason', 48, '接回，每次都带着上一次。'),
    ('close', 56, '让结果，成为下一次的起点。'),
]


def compose() -> dict:
    phases={key:round(seconds*FPS) for key,seconds,_ in SECTIONS}
    total=64*FPS
    phases['end']=total
    events=dict(phases)
    a,b=phases['return'],phases['again']
    events.update({'first-output':phases['setup']+90,'take-finish':phases['take']+132,
                   'return-output':a+90,'return-travel':a+135,'return-merge':b-24,
                   'second-output':b+8,'second-travel':b+20,'second-merge':b+64,
                   'third-output':b+105,'third-travel':b+120,'third-merge':b+164,
                   'curve-arrive':phases['compare']-12,'title-arrive':phases['close']+90})
    roles={'first-output':'emit','take-finish':'land','return-output':'emit',
           'return-travel':'travel','return-merge':'merge','second-output':'emit',
           'second-travel':'travel','second-merge':'merge','third-output':'emit',
           'third-travel':'travel','third-merge':'merge','curve-arrive':'reveal','title-arrive':'close'}
    for n in (5,10,20):
        identity=f'take-round-{n}'
        events[identity]=math.ceil(phases['take']+(n-1)/29*(events['take-finish']-phases['take']))
        roles[identity]='emit'
    captions=[
        (.3,3.9,'重复，就会复利吗？'),
        (4.4,9.8,'每轮产出＝当轮投入的10%。'),
        (10.2,14.3,'产出取走，下一轮仍从100开始。'),
        (14.6,17,'投入100＋已取300＝400。'),
        (17.2,20.1,'另一组，同样从100出发。'),
        (20.3,23.9,'把这10，接回下一轮。'),
        (24.2,27.3,'110，再产生11，合计121。'),
        (27.5,30.9,'新增的部分，也参与下一轮。'),
        (31.2,35,'刚开始，差得不多。'),
        (35.2,40.8,'第10轮、第20轮、第30轮……'),
        (41.3,45,'同样30轮，400 对 1,745。'),
        (45.2,47.9,'接回总量，约为取走的4.36倍。'),
        (48.2,51.8,'取走，每次都从原点出发。'),
        (52,55.8,'接回，每次都带着上一次。'),
        (56.5,64,'让结果，成为下一次的起点。')]
    subtitles=[{'startFrame':round(a*FPS),'endFrame':round(b*FPS),'text':text} for a,b,text in captions]
    project={'schemaVersion':1,'id':'compound-connect','type':'general',
             'materials':{'storyboard':'storyboard.json'},
             'output':{'width':1920,'height':1080,'fps':FPS,'audio':'required'},'style':{'id':'dark-proof'}}
    board={'version':8,'schemaVersion':8,'fps':FPS,'width':1920,'height':1080,'title':'接','targetSeconds':64,
           'input':{'kind':'topic','topic':'理想数学模型：同样100单位，30轮，每轮产出为当轮投入10%；产出取走保存与接回下一轮的总量对照。无旁白无配乐，仅事件音效。'},
           'scenes':[{'id':'compound-connect','template':'code','keywords':['复利','回流','总量对照'],
                      'durationFrames':total,'transition':'cut','narrationSegments':[],
                      'content':{'title':'接','entry':'scenes/compound-connect.tsx',
                                 'props':{'model':MODEL,'phases':phases,'screenSubtitles':subtitles,
                                          'capture':{'mode':'pure-time','jobs':2}}},
                      'events':[{'id':key,'frame':value} for key,value in events.items() if key!='end']}],
           'soundtrack':{'effects':[{'sourceRef':f'assets/media/{role}-v2.wav','sceneId':'compound-connect',
                                    'eventId':event,'gainDb':-12 if event.startswith('take-round') else -5}
                                   for event,role in roles.items()]}}
    for name,value in [('project.json',project),('storyboard.json',board)]:
        (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'mode':'effects-only','durationFrames':total,'phases':phases,'captions':subtitles}
    timing=ROOT/'outputs/screen-timing.json'
    timing.parent.mkdir(parents=True,exist_ok=True)
    timing.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    sync_contract(board,events)
    return report


def sync_contract(board: dict, events: dict) -> None:
    """只同步机器合同；人工导演记录保留。帧数从动作与短句分镜派生。"""
    phases=board['scenes'][0]['content']['props']['phases']
    identities=[x[0] for x in SECTIONS]
    shots=[]; points=[]
    for i,key in enumerate(identities):
        a=phases[key];b=phases[identities[i+1]] if i+1<len(identities) else phases['end']
        shot={'id':key,'tier':'A' if key in ('question','return','again','history','compare','close') else 'B','window':[a,b]}
        at=(a+b)//2
        if key=='return':
            at=events['return-merge']+3
            def part(window,visible):
                return {'window':window,'audience':'观看对象变化，分辨其先后',
                        'visible':visible,'attention':'投入簇与返回资源','toleranceFrames':3,
                        'failure':'先更新数字或资源包无法认回'}
            shot['timeStructure']={'establish':part([a,events['return-output']],'100与两组身份'),
                                   'change':part([events['return-output'],events['return-merge']],'产出从出口返回'),
                                   'result':part([events['return-merge'],b],'110与新增圆片落定')}
        if key=='again':
            at=min(b-2,events['third-merge']+3)
            shot['timeStructure']={
                'establish':part([a,events['second-output']],'110成为下一轮起点'),
                'change':part([events['second-output'],events['third-merge']],'产出11并入为121，再产出12.1'),
                'result':part([events['third-merge'],b],'133.1落定，新增部分已经参与产出')}
        cp={'id':'cp-'+key,'shotId':key,'frame':at,'window':[a,b],
            'expected':[],'textPlan':[],'claims':[],'forbidden':['投资建议','保证收益'],
            'measurement':{'allowedOverlaps':[['return-packet','active-resource'],['return-packet','active-value'],['output-resource','saved-resource']],
                           'thresholdSource':'DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。',
                           'bodyRoles':['active-value','output-value'],'minFont393':12,'maxTextCharacters':30,
                           'subtitleRoles':['screen-subtitle']}}
        cp['textPlan']=[{'role':'screen-subtitle','text':x['text'],
                         'window':[max(a,x['startFrame']),min(b,x['endFrame'])]}
                        for x in board['scenes'][0]['content']['props']['screenSubtitles']
                        if x['startFrame']<b and x['endFrame']>a]
        if key=='return':
            cp.update(minEventFrames=12,expected=[{'role':'active-resource','count':11}],
                      claims=[{'id':'active-first','value':110,'unit':'units','basis':'100+100×10%'}],
                      statePlan=[{'window':[a,events['return-merge']],'expected':[{'role':'active-resource','count':10}]},
                                 {'window':[events['return-merge'],b],'expected':[{'role':'active-resource','count':11}]}])
        elif key=='again':
            cp['minEventFrames']=8
            cp['claims']=[{'id':'active-second','value':121,'unit':'units','basis':'110+110×10%'}]
        elif key=='compare':
            cp['claims']=[{'id':'withdraw-total','value':400,'unit':'units','basis':'100+30×10'},
                          {'id':'reinvest-total','value':1744.94,'unit':'units','basis':'100×1.1^30；两位小数'}]
        shots.append(shot);points.append(cp)
    c={'version':2,'cycleId':'compound-connect-return-20261104','fps':FPS,'width':1920,'height':1080,
       'reviewPlan':{'basis':'用户采用的单一回流实验；强轮廓与局部光、返回因果与先后顺序须在扩展前独立观察。',
                     'risks':[
                         {'id':'return-appearance','kind':'static-expression','scope':{'checkpointIds':['cp-return']},
                          'reason':'关键采用项见outputs/style-reference.md：大数字、清楚轮廓、局部自发光及主体层级。',
                          'requiredEvidence':['design/keyframes/return-establish.png','design/keyframes/return-result.png']},
                         {'id':'return-sequence','kind':'structure-timing','scope':{'checkpointIds':['cp-return','cp-again']},
                          'reason':'必须先有产出，再返回并入，下一轮才开始；组别交接须有前后文。',
                          'requiredEvidence':['production/checkpoints/cp-return/window.mp4','production/checkpoints/cp-again/window.mp4']},
                         {'id':'same-packet','kind':'core-event','scope':{'checkpointIds':['cp-return','cp-again']},
                          'reason':'认回产出包，110和121有可见资源来源，光效不能代替数量关系。',
                          'requiredEvidence':['production/checkpoints/cp-return/window.mp4','production/checkpoints/cp-again/window.mp4']} ]},
       'scenes':[{'id':'compound-connect','durationFrames':phases['end'],'shots':shots,'checkpoints':points}]}
    target=ROOT/'DESIGN.md'
    body=target.read_text(encoding='utf-8')
    block='```m2v-checkpoints\n'+json.dumps(c,ensure_ascii=False,indent=2)+'\n```'
    body=re.sub(r'```m2v-checkpoints\s*\n.*?```',lambda _:block,body,flags=re.S)
    if '```m2v-checkpoints' not in body:body+='\n\n'+block+'\n'
    target.write_text(body,encoding='utf-8')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    print(json.dumps(compose(), ensure_ascii=False, indent=2))
