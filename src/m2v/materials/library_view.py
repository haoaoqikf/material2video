"""显式多库的原生本地浏览；只读源库，仅在指定输出目录派生缩略图与页面。"""
from __future__ import annotations

import base64
from contextlib import ExitStack
import hashlib
import html
import json
from pathlib import Path

from PIL import Image

from .contracts import Artifact, fingerprint
from .errors import MaterialError
from .indexing import _find_index
from .organization import list_media
from .paths import no_links
from .sampling import frame_time, spread
from .store import MaterialStore

SCRIPT = '''const cards=[...document.querySelectorAll('.card')];
const q=document.querySelector('#q'),tag=document.querySelector('#tag'),collection=document.querySelector('#collection'),fav=document.querySelector('#favorite');
function filter(){let count=0;for(const card of cards){const show=card.dataset.search.includes(q.value.toLocaleLowerCase())&&(!tag.value||JSON.parse(card.dataset.tags).includes(tag.value))&&(!collection.value||JSON.parse(card.dataset.collections).includes(collection.value))&&(!fav.checked||card.dataset.favorite==='1');card.hidden=!show;if(show)count++;}document.querySelector('#count').textContent=count+' 件素材';}
for(const element of [q,tag,collection,fav])element.addEventListener('input',filter);filter();'''


def _thumbnail(store, item, directory, identity):
    artifact = Artifact.model_validate(item['artifact'])
    if item['kind'] == 'video':
        media = store.get(item['mediaId'], kind='material.media')
        index = _find_index(store, media, 'frames')
        records = [r for r in store.records(index.id) if r.frame] if index else []
        if not records:
            return None
        artifact = spread(records, 1, time=frame_time)[0].frame
    if item['kind'] == 'audio':
        return None
    source = store.verify_artifact(artifact)
    name = f'{identity}-{artifact.sha256[:24]}.jpg'
    target = no_links(directory / name)
    if not target.is_file():
        with Image.open(source) as picture:
            picture = picture.convert('RGB')
            picture.thumbnail((480, 270))
            picture.save(target, format='JPEG', quality=85)
    return 'thumbnails/' + name


