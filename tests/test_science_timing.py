from types import SimpleNamespace
import a2v.types.article.animation_review as ar
import a2v.engine.beats as beats
import a2v.types.article.cli as cli
from test_animation_review import _scene, SPANS, SEGMENT_TEXTS

def test_a4_pause_windows_contain_only_their_spoken_cues():
    scene = _scene(resolved=True)
    for segment in scene['narrationSegments']: segment['speech'] = {'pauseBeforeMs': 100, 'pauseAfterMs': 100}
    cues = [{'start': start/30 + .1, 'end': end/30 - .1, 'text': text} for (_,start,end),text in zip(SPANS,SEGMENT_TEXTS)]
    timeline = beats.BeatTimeline.from_json(scene['resolvedBeats'])
    assert ar._a4_scene(scene, cues, timeline, 30, 120) == []
    cues[0]['end'] = 1.2
    assert ar._a4_scene(scene, cues, timeline, 30, 120)

def test_review_frame_range_uses_extended_media_timeline(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, '_force_utf8_output', lambda: None)
    monkeypatch.setattr(cli, '_validated_storyboard', lambda *args: SimpleNamespace(total_frames=90))
    monkeypatch.setattr(cli, '_article_for', lambda *args, **kwargs: SimpleNamespace(preview_dir=tmp_path, workspace_root=tmp_path))
    monkeypatch.setattr(cli, 'load_media', lambda *args: SimpleNamespace(storyboard=SimpleNamespace(total_frames=120)))
    monkeypatch.setattr(cli, '_storyboard_url', lambda *args: 'local')
    monkeypatch.setattr(cli, '_resolve_render_output', lambda *args: tmp_path / 'review.mp4')
    captured = {}
    def render(**kwargs):
        captured.update(kwargs); return SimpleNamespace(summary=lambda:'ok')
    monkeypatch.setattr(cli, 'render_with_remotion', render)
    assert cli.main_render(['--storyboard','source.json','--media','media.json','--purpose','review','--frame-range','0-119','--out',str(tmp_path/'review.mp4')]) == 0
    assert captured['frame_range'] == (0,119)
