"""只读诊断：工具、设备、运行库、模型与来源凭据的真实可用性。

诊断不安装任何依赖、不下载模型、不回显凭据；配置存在或缺模型只说明
“未验证”，不能写成已通过。真实推理仍须显式 index / verify。
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .errors import MaterialError
from .model_manager import ModelManager


def _version(executable: str, *, first_line: bool = True) -> dict:
    try:
        result = subprocess.run([executable, '-version'], capture_output=True, timeout=20)
        text = result.stdout.decode('utf-8', 'replace').strip().splitlines()
        if result.returncode or not text:
            return {'available': True, 'version': None, 'note': '工具存在但未返回版本'}
        return {'available': True, 'version': text[0] if first_line else text[:1]}
    except (OSError, subprocess.TimeoutExpired):
        return {'available': False, 'version': None, 'note': '无法执行'}


def _ffprobe() -> dict:
    executable = os.environ.get('M2V_FFPROBE') or shutil.which('ffprobe')
    if not executable or not Path(executable).is_file():
        return {'available': False, 'path': None, 'source': None,
                'note': '缺少 ffprobe；安装 FFmpeg 或设置 M2V_FFPROBE 后才能探测时基'}
    source = 'M2V_FFPROBE' if os.environ.get('M2V_FFPROBE') else 'PATH'
    return {**_version(executable), 'path': str(Path(executable)), 'source': source}


def tools() -> dict:
    ffmpeg = get_ffmpeg_exe()
    return {'ffmpeg': {**_version(ffmpeg), 'path': str(ffmpeg)},
            'ffprobe': _ffprobe(),
            'yt-dlp': _ytdlp_version()}


def _ytdlp_version() -> dict:
    try:
        from m2v.materials.ytdlp_worker import YTDLP_VERSION
    except ImportError:  # pragma: no cover - 包内模块始终存在
        YTDLP_VERSION = None
    try:
        import importlib.metadata
        installed = importlib.metadata.version('yt-dlp')
    except importlib.metadata.PackageNotFoundError:
        return {'available': False, 'expected': YTDLP_VERSION, 'installed': None,
                'note': '未安装 yt-dlp；平台获取不可用'}
    return {'available': installed == YTDLP_VERSION, 'expected': YTDLP_VERSION,
            'installed': installed,
            'note': None if installed == YTDLP_VERSION else '版本与受控 worker 不一致，平台获取会拒绝'}


def device() -> dict:
    """设备诊断只报告本机可见性；不因有 GPU 就自动启用非确定性路径。"""
    if importlib.util.find_spec('torch') is None:
        return {'torch': False, 'cuda': False, 'note': '未安装 torch；语义/视觉索引不可用（CPU 默认）'}
    try:
        import torch
        return {'torch': True, 'version': torch.__version__,
                'cuda': bool(torch.cuda.is_available()),
                'deviceDefault': 'cpu',
                'note': '默认 CPU；CUDA 可用也不自动切换，需显式参数与真实测试'}
    except Exception as exc:  # noqa: BLE001 - 运行库损坏应可在诊断中看到
        return {'torch': False, 'cuda': False,
                'note': f'torch 无法加载（{type(exc).__name__}）；请按锁定依赖恢复'}


def sources() -> dict:
    """来源与凭据只报告存在性；不回显 Key、cookie 内容或完整地址。"""
    pixabay = bool(os.environ.get('PIXABAY_API_KEY') or os.environ.get('PIXABAY_KEY'))
    return {
        'pixabay': {'configured': pixabay, 'api': 'enabled' if pixabay else 'key-missing',
                    'note': '图库检索需要显式环境变量 Key；缺失不阻断其它来源'},
        'pexels': {'configured': bool(os.environ.get('PEXELS_API_KEY')), 'api': 'disabled',
                   'note': 'Pexels API 停用；显式网页与公开直链仍可用'},
        'public': {'commons': 'public-api', 'archive': 'public-api', 'nasa': 'public-api'},
        'platform': {'search': ['youtube', 'bilibili'], 'knownLinks': ['douyin', 'xiaohongshu', 'weibo', 'xigua'],
                     'note': '会话/风控可能受限；cookie 只从显式文件读取'},
        'cookieFileConfigured': bool(os.environ.get('M2V_PLATFORM_COOKIES')),
    }


def doctor(models_root: Path, *, registry_path: Path | None = None) -> dict:
    models = ModelManager(models_root, registry_path=registry_path)
    report = models.doctor()
    report.update(tools=tools(), device=device(), sources=sources(),
                  modelsRoot=str(models_root), registryDigest=models.registry_digest)
    # 显式声明：这份报告没有任何联网、下载、安装或真实推理发生。
    report['performed'] = {'network': False, 'install': False, 'inference': False, 'download': False}
    report['note'] = ('文件存在、依赖已安装、凭据已配置都不等于模型摘要或真实推理通过；'
                      '请显式运行 models verify 与 index 取得真实证据')
    return report


def require_dependency(package: str, *, extra: str, purpose: str) -> None:
    try:
        available = importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        # 测试或宿主注入的模块可能没有 __spec__；已导入即视为可用。
        available = package in __import__('sys').modules
    if not available:
        raise MaterialError('dependency-missing', f'{purpose}需要可选依赖 {package}；请显式安装 extra：{extra}',
                            stage='models')
