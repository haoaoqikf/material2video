"""正式暗场论证风格包：清单、组件契约、指纹与R5规范示例。"""
from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.types.general import explainer
from m2v.types.general.code_scenes import build_scene

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "styles" / "dark-proof"
EXAMPLE = PACKAGE / "examples" / "compound-connect"
LUCK_EXAMPLE = PACKAGE / "examples" / "luck-on-stage"


def test_narration_is_optional():
    from m2v.core.styles import check_requirements
    package = styles.load_style("dark-proof")
    check_requirements(package, has_narration=False)
    check_requirements(package, has_narration=True)


def test_shipped_example_is_an_effects_only_v8_work():
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    assert project["type"] == "general"
    assert project["style"] == {"id": "dark-proof"}
    assert (project["output"]["width"], project["output"]["height"], project["output"]["fps"]) == (1920, 1080, 30)
    board = explainer.load(EXAMPLE, project)
    explainer.validate(board, EXAMPLE, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8
    assert not any(scene['narrationSegments'] for scene in board['scenes'])
    assert 'music' not in board.get('soundtrack', {})
    assert 'tts' not in project
    assert board['soundtrack']['effects']


def test_second_example_is_independent_effects_only_v8_work():
    project = json.loads((LUCK_EXAMPLE / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(LUCK_EXAMPLE, project)
    explainer.validate(board, LUCK_EXAMPLE, project)
    assert project["style"] == {"id": "dark-proof"}
    assert (project["output"]["width"], project["output"]["height"], project["output"]["fps"]) == (1920, 1080, 30)
    assert board["version"] == board["schemaVersion"] == 8
    assert sum(scene["durationFrames"] for scene in board["scenes"]) == 1350
    assert not any(scene["narrationSegments"] for scene in board["scenes"])
    assert "music" not in board.get("soundtrack", {})
    assert board["soundtrack"]["effects"]


def test_model_recurs_and_coordinates_are_monotonic():
    """核对递推、增量、同起点及乱序求值，不镜像具体分镜参数。"""
    if shutil.which('node') is None:
        pytest.skip('需要Node.js')
    script = r"""
      const assert=require('node:assert/strict');
      const code=require('esbuild').buildSync({entryPoints:[process.argv[1]],bundle:true,
        platform:'node',format:'cjs',write:false}).outputFiles[0].text;
      const mod={exports:{}};new Function('module','exports',code)(mod,mod.exports);
      const {MODEL,compounded,constant,increment,chartPoint}=mod.exports;
      const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
      near(compounded(0),constant(0));near(compounded(1),constant(1));
      const saved=compounded(7);compounded(MODEL.rounds);near(compounded(7),saved);
      for(let n=1;n<=MODEL.rounds;n++){
        near(compounded(n),compounded(n-1)+increment(n));
        near(increment(n),compounded(n-1)*MODEL.rate);
        near(constant(n)-constant(n-1),MODEL.initial*MODEL.rate);
        assert.ok(compounded(n)>=constant(n)-1e-8);
        const a=chartPoint(n-1,compounded(n-1)),b=chartPoint(n,compounded(n));
        assert.ok(b[0]>a[0] && b[1]<a[1]);
      }
    """
    result=subprocess.run(['node','-e',script,str(EXAMPLE/'scenes/model.ts')],
                          cwd=ROOT/'web',capture_output=True,text=True,encoding='utf-8')
    assert result.returncode == 0, result.stdout+result.stderr


def test_example_edits_do_not_change_fingerprint_but_guide_edits_do(tmp_path, monkeypatch):
    package=tmp_path/'dark-proof'
    shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('examples'))
    monkeypatch.setattr(styles,'STYLES_ROOT',tmp_path)
    before=styles.load_style('dark-proof')['identity']['fingerprint']
    example=package/'examples/compound-connect';example.mkdir(parents=True)
    (example/'CASE_STUDY.md').write_text('复盘',encoding='utf-8')
    assert styles.load_style('dark-proof')['identity']['fingerprint']==before
    (package/'GUIDE.md').write_text('修改指南',encoding='utf-8')
    assert styles.load_style('dark-proof')['identity']['fingerprint']!=before


def load_fetch(example: Path):
    spec=importlib.util.spec_from_file_location(f'{example.name}_fetch',example/'assets/fetch.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


@pytest.mark.media
@pytest.mark.parametrize('example', [EXAMPLE, LUCK_EXAMPLE], ids=['compound', 'luck'])
def test_sound_restore_matches_checks_and_refuses_drift(tmp_path, example):
    fetch=load_fetch(example);assets=tmp_path/'assets';assets.mkdir()
    for name in ['sound-recipe.json','sound-checks.json']:
        shutil.copy2(example/'assets'/name,assets/name)
    fetch.restore(tmp_path)
    record=assets/'sound-sources.json';before=record.read_bytes()
    checks=json.loads((assets/'sound-checks.json').read_text(encoding='utf-8'))
    registered=json.loads(before)
    assert {a['id']:a['sha256'] for a in registered['assets']}=={a['id']:a['sha256'] for a in checks['assets']}
    fetch.restore(tmp_path);assert record.read_bytes()==before
    damaged=tmp_path/registered['assets'][0]['path'];damaged.write_bytes(b'damaged')
    with pytest.raises(ValueError,match='拒绝覆盖'):
        fetch.restore(tmp_path)
    assert damaged.read_bytes()==b'damaged' and record.read_bytes()==before
    recipe=json.loads((assets/'sound-recipe.json').read_text(encoding='utf-8'))
    recipe['assets'][0]['synthesis']['seed']+=1
    (assets/'sound-recipe.json').write_text(json.dumps(recipe),encoding='utf-8')
    with pytest.raises(ValueError,match='恢复摘要或规格不符'):
        fetch.restore(tmp_path)
    assert record.read_bytes()==before


def test_composer_creates_a_fresh_work_and_keeps_event_contract_in_sync(tmp_path, monkeypatch):
    spec=importlib.util.spec_from_file_location('compound_compose',EXAMPLE/'assets/compose.py')
    composer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composer)
    monkeypatch.setattr(composer,'ROOT',tmp_path)
    design=tmp_path/'DESIGN.md'
    design.write_text('# 临时制作源\n\n```m2v-checkpoints\n{}\n```\n',encoding='utf-8')
    composer.compose()
    board=json.loads((tmp_path/'storyboard.json').read_text(encoding='utf-8'))
    contract=json.loads(design.read_text(encoding='utf-8').split('```m2v-checkpoints\n')[1].split('```')[0])
    scene=board['scenes'][0]
    events={(s['id'],e['id']) for s in board['scenes'] for e in s['events']}
    assert contract['scenes'][0]['durationFrames']==scene['durationFrames']
    assert all((e['sceneId'],e['eventId']) in events for e in board['soundtrack']['effects'])
    assert all(e['frame'] < s['durationFrames'] for s in board['scenes'] for e in s['events'])
    assert {s['id']:s['durationFrames'] for s in board['scenes']} == {s['id']:s['durationFrames'] for s in contract['scenes']}
    before={p.name:p.read_bytes() for p in tmp_path.glob('*.json')}
    contract_before=design.read_bytes()
    composer.compose()
    assert {p.name:p.read_bytes() for p in tmp_path.glob('*.json')}==before
    assert design.read_bytes()==contract_before


@pytest.mark.slow
@pytest.mark.parametrize('scene_index',[0,1,2])
def test_example_scene_builds_with_the_package(tmp_path,scene_index):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(EXAMPLE, project)
    work = tmp_path / "work"
    work.mkdir()
    inputs = build_scene(EXAMPLE, board["scenes"][scene_index], work)
    assert inputs["style"] == styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()
