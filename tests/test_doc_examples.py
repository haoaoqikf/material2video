"""通用手册描述当前 v8 全画布契约、真实时长与输入审查。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / ".agents/skills/material2video/references"


def test_fixed_examples_document_media_restore():
    """示例媒体不入库，两个有固定媒体的示例都必须写明恢复入口。"""
    root = Path(__file__).resolve().parents[1] / "examples"
    for name in ("american-science-milestones", "solar-system-journey"):
        readme = (root / name / "README.md").read_text(encoding="utf-8")
        assert f"examples/{name}/assets/fetch.py" in readme, f"{name} 没有写明媒体恢复入口"
        assert (root / name / "assets/recipe.json").is_file()


def test_workflow_and_compatibility_documented():
    text = (ROOT / "article-to-storyboard.md").read_text(encoding="utf-8")
    assert "确定画幅" in text and "视觉设计" in text and "不要求播放视频" in text
    assert "实际观看" not in text
    # 替代验收口径：查看帧序列与自动音频，不再把完整播放/试听写成完成前置。
    assert "帧序列" in text and "自动音频" in text
    assert "完整看听" not in text and "完整播放" not in text
    assert "候选稿须用户明确采用并重新审查后才能制作" in text
    assert "实际时长" in text and "600 秒" in text
    assert "最多3个" in text and "用户明确授权才可替换" in text
    assert "人生五选择按核心试制" in text and "five-life-choices" in text
    assert "逐场设计与独立验收" in text and "传播表现评估" in text
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    assert "v7 及更早分镜必须重新编排" in schema
    # v8 没有受控模板：画幅、配色与构图都由作品代码决定。
    assert 'template`（只能是 `code`）' in schema
    assert not any(kind in schema for kind in ("| point |", "| compare |", "| steps |", "| cause |"))


def test_media_and_sound_reference_documents_the_import_boundary():
    text = (ROOT / "article-media-and-sound.md").read_text(encoding="utf-8")
    assert "assets/media-sources.json" in text
    assert "assets/media/<sha256>" in text
    assert "useMediaAsset" in text and "未知" in text
    assert all(name in text for name in ["ding", "ding-dong", "click", "transition"])
    assert "M2V_PIXABAY_API_KEY" in text and "Pexels 固定停用" in text


def test_code_scene_contract_is_documented():
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    assert "m2v/code-scene" in schema and "outputs/code-cache/" in schema
    assert "subtitleSafeArea" in schema and "useMediaAsset" in schema
    assert "1920×1080" in schema and "1080×1920" in schema
    render = (ROOT / "code-scene-runtime.md").read_text(encoding="utf-8")
    assert "代码场景的顺序逐帧采集" in render and "契约页（`version: 6`）" in render
    assert "不使用 fps 重采样或尾帧复制" in render and "不支持倒序或跳帧" in render


def test_visual_creative_direction_is_documented():
    """视觉创意导演方法必须可检索，并接入制作、逐场、复核、导演与示例。"""
    doc = (ROOT / "visual-creative-direction.md").read_text(encoding="utf-8")
    for token in ("视觉创意导演方法", "核心表达", "核心视觉母题", "把 ___ 设计成 ___",
                  "可见变化", "形态变换", "镜头行为", "视觉高潮", "结尾视觉揭示",
                  "禁止项", "十项自我检查", "例外留痕", "不按形式标签",
                  "载体来源", "证据体制", "逐场实例",
                  "不得用图库素材冒充", "不得用代码动画伪造",
                  "cut", "crossfade", "CameraRig"):
        assert token in doc, f"视觉创意文档缺少：{token}"
    assert (ROOT / "visual-creative-direction.md").is_file()
    for name in ("production-workflow.md", "creative-production.md",
                 "article-to-storyboard.md", "scene-design-and-acceptance.md",
                 "visual-review-rubric.md", "director-review-and-edit.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "visual-creative-direction.md" in text, f"{name} 未引用视觉创意文档"
    skill = (ROOT.parents[0] / "SKILL.md").read_text(encoding="utf-8")
    assert "visual-creative-direction.md" in skill
    readme = (ROOT.parents[3] / "README.md").read_text(encoding="utf-8")
    assert "visual-creative-direction.md" in readme
    for name in ("american-science-milestones", "five-life-choices", "solar-system-journey"):
        design = (ROOT.parents[3] / "examples" / name / "DESIGN.md").read_text(encoding="utf-8")
        for token in ("视觉创意方案（2026-10-24，非重制记录）", "核心表达", "核心视觉母题",
                      "整体视觉风格", "分镜设计", "视觉高潮", "结尾视觉揭示", "禁止项",
                      "十项自我检查"):
            assert token in design, f"{name}/DESIGN.md 缺少：{token}"


def test_visual_event_design_has_one_template_and_is_connected():
    """事件方法须同时覆盖画面与认识，并由各入口引用同一定义。"""
    doc = (ROOT / "visual-creative-direction.md").read_text(encoding="utf-8")
    event = doc.split("## 视觉事件设计\n", 1)[1].split("\n## 5.", 1)[0]
    for part in ("初始状态", "变化", "预期", "揭示", "结果"):
        assert f"| {part} |" in event
    for token in ("画面状态", "观众认识", "镜头的信息职责", "同文档", "普通镜头简写",
                  "完整窗口", "简化动态粗样", "保留必要标签", "去文字仅作职责诊断",
                  "五段式预期答案不得进入盲审包", "不新增运行时字段", "CLI 门禁",
                  "金融与住宅只执行适用项", "明确启动的重制", "不追溯"):
        assert token in event, f"事件模板缺少：{token}"
    # 这些是制作方法的契约检查，不是自动判断视频审美。
    for scenario in ("完整揭示事件", "无反转直接因果", "静态文字表达", "有运动但无认识推进"):
        assert f"| {scenario} |" in event
    for name in ("production-workflow.md", "creative-production.md",
                 "scene-design-and-acceptance.md", "visual-review-rubric.md", "subagent-review.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "visual-creative-direction.md#视觉事件设计" in text, name
        assert "| 初始状态 |" not in text, f"{name} 不应维护第二份完整模板"
    repo = ROOT.parents[3]
    for path in (ROOT.parent / "SKILL.md", repo / "README.md"):
        assert "visual-creative-direction.md#视觉事件设计" in path.read_text(encoding="utf-8")


def test_visual_event_design_examples_preserve_delivery_boundary():
    """后补设计不能被误认为既有成片已重制或通过新验收。"""
    repo = ROOT.parents[3]
    for name in ("american-science-milestones", "five-life-choices", "solar-system-journey"):
        design = (repo / "examples" / name / "DESIGN.md").read_text(encoding="utf-8")
        event = design.split("## 视觉事件设计示范（后续制作指导）", 1)[1].split(
            "## 重制选案与方案（2026-10-24）", 1)[0]
        for token in ("未试制、未重渲染", "不改写已有成片验收结论", "镜头的信息职责",
                      "完整窗口", "visual-creative-direction.md#视觉事件设计"):
            assert token in event, (name, token)
        expected_count = 3 if name == "five-life-choices" else 1
        for part in ("初始状态", "变化", "预期", "揭示", "结果"):
            assert event.count(f"| {part} |") == expected_count, (name, part)
        if name == "five-life-choices":
            for title in ("行业：", "学习：", "结尾："):
                assert title in event


def test_remake_start_preserves_constraints_baseline_and_stage_scope():
    """重制入口须防止旧实现锁死方案，或未经核验解除用户要求。"""
    workflow = (ROOT / "production-workflow.md").read_text(encoding="utf-8")
    remake = workflow.split("## 重制启动\n", 1)[1].split("## 立意六项", 1)[0]
    for token in ("用户硬约束及来源", "历史实现选择", "问题与目标", "重入阶段与理由",
                  "局部修复", "结构重制", "不机械重跑全部选案", "实际重制方案确定后",
                  "SHA-256", "preparedFingerprint", "remake-baseline", "直接 Markdown 文件链接",
                  "目录链接", "不递归", "下一次 render 前", "渲染后复查",
                  "videos/examples/", "旧通过结论只作历史", "不伪造"):
        assert token in remake, f"重制入口缺少：{token}"
    design = (ROOT.parents[3] / "examples/five-life-choices/DESIGN.md").read_text(encoding="utf-8")
    sample = design.split("### 后续重制启动示范", 1)[1].split("### 行业：", 1)[0]
    for token in ("60秒与七幕顺序", "持续运镜", "待核验", "核验前保留", "不预先放宽",
                  "不改动当前分镜、测试断言", "不关闭旧问题", "最小动态证据"):
        assert token in sample, token


def test_dynamic_event_evidence_covers_process_and_speed_frame():
    """过程证据集中定义；世界参数与观众可见过程不能混为一谈。"""
    rubric = (ROOT / "visual-review-rubric.md").read_text(encoding="utf-8")
    evidence = rubric.split("## 核心事件的最小动态证据\n", 1)[1].split("## 检查方法", 1)[0]
    requirements = {
        "同速建立": ("同一时间窗", "世界速度", "画面速度", "透视"),
        "尺度揭示": ("局部观察", "新信息进入", "全貌稳定", "结果观察"),
        "实际换轨": ("同一主体", "进入连接", "经过连接", "离开", "继续前进"),
        "分支展开": ("主路径身份", "分叉来源", "层级显现", "整体观察"),
    }
    for kind, tokens in requirements.items():
        row = next(line for line in evidence.splitlines() if line.startswith(f"| {kind} |"))
        for token in tokens:
            assert token in row, (kind, token)
    for token in ("检查前", "取证后", "手机显示条件", "失败现象", "不设统一采样频率",
                  "补证并保持待验证", "不增加「待验证」枚举", "不能仅披露采样限制便判通过"):
        assert token in evidence, token
    for name in ("visual-creative-direction.md", "scene-design-and-acceptance.md", "subagent-review.md"):
        assert "visual-review-rubric.md#核心事件的最小动态证据" in (ROOT / name).read_text(encoding="utf-8")


def test_remake_comparison_and_completion_do_not_overclaim():
    """理解成立、粗样胜出与技术通过均不能单独证明重制完成。"""
    review = (ROOT / "subagent-review.md").read_text(encoding="utf-8")
    comparison = review.split("### 重制的理解、表现与相对改善\n", 1)[1].split("## 评审包", 1)[0]
    for dimension in ("理解", "表现", "相对改善"):
        assert f"| {dimension} |" in comparison
    for token in ("无明显改善", "退步", "证据不足", "理解成立但表现未改善", "自己的时间轴",
                  "最终精制候选仍须", "不能把粗样胜出", "两轮无改善", "不以投票",
                  "不等同真实观众试映"):
        assert token in comparison, token
    director = (ROOT / "director-review-and-edit.md").read_text(encoding="utf-8")
    summary = director.split("## 当前版本完成汇总", 1)[1].split("```", 1)[0]
    for token in ("交付文件与 SHA-256", "两项结论共同绑定", "技术交付完成", "制作复核完成",
                  "未关闭问题", "未覆盖范围"):
        assert token in summary
    assert "技术通过但制作未完成" in director
    assert "`delivered` 只说明技术交付状态" in director


def test_scene_design_and_reach_templates_are_documented():
    """逐场设计与独立验收、百万播放潜力都必须有可填写的模板与完成边界。"""
    scene = (ROOT / "scene-design-and-acceptance.md").read_text(encoding="utf-8")
    for token in ("逐场设计表", "多镜头场景", "逐场验收", "先盲看",
                  "独立评审职责", "缺项", "可见变化", "镜头行为", "母题状态",
                  "载体来源与理由", "真实/示意", "一个核心信息"):
        assert token in scene, f"逐场模板缺少：{token}"
    reach = (ROOT / "reach-potential.md").read_text(encoding="utf-8")
    for token in ("支持具备潜力", "证据不足", "当前未达到", "未知", "发布后验证",
                  "不预测百万播放", "不新增评分或机器门禁"):
        assert token in reach, f"潜力模板缺少：{token}"
    director = (ROOT / "director-review-and-edit.md").read_text(encoding="utf-8")
    for token in ("角色分离自审", "第一次导演审查", "第二次导演审查", "剪辑重组",
                  "回写", "重新 `prepare`", "全片否决", "真实观众", "判断演练"):
        assert token in director, f"导演审查模板缺少：{token}"


def test_subagent_review_is_documented():
    """A/B 级评审必须显式要求独立子代理，并定义评审包与降级披露。"""
    review = (ROOT / "subagent-review.md").read_text(encoding="utf-8")
    for token in ("A 级", "B 级", "独立子代理", "评审包", "角色分离自审",
                  "未独立评审（降级）", "先描述后判定", "没有冷审不等于冷审通过",
                  "不适用"):
        assert token in review, f"子代理评审文档缺少：{token}"
    skill = (ROOT.parents[0] / "SKILL.md").read_text(encoding="utf-8")
    assert "subagent-review.md" in skill
    director = (ROOT / "director-review-and-edit.md").read_text(encoding="utf-8")
    assert "独立子代理" in director and "角色分离自审" in director
    scene = (ROOT / "scene-design-and-acceptance.md").read_text(encoding="utf-8")
    assert "先盲看" in scene and "独立评审职责" in scene


def test_reference_audio_reuse_is_documented():
    """参考音轨复用是受控例外：命令、授权说明与无旁白时间轴都要写清楚。"""
    repo = ROOT.parents[3]
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert "m2v ref audio" in readme and "--user-authorized" in readme
    skill = (ROOT.parents[0] / "SKILL.md").read_text(encoding="utf-8")
    assert "ref audio" in skill and "user-authorized" in skill
    sound = (ROOT / "article-media-and-sound.md").read_text(encoding="utf-8")
    assert "复用参考音轨（受控例外）" in sound
    assert "gainDb: 0" in sound and "sampleRate - 1" in sound
    schema = (ROOT / "storyboard-schema.md").read_text(encoding="utf-8")
    assert "整片只有音床" in schema and "sampleRate - 1" in schema


def test_continuous_sampling_and_text_reveal_checks_are_documented():
    """重制验证过的采样与文字竞争方法必须写回共享参考，并保留适用边界。"""
    text = (ROOT / "visual-review-rubric.md").read_text(encoding="utf-8")
    section = text.split("### 连续采样与文字竞争的最小检查", 1)[1].split("## 检查方法与完成条件", 1)[0]
    for token in ("累计弧长表", "世界距离", "零长度段", "端点钳制", "floor(u × 点数)",
                  "世界速度与画面速度分开", "屏幕位移", "揭示不是缩放",
                  "文字与揭示竞争", "完整揭示窗口", "换轨看主体全过程",
                  "适用边界", "不成为所有题材的统一门禁", "不得升级为通用阈值"):
        assert token in section, f"共享参考缺少：{token}"
