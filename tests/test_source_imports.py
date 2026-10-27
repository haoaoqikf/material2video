"""共享引用解析的边界；构建和证据绑定继续由各自消费者回归。"""
from m2v.core.source_imports import import_specifiers, resolve_import


def test_all_literal_import_forms():
    source = """import x from './x';
export {y} from '@/y';
import('./lazy');
import './effect.css';
@import url('./theme.css');
background: url(./image.png);
import(variable);
"""
    assert sorted(import_specifiers(source)) == sorted([
        './x', '@/y', './lazy', './effect.css', './theme.css', './theme.css', './image.png'])


def test_alias_directory_assets_and_bare_module(tmp_path):
    web = tmp_path / 'web'
    (web / 'src/pkg').mkdir(parents=True)
    target = web / 'src/pkg/index.tsx'
    target.write_text('export default 1;', encoding='utf-8')
    importer = web / 'src/main.ts'
    assert resolve_import('@/pkg', importer, web) == target
    assert resolve_import('~/pkg', importer, web) == target
    assert resolve_import('./pkg', importer, web) == target
    assert resolve_import(str(target), importer, web) == target
    assert resolve_import('react', importer, web) is None
    assert resolve_import('./absent', importer, web) is None