def browse(workspaces, out: Path, *, tags=(), collection=None, favorites=False, query=None, limit=200):
    roots = list(dict.fromkeys(no_links(Path(path)) for path in workspaces))
    if not roots or len(roots) > 16:
        raise MaterialError('invalid-request', '浏览须显式选择 1..16 个素材库', stage='library')
    for root in roots:
        if not (root / 'catalog.sqlite3').is_file():
            raise MaterialError('not-found', '显式浏览库不存在', stage='library')
    directory = no_links(Path(out))
    if any(directory == root or directory.is_relative_to(root / 'objects') or root.is_relative_to(directory) for root in roots):
        raise MaterialError('invalid-request', '浏览输出不能覆盖库根或内容对象', stage='library')
    directory.mkdir(parents=True, exist_ok=True)
    thumbnails = no_links(directory / 'thumbnails')
    thumbnails.mkdir(exist_ok=True)
    entries, warnings, partial = [], [], False
    with ExitStack() as stack:
        stores = [(root, stack.enter_context(MaterialStore(root, readonly=True))) for root in roots]
        for root, store in stores:
            result = list_media(store, tags=tags, collection=collection, favorites=favorites, query=query, limit=limit)
            partial = partial or result['hasMore']
            identity = fingerprint({'workspace': str(root)})[:12]
            for item in result['items']:
                entry = {**item, 'workspace': str(root), 'libraryId': identity, 'thumbnail': None}
                try:
                    entry['thumbnail'] = _thumbnail(store, item, thumbnails, identity)
                except (OSError, MaterialError, Image.DecompressionBombError):
                    warnings.append({'workspace': str(root), 'mediaId': item['mediaId'], 'reason': 'thumbnail-unavailable'})
                entries.append(entry)
    _write_page(directory / 'index.html', entries, partial)
    manifest = {'items': entries, 'truncated': partial, 'warnings': warnings,
                'workspaces': [str(root) for root in roots], 'html': str(directory / 'index.html')}
    (directory / 'index.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def _write_page(path, entries, truncated):
    escape = lambda value: html.escape(str(value), quote=True)
    cards = []
    for item in entries:
        search = ' '.join([item['title'], item['note'], item['workspace'], *item['tags'], *item['collections']]).casefold()
        image = f'<img loading="lazy" src="{escape(item["thumbnail"])}" alt="素材缩略图">' if item['thumbnail'] else '<div class="placeholder">没有可用缩略图</div>'
        source = (f'<a href="{escape(item["sourceUrl"])}" target="_blank" rel="noreferrer noopener">原始来源</a>'
                  if item['sourceUrl'] else '本地来源')
        duration = f'{item["durationUs"]/1e6:.2f} 秒' if item['durationUs'] is not None else '图片'
        cards.append(f'''<article class="card" data-search="{escape(search)}" data-tags="{escape(json.dumps(item['tags'],ensure_ascii=False))}" data-collections="{escape(json.dumps(item['collections'],ensure_ascii=False))}" data-favorite="{int(item['favorite'])}">
{image}<div class="body"><h2>{'★ ' if item['favorite'] else ''}{escape(item['title'])}</h2>
<p>{escape(item['kind'])} · {escape(item['width'])} × {escape(item['height'])} · {escape(duration)}</p>
<p class="tags">{escape(' · '.join(item['tags']))}</p><p>集合：{escape('、'.join(item['collections']) or '未分组')}</p>
<p>{escape(item['note'])}</p><p>{source} · {escape(item['author'])} · {escape(item['license'])}</p>
<details><summary>所属库与素材 ID</summary><pre>{escape(item['workspace'])}\n{escape(item['mediaId'])}</pre></details></div></article>''')
    tags = sorted({tag for item in entries for tag in item['tags']})
    collections = sorted({group for item in entries for group in item['collections']})
    options = lambda values: ''.join(f'<option value="{escape(value)}">{escape(value)}</option>' for value in values)
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>素材库</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#111416;color:#e8edeb;font:15px/1.6 system-ui,sans-serif}}header{{padding:30px 4vw;background:#19201e}}h1{{margin:0;font-size:27px}}.toolbar{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}input,select{{font:inherit;border:1px solid #46524b;background:#111916;color:inherit;padding:8px;border-radius:6px}}#q{{min-width:240px;flex:1}}main{{padding:26px 4vw;display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px}}.card{{border:1px solid #35413a;border-radius:10px;overflow:hidden;background:#1a211e}}.card[hidden]{{display:none}}img,.placeholder{{width:100%;height:210px;object-fit:contain;background:#0c100e}}.placeholder{{display:grid;place-items:center;color:#a4b0a9}}.body{{padding:16px}}h2{{font-size:16px;margin:0;overflow-wrap:anywhere}}p{{margin:8px 0;color:#b9c5bd;overflow-wrap:anywhere}}a{{color:#9ed0b1}}.tags{{color:#c3e2c9}}pre{{font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere}}details{{color:#a4b0a9}}footer{{padding:20px 4vw;color:#a4b0a9}}</style></head><body>
<header><h1>素材库</h1><p>浏览已收集素材，按主题筛选并保留来源。</p><div class="toolbar"><input id="q" aria-label="搜索素材" placeholder="搜索标题、标签或备注"><select id="tag" aria-label="标签"><option value="">全部标签</option>{options(tags)}</select><select id="collection" aria-label="集合"><option value="">全部集合</option>{options(collections)}</select><label><input id="favorite" type="checkbox"> 只看收藏</label></div><span id="count"></span></header>
<main>{''.join(cards)}</main><footer>{'当前达到显示预算，使用命令筛选或调整 limit 查看其他素材。' if truncated else '已显示本轮显式选择的素材。'} 组织信息与相似提示不替代来源核实。</footer><script>{SCRIPT}</script></body></html>'''
    path.write_text(document, encoding='utf-8')
