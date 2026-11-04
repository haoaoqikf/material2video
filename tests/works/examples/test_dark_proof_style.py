"""正式暗场论证风格包：清单、组件契约、指纹与《接》示例。"""
from __future__ import annotations

import json
import importlib.util
import re
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


def test_seed_sources_and_growth_follow_visible_event_order():
    """保护来源、接触和后续生产边界；不启动浏览器或生成媒体。"""
    if shutil.which('node') is None:
        pytest.skip('需要Node.js')
    script = r"""
      const assert = require('node:assert/strict');
      const fs = require('node:fs');
      const code = require('esbuild').buildSync({entryPoints:[process.argv[1]],bundle:true,
        alias:{'m2v/code-scene':process.argv[3]},platform:'node',format:'cjs',write:false}).outputFiles[0].text;
      const mod={exports:{}}; new Function('module','exports',code)(mod,mod.exports);
      const {groveState,flight,podAt,MOTHER,CHILD,THIRD}=mod.exports;
      const board=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
      const b=board.scenes[0].content.props.beats;
      const near=(a,z)=>assert.ok(Math.abs(a-z)<1e-8, `${a} != ${z}`);
      for (const [prefix,from,to,grow,ready] of [
        ['first',MOTHER,CHILD,'child-grow','child-ready'],
        ['second',CHILD,THIRD,'third-grow','third-ready']]) {
        assert.ok(b[`${prefix}-release`]<b[`${prefix}-land`]);
        assert.ok(b[`${prefix}-land`]<b[grow] && b[grow]<b[ready]);
        const a=flight(b[`${prefix}-release`],b[`${prefix}-release`],b[`${prefix}-land`],podAt(from),to);
        const z=flight(b[`${prefix}-land`],b[`${prefix}-release`],b[`${prefix}-land`],podAt(from),to);
        near(a.x,podAt(from).x);near(a.y,podAt(from).y);near(z.x,to.x);near(z.y,to.y);
      }
      assert.ok(b['child-ready']<b['child-fruit'] && b['child-fruit']<b['second-release']);
      assert.equal(groveState(b['child-grow'],b).child,0);
      assert.equal(groveState(b['child-ready'],b).child,1);
      assert.equal(groveState(b['child-fruit']-1,b).childProductive,false);
      assert.equal(groveState(b['child-fruit'],b).childProductive,true);
      const state=groveState(900,b);groveState(1600,b);
      assert.deepEqual(groveState(900,b),state);
    """
    result=subprocess.run(['node','-e',script,str(EXAMPLE/'scenes/model.ts'),str(EXAMPLE/'storyboard.json'),
                           str(ROOT/'web/src/code-scene/motion.ts')],
                          cwd=ROOT/'web',capture_output=True,text=True,encoding='utf-8',check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_example_media_recipe_is_complete():
    recipe = json.loads((EXAMPLE / "assets" / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["schemaVersion"] == 1
    for item in recipe["assets"]:
        assert item["transform"] == "generate"
        assert item["sampleRateHz"] == 24000 and item["channels"] == 1
        assert item["license"] == "CC0-1.0"
        assert re.fullmatch(r"[0-9a-f]{64}", item["expectedSha256"])


def test_composer_creates_a_fresh_work_and_keeps_event_contract_in_sync(tmp_path, monkeypatch):
    spec=importlib.util.spec_from_file_location('compound_compose',EXAMPLE/'assets/compose.py')
    composer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composer)
    monkeypatch.setattr(composer,'ROOT',tmp_path)
    design=tmp_path/'DESIGN.md'
    design.write_text('# 临时制作源\n',encoding='utf-8')
    composer.compose()
    board=json.loads((tmp_path/'storyboard.json').read_text(encoding='utf-8'))
    contract=json.loads(design.read_text(encoding='utf-8').split('```m2v-checkpoints\n')[1].split('```')[0])
    scene=board['scenes'][0]
    events={(s['id'],e['id']) for s in board['scenes'] for e in s['events']}
    assert (tmp_path/'outputs/screen-timing.json').is_file()
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
def test_example_scene_builds_with_the_package(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(EXAMPLE, project)
    work = tmp_path / "work"
    work.mkdir()
    inputs = build_scene(EXAMPLE, board["scenes"][0], work)
    assert inputs["style"] == styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()
