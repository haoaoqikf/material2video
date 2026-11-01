"""金融计划：波动节奏、锚点校验与显式迁移。"""
from __future__ import annotations

import json
from datetime import date

import pytest

from m2v.types.financial import financial, materials, plan
from m2v.core.errors import M2VError
from m2v.types.financial import commands as financial_video
from helpers.financial import edit, project



def test_explicit_migration_preserves_daily_closes_sources_and_backups(tmp_path):
    root = project(tmp_path)
    original = json.loads((root / "prices.json").read_text(encoding="utf-8"))
    old = {**original, "schemaVersion": 2, "points": [{**point, "open": point["close"], "high": point["close"] + 1, "low": point["close"] - 1} for point in original["points"]]}
    (root / "prices.json").write_text(json.dumps(old), encoding="utf-8")
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=2, chartType="candlestick"))
    (root / "events.json").write_text(json.dumps({"selected": [{"title": "旧事件"}]}), encoding="utf-8")
    with pytest.raises(M2VError, match="migrate-line"):
        financial.load_project(root)
    backup = financial.migrate_line(root, duration=15)
    assert json.loads((backup / "prices.json").read_text(encoding="utf-8")) == old
    assert financial.load_project(root)["prices"] == original
    assert not (root / "events.json").exists()
    assert (backup / "events.json").exists()
    with pytest.raises(M2VError, match="计划已是 v8"):
        financial.migrate_line(root)




def test_v3_plan_migrates_without_changing_prices_and_discards_event_material(tmp_path):
    root = project(tmp_path)
    original_prices = (root / "prices.json").read_bytes()
    (root / "events.json").write_text("legacy event material", encoding="utf-8")
    (root / "outputs").mkdir()
    (root / "outputs" / "legibility-review.json").write_text("stale", encoding="utf-8")
    (root / "outputs" / "previews").mkdir()
    (root / "outputs" / "previews" / "preview-record.json").write_text("stale", encoding="utf-8")
    edit(root, "animation-plan.json", lambda plan: plan.update(schemaVersion=3, eventDisplays=[{"eventId": "e1", "frames": [100, 190]}]))

    backup = financial.migrate_line(root, duration=15)

    assert (root / "prices.json").read_bytes() == original_prices
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8
    assert not (root / "events.json").exists()
    assert not (root / "outputs" / "legibility-review.json").exists()
    assert not (root / "outputs" / "previews" / "preview-record.json").exists()
    assert (backup / "events.json").exists()
    assert (backup / "animation-plan.json").exists()




def test_migration_rejects_bad_data_before_writing(tmp_path):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    edit(root, "prices.json", lambda data: data["points"][0].update(close=0))
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    with pytest.raises(M2VError, match="有限正数"):
        financial.migrate_line(root)
    assert {name: (root / name).read_bytes() for name in financial.MATERIALS} == originals




