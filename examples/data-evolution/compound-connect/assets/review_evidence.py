"""从已生成的过程片段或成片抽取有序证据；不另行渲染画面。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe
import argparse,json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'

def collect(label,source,offset,duration,events,keys,step=3):
    target=OUT/'inspection-v4'/label;target.mkdir(parents=True,exist_ok=True)
    selected=set(range(0,duration,step))|{duration-1}
    for n in events:
        selected.update(n+k for k in [-2,-1,0,1,2,3,6,9,12,18] if 0<=n+k<duration)
    selected.update(keys);selected=sorted(selected)
    expression='+'.join(f'eq(n,{n})' for n in selected).replace(',',r'\,')
    subprocess.run([get_ffmpeg_exe(),'-v','error','-y','-i',str(source),'-vf',f'select={expression}','-fps_mode','vfr','-q:v','2',str(target/'raw-%04d.jpg')],check=True)
    font=ImageFont.truetype(str(ROOT.parents[3]/'fonts/files/Inter-Variable.ttf'),20)
    generated=[]
    for page,start in enumerate(range(0,len(selected),16)):
        sheet=Image.new('RGB',(1920,1184),'#151515');draw=ImageDraw.Draw(sheet)
        for slot,ix in enumerate(range(start,min(start+16,len(selected)))):
            n=selected[ix]
            with Image.open(target/f'raw-{ix+1:04d}.jpg') as frame:
                x=slot%4*480;y=slot//4*296
                sheet.paste(frame.resize((480,270),Image.Resampling.LANCZOS),(x,y+26))
                draw.text((x+6,y+2),f'local f{n:04d}  |  global {(offset+n)/30:06.3f}s',font=font,fill='white')
        p=target/f'sequence-{page+1:02d}.jpg';sheet.save(p,quality=93);generated.append(p.relative_to(OUT).as_posix())
    for n in keys:
        ix=selected.index(n)
        with Image.open(target/f'raw-{ix+1:04d}.jpg') as frame:
            for width in [1920,393]:
                p=target/f'key-{n:04d}-{width}.png';frame.resize((width,round(width*1080/1920)),Image.Resampling.LANCZOS).save(p);generated.append(p.relative_to(OUT).as_posix())
    index={'source':source.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'fps':30,'startFrameGlobal':offset,'durationFrames':duration,'sampleFrames':selected,'files':generated}
    (target/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8');print(label,len(selected),'ordered frames,',len(generated),'review files',flush=True)
    return generated

def main():
    parser=argparse.ArgumentParser();parser.add_argument('label',choices=['hook','proof','resolution','final']);a=parser.parse_args()
    board=json.loads((ROOT/'storyboard.json').read_text(encoding='utf-8'))
    if a.label=='final':
        duration=sum(s['durationFrames'] for s in board['scenes']);events=[];offset=0
        for s in board['scenes']:
            events.extend(offset+v['frame'] for v in s['events']);offset+=s['durationFrames']
        collect('final',OUT/'video.mp4',0,duration,events,[30,76,135,285,306,312,314,318,329,330,350,438,650,672,816,834,861,937,990,1005,1140,1199])
    else:
        offset=0
        for s in board['scenes']:
            if s['id']==a.label:break
            offset+=s['durationFrames']
        keys={'hook':[30,76,84,135,205,250,285,318,324,329],'proof':[30,76,120,160,184,250,320,334,359,390,438,486,518,539],'resolution':[0,30,65,120,126,170,192,240,329]}
        collect(a.label,OUT/f'production/checkpoints/cp-{a.label}/window.mp4',offset,s['durationFrames'],[v['frame'] for v in s['events']],keys[a.label])
if __name__=='__main__':main()
