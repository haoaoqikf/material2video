"""视觉组件库的静态契约。

组件库是「AI 只选组件、不画组件」这条链路的地基，因此这里锁定最容易
静默出错的几处：注册表与页面声明的 kind 是否对得上、组件取的每个
data-el 是否真的存在于自己的 markup、以及库里有没有引入时间/随机源。
这些都是纯静态检查，不需要浏览器，可以在每次提交时跑。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / ".agents/skills/article2video"
ASSETS = SKILL / "assets"
FIGURES_JS = ASSETS / "figures.js"
FIGURES_CSS = ASSETS / "figures.css"
THEME_CSS = ASSETS / "theme.css"
PAGE = SKILL.parents[2] / "videos/never-fear-interviews/index.html"

# 每注册一个组件：define('kind', [...labels], MARKUP_X, updateX)
_DEFINE = re.compile(r"define\('([a-z0-9-]+)',\s*(\[[^\]]*\]),\s*([A-Z_]+),\s*(\w+)\);")


def _source() -> str:
    return FIGURES_JS.read_text(encoding="utf-8")


def _figures() -> list[tuple[str, list[str], str, str, str]]:
    """返回 (kind, labels, markup, markup_source, body)。

    文件结构固定为「函数体 → markup 常量 → define 调用」，因此每个组件的
    函数体落在上一个 define 结束与自己的 markup 常量之间。
    """
    text = _source()
    matches = list(_DEFINE.finditer(text))
    found = []
    for index, match in enumerate(matches):
        kind, labels, markup_name, _update = match.groups()
        start = matches[index - 1].end() if index > 0 else 0
        marker = f"var {markup_name} = "
        end = text.index(marker, start)
        markup_match = re.search(rf"var {markup_name} = `(.*?)`;", text, re.DOTALL)
        assert markup_match, markup_name
        found.append((kind, json.loads(labels), markup_match.group(1), markup_name, text[start:end]))
    return found


def test_library_registers_the_expected_kinds():
    kinds = [kind for kind, *_ in _figures()]
    assert kinds == ["balance", "gap", "versus", "iceberg", "loop", "stairs", "exchange", "number"]


def test_catalog_mirror_matches_the_library():
    """catalog.py 是校验器用的镜像，必须与浏览器端的注册表逐项一致。

    目录一旦漂移，校验器就会放行一个网页根本不认识的 kind，
    或反过来把合法标注判成错的——两种都只在渲染时才暴露。
    """
    from a2v import catalog

    mirrored = {kind: set(labels) for kind, labels, *_ in _figures()}
    declared = {kind: set(entry.labels) for kind, entry in catalog.FIGURE_CATALOG.items()}
    assert mirrored == declared


def test_catalog_defaults_match_the_page():
    from a2v import catalog

    page = PAGE.read_text(encoding="utf-8")
    block = re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", page, re.DOTALL)
    assert block, "页面不再声明 DEFAULT_FIGURES"
    mapping = dict(re.findall(r"(\w+):\s*'([\w-]+)'", block.group(1)))
    assert mapping == {kind: value for kind, value in catalog.DEFAULT_KINDS.items() if kind != "number"}
    shared = (SKILL / "assets/declarative.js").read_text(encoding="utf-8")
    block = re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", shared, re.DOTALL)
    assert block
    assert dict(re.findall(r"(\w+):\s*'([\w-]+)'", block.group(1))) == catalog.DEFAULT_KINDS


def test_catalog_covers_every_registered_kind():
    from a2v import catalog

    assert set(catalog.FIGURE_CATALOG) == {kind for kind, *_ in _figures()}


def test_scene_kicker_is_authored_copy_not_the_scene_type():
    """幕角标只能来自 `visual.kicker`，不能回落到 `scene.type`。

    角标原先写的是 `kind.textContent = scene.type`，于是画面左上角显示的是
    分镜的内部类型标识符：TITLE / LIST / TIMELINE / NUMBER / CONCLUSION。
    那是 schema 字段名，不是给读者看的字——既没有信息量（读者不需要知道
    "这是一条时间线"），也和整屏中文格格不入。

    这条测试是源码级棘轮：它挡住"哪天顺手把类型名接回去"的回归。
    """
    shared = (SKILL / "assets/declarative.js").read_text(encoding="utf-8")
    block = re.search(r"function sceneIndexBar\(storyboard, index\)\s*\{(.*?)\n  \}", shared, re.DOTALL)
    assert block, "找不到 sceneIndexBar"
    body = block.group(1)
    assert "scene.visual" in body and "kicker" in body, "角标应当取自 scene.visual.kicker"
    assert "scene.type" not in body, "角标不能回落到 scene.type——那是 schema 字段名"

    # 角标只在启用预设时挂载，所以这一条不会动到非预设画面。
    assert "if (preset) section.appendChild(sceneIndexBar(" in shared


def test_catalog_entries_are_documented():
    """目录条目必须在参考文档里出现，避免「代码有、文档查不到」。"""
    from a2v import catalog

    doc = (SKILL / "references/figure-catalog.md").read_text(encoding="utf-8")
    for kind in catalog.FIGURE_CATALOG:
        assert f"`{kind}`" in doc, kind


def test_exposes_the_public_api():
    text = _source()
    assert "A2V.figures = {" in text
    for name in ("register", "known", "mount", "renderScene", "describe"):
        assert re.search(rf"\b{name}: {name}\b", text), name


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_every_picked_element_exists_in_its_markup(kind):
    """组件按 data-el 取元素，取错名字不会报错，只会让画面对不上。

    这类错误在逐帧渲染里表现为「某个元素始终不动」，很难从成片上定位，
    所以在这里静态对照 markup 与函数体。
    """
    for name, _labels, markup, markup_source, body in _figures():
        if name != kind:
            continue
        available = set(re.findall(r'data-el="([^"]+)"', markup))
        assert available, f"{markup_source} 没有任何 data-el"
        # markup 常量本身与 define 行不属于函数体，排除后再找 pick
        for picked in sorted(set(re.findall(r"pick\('([^']+)'\)", body))):
            assert picked in available, f"{kind} 取了 markup 里不存在的 data-el: {picked}"


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_every_declared_label_is_actually_drawn(kind):
    """声明了却没人画的标注键是隐形陷阱。

    分镜写上去、校验器放行、画面上什么都没有——这类「支持但其实没实现」
    比直接报错更糟，所以在这里要求声明与使用严格相等。
    """
    for name, labels, _markup, _source, body in _figures():
        if name != kind:
            continue
        drawn = set(re.findall(r"\bann\.(\w+)", body))
        assert drawn == set(labels), f"{kind}: 声明 {sorted(labels)}，实际画 {sorted(drawn)}"


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_component_reads_labels_from_the_injected_argument(kind):
    """组件只能读注入的标签，不能自己去翻分镜字段。

    两种写法（figure.labels 与旧的 annotations）在 renderScene 合流成一份再注入；
    组件若自己解析字段，迁移写法时就会只有一部分组件跟着变，且不报错。
    """
    for name, _labels, _markup, _source, body in _figures():
        if name != kind:
            continue
        assert re.search(r"var ann = labels \|\| \{\};", body), f"{kind} 没有使用注入的 labels"
        assert "data.annotations" not in body, f"{kind} 直接读了分镜字段"


def test_define_wrapper_forwards_the_labels():
    """define 的包装层必须把 labels 传下去。

    它一度只转发三个参数，结果是所有标注静默消失——画面照常出，只是标签全空。
    """
    text = _source()
    assert re.search(r"update: function \(state, api\) \{\s*update\(state, api, pick, ann\);", text)


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_component_body_has_no_time_or_random_source(kind):
    for name, _labels, _markup, _source, body in _figures():
        if name != kind:
            continue
        for pattern in (r"\bDate\.now\s*\(", r"\bperformance\.now\s*\(", r"\bMath\.random\s*\("):
            assert not re.search(pattern, body), f"{kind} 使用了 {pattern}"


def test_stylesheet_has_no_clock_driven_motion():
    text = FIGURES_CSS.read_text(encoding="utf-8")
    for pattern in (r"@keyframes\b", r"(?<![\w-])animation(?:-[\w-]+)?\s*:", r"(?<![\w-])transition(?:-[\w-]+)?\s*:"):
        assert not re.search(pattern, text), pattern


class TestThemeTokens:
    """组件库的墨色令牌必须由主题提供。

    这是实际踩过的坑：`--fig-*` 一度只在某一支视频的页面里定义，
    换一个主题后组件照样挂载、照样不报错，只是所有线条与填充变成透明，
    画面上只剩文字。视觉评审能看出来，但校验器不会——只能靠这条测试兜住。
    """

    TOKENS = ("--fig-line", "--fig-line-soft", "--fig-ink", "--fig-on-ink", "--fig-surface")

    @staticmethod
    def _used() -> set[str]:
        text = FIGURES_CSS.read_text(encoding="utf-8")
        return set(re.findall(r"var\((--fig-[\w-]+)", text))

    @staticmethod
    def _defined() -> set[str]:
        text = THEME_CSS.read_text(encoding="utf-8")
        return set(re.findall(r"^\s*(--fig-[\w-]+)\s*:", text, re.MULTILINE))

    def test_theme_defines_every_figure_token_the_library_uses(self):
        missing = self._used() - self._defined()
        assert not missing, f"theme.css 缺少组件库用到的令牌：{sorted(missing)}"

    def test_core_tokens_are_all_declared(self):
        assert set(self.TOKENS) <= self._defined()

    def test_token_defaults_are_not_hardcoded_whites(self):
        """物体的表面要用令牌，不能写死白色——写死了在深色主题上就是白底白字。"""
        text = FIGURES_CSS.read_text(encoding="utf-8")
        assert "fill: #ffffff" not in text
        assert "fill: #fff;" not in text


def test_page_defaults_point_at_registered_kinds():
    """页面给出的「类型 → 默认组件」必须都能挂载，否则渲染时才抛错。"""
    page = PAGE.read_text(encoding="utf-8")
    match = re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", page, re.DOTALL)
    assert match, "页面不再声明 DEFAULT_FIGURES"
    mapping = dict(re.findall(r"(\w+):\s*'([\w-]+)'", match.group(1)))
    assert mapping, "DEFAULT_FIGURES 为空"
    registered = {kind for kind, *_ in _figures()}
    for scene_type, kind in mapping.items():
        assert kind in registered, f"场景类型 {scene_type} 指向未注册的组件 {kind}"


def test_page_mounts_a_figure_slot_in_every_scene():
    page = PAGE.read_text(encoding="utf-8")
    scenes = page.count("<section data-a2v-scene")
    slots = page.count("data-a2v-figure")
    assert scenes > 0
    assert slots == scenes, f"{scenes} 个场景只有 {slots} 个挂载点"


def test_storyboard_annotation_keys_are_declared_by_the_component():
    """分镜写的标注键必须落在组件的 labels 声明里。

    拼错键名不会报错，只会让某个标签空着，因此在这里对照一次。
    """
    declared = {kind: labels for kind, labels, *_ in _figures()}
    page = PAGE.read_text(encoding="utf-8")
    mapping = dict(re.findall(r"(\w+):\s*'([\w-]+)'", re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", page, re.DOTALL).group(1)))
    storyboard = json.loads((PAGE.parent / "storyboard.json").read_text(encoding="utf-8"))
    for scene in storyboard["scenes"]:
        annotations = (scene["data"].get("figure") or {}).get("labels")
        if annotations is None:
            annotations = scene["data"].get("annotations")
        if not annotations:
            continue
        kind = (scene["data"].get("figure") or {}).get("kind") or mapping[scene["type"]]
        unknown = set(annotations) - set(declared[kind])
        assert not unknown, f"场景 {scene['id']} 给 {kind} 传了未声明的标注键: {sorted(unknown)}"


class TestFocusStateMigration:
    """「哪一块是焦点」是组件状态，不是组件各自的临场类名。

    迁移之前，每个组件用一套自己的写法表达焦点：`.berg-callout.is-accent`、
    `.stair-bar.is-focus`、以及飞轮那样**根本不表达**（四个节点永远 rest）。
    后果是可测量的：24 帧抽检里 17 帧被 K2 判「几乎没有强调色」。
    这些测试守住迁移后的契约。
    """

    #: 已迁到状态基元的表面：不许再有临场类名。
    MIGRATED = ("berg-callout", "loop-node-disc", "stair-bar", "load-token")

    #: 尚未迁移，逐项登记（见 tasks.md 第 5 组）。
    #: `berg-link` / `berg-callout-label` 是**文字与连接线**的角色色，不是表面状态；
    #: `ex-*` 是交换幕，整组迁移还没做。
    PENDING = ("berg-link", "ex-node-disc", "ex-arc", "ex-arrow")

    def test_ad_hoc_focus_classes_are_confined_to_the_tracked_pending_list(self) -> None:
        """这是一条棘轮：迁完一个组件就要把它从 PENDING 里删掉。

        列表不会悄悄变长，也不会有组件在无人察觉时回到旧写法。
        """
        for line in _source().splitlines():
            if "' is-focus'" not in line and "' is-accent'" not in line:
                continue
            classes = re.findall(r"class:\s*'([\w-]+)", line) + re.findall(r'class="([\w-]+)', line)
            assert classes, f"认不出这一行在给谁加类名：{line.strip()}"
            unknown = set(classes) - set(self.PENDING)
            assert not unknown, (
                f"{sorted(unknown)} 仍在用临场焦点类名。已迁移的表面必须用 "
                f"a2v-surface + data-a2v-state；若确属未迁移，登记到 PENDING 并在 tasks.md 留痕。"
            )

    def test_migrated_surfaces_are_gone_from_the_stylesheet(self) -> None:
        """迁移后的表面不该在样式表里留下 `.is-focus` / `.is-accent` 规则。

        注释里提到旧写法不算——那些是留下迁移来由的说明，要能被搜到。
        """
        text = re.sub(r"/\*.*?\*/", "", FIGURES_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
        for element in self.MIGRATED:
            offenders = re.findall(re.escape(element) + r"\.is-(?:focus|accent)\b", text)
            assert not offenders, f"{element} 的临场焦点规则还没删：{offenders}"
        assert not re.search(r"\.is-focus\b", text), "样式表里还有 .is-focus 规则"

    def test_focus_surfaces_declare_the_state(self) -> None:
        """承载焦点的表面必须挂 `a2v-surface`，状态由 `data-a2v-state` 表达。"""
        text = _source()
        for element in self.MIGRATED:
            pattern = r'class:\s*[\'"]' + element + r' a2v-surface[\'"]|class="' + element + r' a2v-surface"'
            assert re.search(pattern, text), f"{element} 没有迁到 a2v-surface 基元"

    def test_stairs_focus_follows_the_narration(self) -> None:
        """阶梯的焦点跟着口播走，不是"等最后一根柱子长到 95%"。

        原先的写法让前 73% 的帧整屏没有焦点（`STAIRS.START = [0.07, 0.24, 0.48, 0.73]`），
        实测 K2 在 35% 帧只量到 0.0011。
        """
        for _kind, _labels, _markup, _source, body in _figures():
            if "stair-bar" not in body:
                continue
            assert "index === activeStep" in body, "阶梯的焦点没有跟着口播走"
            assert "groups.length - 1 && p > 0.95" not in body, "阶梯仍按「最后一根长到 95%」判焦点"
            return
        raise AssertionError("没有找到阶梯组件")

    def test_loop_focus_follows_the_arrived_node(self) -> None:
        """飞轮到达的那个节点就是焦点。

        迁移前四个节点永远 `rest`，整幕没有任何强调色（实测 35% 帧 0.0015），
        而"到达了哪个节点"这个信息组件本来就已算出来（脉冲用的就是它）。

        第十轮把判焦点从离散改成**连续交接**：焦点仍然跟着到达的节点走
        （`focusIndex` 由 `arrived` 与 `frac` 推出），但换手发生在 `mix = 0`
        那一帧，所以既没有翻牌的跳变，同一帧也仍然只有一个焦点。
        """
        for _kind, _labels, _markup, _source, body in _figures():
            if "loop-node-disc" not in body:
                continue
            assert "arrived" in body, "飞轮没有用到达的节点判焦点"
            assert "focusIndex" in body, "飞轮没有把焦点算成一个下标"
            assert "data-a2v-state" in body, "飞轮没有写状态"
            assert "--a2v-focus-mix" in body, "飞轮没有写连续焦点量"
            return
        raise AssertionError("没有找到飞轮组件")


class TestAssetSyntax:
    """页面脚本必须能解析。

    这一条是补的：往 `figures.js` 的组件模板字符串里写注释时带了反引号，
    模板字符串被提前终结，整个 `figures.js` 语法错误——首页加载失败、
    所有图形消失。当时是跑到浏览器体检才发现的（体检直接报
    `Cannot read properties of undefined (reading 'renderScene')`），
    而纯静态的那批检查全都没拦住。

    这类破坏不需要浏览器就能查出来，而且 `node --check` 的报错精确到行列，
    所以放在这一层做快速拦截，别等浏览器。
    """

    @pytest.mark.parametrize("name", sorted(p.name for p in ASSETS.glob("*.js")))
    def test_every_page_script_parses(self, name: str) -> None:
        node = shutil.which("node")
        if node is None:
            pytest.skip("未安装 node，跳过脚本语法检查")
        target = ASSETS / name
        result = subprocess.run(
            [node, "--check", str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result.returncode == 0, (
            f"{name} 语法错误，页面会整片加载失败：\n{result.stderr.strip()}"
        )
