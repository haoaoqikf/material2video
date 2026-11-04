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


def test_reinvestment_preserves_resources_across_merge_boundaries():
    """保护两组核算和在途包→投入的边界；不启动浏览器或生成媒体。"""
    if shutil.which('node') is None:
        pytest.skip('需要Node.js')
    script = r"""
      const assert = require('node:assert/strict');
      const fs = require('node:fs');
      const code = require('esbuild').buildSync({entryPoints:[process.argv[1]],bundle:true,
        platform:'node',format:'cjs',write:false}).outputFiles[0].text;
      const mod={exports:{}}; new Function('module','exports',code)(mod,mod.exports);
      const {ledger,returnState,tokenPosition}=mod.exports;
      const board=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
      const scene=board.scenes[0], model=scene.content.props.model;
      const events=Object.fromEntries(scene.events.map(x=>[x.id,x.frame]));
      const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8, `${a} != ${b}`);
      near(ledger(model,0,true).total,100);
      near(ledger(model,30,false).active,100);
      near(ledger(model,30,false).saved,300);
      near(ledger(model,30,false).total,400);
      near(ledger(model,30,true).total,1744.9402268886407);
      near(ledger(model,-2,true).total,100);
      near(ledger(model,40,true).total,ledger(model,30,true).total);
      for (const id of ['return','second','third']) {
        const end=events[`${id}-merge`];
        const before=returnState(end-1,events,model),after=returnState(end,events,model);
        assert.ok(before.packet); assert.equal(after.packet,null);
        near(before.active+before.packet.value,after.active);
        assert.equal(after.round,before.round+1);
        const destination=tokenPosition(Math.floor(before.active/model.unit));
        assert.deepEqual(before.packet.path.at(-1),destination);
      }
      console.log('ledger, saved resources, fractional output and merge boundaries: passed');
    """
    result=subprocess.run(['node','-e',script,str(EXAMPLE/'scenes/model.ts'),str(EXAMPLE/'storyboard.json')],
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
    events={e['id']:e['frame'] for e in scene['events']}
    assert (tmp_path/'outputs/screen-timing.json').is_file()
    assert contract['scenes'][0]['durationFrames']==scene['durationFrames']
    assert all(e['eventId'] in events for e in board['soundtrack']['effects'])
    assert events['return-merge']<events['second-output']<events['second-merge']
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