def test_plan_uses_short_holds_and_uniform_60_second_default():
    request = {"displayRange": ["1999-01-22", "2026-10-08"]}
    plan = financial.build_line_plan(request)
    assert plan["schemaVersion"] == 8
    assert plan["durationSeconds"] == 60
    assert plan["axis"]["dateScale"] == "staged-expanding"
    assert [segment["kind"] for segment in plan["segments"]] == ["opening", "advance", "ending"]
    assert [segment["frames"] for segment in plan["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    assert "eventDisplays" not in plan
    dates = [financial.frame_date(plan, frame) for frame in range(1800)]
    assert dates == sorted(dates)
    assert dates[-1].isoformat() == "2026-10-08"
    with pytest.raises(M2VError, match="至少需要 4 秒"):
        financial.build_line_plan(request, duration=3)
    under_20 = financial.build_line_plan({"displayRange": ["2000-02-29", "2020-02-29"]})
    over_20 = financial.build_line_plan({"displayRange": ["2000-02-29", "2020-03-01"]})
    assert under_20["durationSeconds"] == 60
    assert [part["frames"] for part in under_20["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    assert over_20["durationSeconds"] == 60
    assert [part["frames"] for part in over_20["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    explicit = financial.build_line_plan(request, duration=90)
    assert explicit["durationSeconds"] == 90
    assert [part["frames"] for part in explicit["segments"]] == [[0, 30], [30, 2640], [2640, 2700]]
    four_seconds = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-02"]}, duration=4)
    assert [part["frames"] for part in four_seconds["segments"]] == [[0, 30], [30, 60], [60, 120]]
    with pytest.raises(M2VError, match="至少需要 4 秒"):
        financial.build_line_plan(request, duration=3)
    single_day = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-01"]}, duration=4)
    assert all(financial.frame_date(single_day, frame).isoformat() == "2020-01-01" for frame in range(60))




@pytest.mark.parametrize("values", [[100, 100, 100, 100], [100, 101, 400, 402], [400, 399, 100, 99]])
def test_monthly_pacing_is_monotone_bounded_and_weights_both_directions(values):
    request = {"displayRange": ["2020-01-01", "2020-03-01"], "investment": {"year": 2020, "principal": 100_000}}
    points = [{"date": day, "close": value} for day, value in zip(
        ["2020-01-01", "2020-01-31", "2020-02-02", "2020-03-01"], values)]
    plan = financial.build_line_plan(request, prices={"points": points})
    materials._validate_plan(plan, request, {"points": points})
    dates = [financial.frame_date(plan, frame) for frame in range(1800)]
    assert dates == sorted(dates)
    assert dates[30] == date(2020, 1, 1) and dates[1739] == date(2020, 3, 1)
    for frame in reversed(range(len(dates))):
        assert financial.frame_date(plan, frame) == dates[frame]
    anchors = plan["pacing"]["anchors"]
    if len(set(values)) == 1:
        assert len(anchors) == 2
    else:
        feb = anchors[1]
        assert feb["date"] == "2020-02-01"
        assert feb["frame"] - 30 < 1739 - feb["frame"]




def test_existing_v8_plan_keeps_its_saved_hold_durations(tmp_path):
    root = project(tmp_path)
    def use_previous_v8_timing(plan):
        plan["durationSeconds"] = 60
        plan["segments"] = [
            {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
            {"frames": [90, 1620], "dates": ["2020-01-01", "2020-01-03"], "kind": "advance"},
            {"frames": [1620, 1800], "dates": ["2020-01-03", "2020-01-03"], "kind": "ending"},
        ]
        plan["pacing"] = {"mode": "uniform", "anchors": [
            {"frame": 90, "date": "2020-01-01"}, {"frame": 1619, "date": "2020-01-03"},
        ]}
    edit(root, "animation-plan.json", use_previous_v8_timing)
    docs = financial.load_project(root)
    assert docs["plan"]["segments"][0]["frames"] == [0, 90]
    assert (docs["plan"]["segments"][-1]["frames"][1] - docs["plan"]["segments"][-1]["frames"][0]) / 30 == 6




def test_v7_compatibility_and_explicit_backup_upgrade(tmp_path):
    root = project(tmp_path)
    def legacy(plan):
        plan["schemaVersion"] = 7
        plan.pop("pacing")
        plan["segments"][0]["frames"] = [0, 90]
        plan["segments"][1]["frames"][0] = 90
        plan["segments"][1]["frames"][1] = 270
        plan["segments"][2]["frames"][0] = 270
        plan["segments"][2]["frames"][1] = 390
        plan["durationSeconds"] = 13
    edit(root, "animation-plan.json", legacy)
    docs = financial.load_project(root)
    assert (docs["plan"]["segments"][-1]["frames"][1] - docs["plan"]["segments"][-1]["frames"][0]) / 30 == 4
    assert financial.frame_date(docs["plan"], 180) == date(2020, 1, 2)
    with pytest.raises(M2VError, match="显式"):
        financial.prepare_line_plan(root, 15)
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    unified_records = ("prepared.json", "review.json", "preview-record.json")
    for name in unified_records:
        (outputs / name).write_bytes(b"old unified record")
    backup = financial.migrate_line(root, 15)
    assert all((backup / name).read_bytes() == content for name, content in originals.items())
    assert (root / "prices.json").read_bytes() == originals["prices.json"]
    for name in unified_records:
        assert (backup / "outputs" / name).read_bytes() == b"old unified record"
        assert not (outputs / name).exists()
    migrated = financial.load_project(root)
    assert (migrated["plan"]["segments"][-1]["frames"][1] - migrated["plan"]["segments"][-1]["frames"][0]) / 30 == 2




@pytest.mark.parametrize("mutation", [
    lambda a: a[1].update(frame=a[0]["frame"]),
    lambda a: a[0].update(date="2019-12-31"),
    lambda a: a[-1].update(frame=3238),
    lambda a: a[-1].update(date="2020-01-01"),
    lambda a: a[0].update(frame=True),
])
def test_invalid_v8_anchors_are_rejected(mutation):
    request = {"displayRange": ["2020-01-01", "2020-03-01"]}
    plan = financial.build_line_plan(request)
    mutation(plan["pacing"]["anchors"])
    with pytest.raises(M2VError, match="anchors"):
        materials._validate_plan(plan, request, {"points": []})




def test_short_many_months_and_single_point_pacing():
    request = {"displayRange": ["1999-01-22", "2026-10-08"]}
    points = [{"date": f"{year}-02-01", "close": year - 1998} for year in range(1999, 2027)]
    plan = financial.build_line_plan(request, 10, {"points": points})
    materials._validate_plan(plan, request, {"points": points})
    assert len(plan["pacing"]["anchors"]) <= 420
    assert financial.frame_date(plan, 239) == date(2026, 10, 8)
    single = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-02"]}, 10,
                                       {"points": [{"date": "2020-01-02", "close": 100}]})
    assert len(single["pacing"]["anchors"]) == 2




def test_plan_validates_data_before_overwriting_and_rejects_legacy(tmp_path):
    root = project(tmp_path)
    old = (root / "animation-plan.json").read_bytes()
    edit(root, "prices.json", lambda data: data["points"].pop())
    assert financial_video.main(["plan", "--project-dir", str(root)]) == 2
    assert (root / "animation-plan.json").read_bytes() == old
    with pytest.raises(SystemExit):
        financial_video.main(["plan", "--project-dir", str(root), "--period", "year"])




def test_migration_rolls_back_if_post_write_validation_fails(tmp_path, monkeypatch):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    legacy_events = b'{"selected":[]}'
    legacy_review = b'{"result":"pass"}'
    (root / "events.json").write_bytes(legacy_events)
    (root / "outputs").mkdir()
    (root / "outputs" / "legibility-review.json").write_bytes(legacy_review)
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}

    def reject(_root):
        raise M2VError("合成写入后故障")

    # `migrate_line` 在 `plan` 模块里执行，它用的是从 `materials` 导入的那份 `load_project`：
    # 替换必须打在真正被调用的命名空间上。
    monkeypatch.setattr(plan, "load_project", reject)
    with pytest.raises(M2VError, match="写入后故障"):
        financial.migrate_line(root, duration=15)
    assert {name: (root / name).read_bytes() for name in financial.MATERIALS} == originals
    assert (root / "events.json").read_bytes() == legacy_events
    assert (root / "outputs" / "legibility-review.json").read_bytes() == legacy_review




def test_close_only_legacy_migration_and_mixed_versions(tmp_path):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    with pytest.raises(M2VError, match="需要 v3 价格和 v7/v8 动画计划"):
        financial.load_project(root)
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    backup = financial.migrate_line(root, duration=15)
    assert backup.is_dir()
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8




def test_v4_plan_requires_explicit_migration_with_complete_backup(tmp_path):
    root = project(tmp_path)
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=4))
    original = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    with pytest.raises(M2VError, match="migrate-line"):
        financial.load_project(root)
    assert financial_video.main(["plan", "--project-dir", str(root)]) == 2
    assert (root / "animation-plan.json").read_bytes() == original["animation-plan.json"]
    final = root / "outputs" / "existing.mp4"
    final.parent.mkdir()
    final.write_bytes(b"existing final")
    backup = financial.migrate_line(root)
    assert {name: (backup / name).read_bytes() for name in financial.MATERIALS} == original
    assert final.read_bytes() == b"existing final"
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8




def test_v5_plan_migrates_explicitly_and_preserves_existing_video(tmp_path):
    root = project(tmp_path)
    edit(root, "animation-plan.json", lambda plan: plan.update(schemaVersion=5, axis={**plan["axis"], "dateScale": "full-range"}))
    existing = root / "outputs" / "financial-line.mp4"
    existing.parent.mkdir()
    existing.write_bytes(b"existing user video")
    review = root / "outputs" / "legibility-review.json"
    review.write_text('{"result":"pass"}', encoding="utf-8")

    with pytest.raises(M2VError, match="需要 v3 价格和 v7/v8 动画计划"):
        financial.load_project(root)
    backup = financial.migrate_line(root, duration=15)

    assert json.loads((backup / "animation-plan.json").read_text(encoding="utf-8"))["schemaVersion"] == 5
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8
    assert financial.load_project(root)["plan"]["axis"]["dateScale"] == "staged-expanding"
    assert existing.read_bytes() == b"existing user video"
    assert not review.exists()
