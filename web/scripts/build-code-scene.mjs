/** 独立 esbuild 入口：作品代码只能访问本作品与明确批准的包。 */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {build} from 'esbuild';

const [projectArg, entry, output] = process.argv.slice(2);
const project = fs.realpathSync(projectArg);
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(web, 'package.json'));
const sdk = path.join(web, 'src/code-scene/sdk.tsx');
const sdkEntries = new Map([
  ['m2v/code-scene', sdk],
  ...Object.entries(JSON.parse(fs.readFileSync(path.join(web, 'src/code-scene/entries.json'), 'utf8')))
    .map(([name, file]) => [name, path.join(web, 'src/code-scene', file)]),
]);
function checkMathFonts() {
  const repo = path.dirname(web);
  const registry = JSON.parse(fs.readFileSync(path.join(repo, 'fonts/registry.json'), 'utf8'));
  for (const font of registry.fonts.filter(entry => entry.id.startsWith('katex-'))) {
    const file = path.join(repo, font.targets.find(target => target.startsWith('web/src/assets/math/')));
    const data = fs.existsSync(file) && fs.readFileSync(file);
    if (!data || data.length !== font.bytes || createHash('sha256').update(data).digest('hex') !== font.sha256) {
      throw new Error(`公式字体缺失或摘要失配：${font.file}；先运行 uv run python fonts/fetch.py`);
    }
  }
}
const approved = new Set(['react', 'react-dom', 'motion', 'three', '@react-three/fiber', '@react-three/drei', 'gsap', 'echarts',
  'postprocessing', '@react-three/postprocessing']);
const within = (base, file) => {const rel = path.relative(base, file); return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));};
const result = await build({
  stdin: {contents: `import Scene from ${JSON.stringify(path.resolve(project, entry))}; import {mount} from ${JSON.stringify(path.join(web, 'src/code-scene/host.tsx'))}; mount(Scene);`, resolveDir: web, loader: 'tsx'},
  bundle: true, format: 'iife', platform: 'browser', jsx: 'automatic', metafile: true,
  // 依赖里仍有 process.env.NODE_ENV 分支；浏览器没有 process，构建期直接折成 production。
  define: {'process.env.NODE_ENV': '"production"'},
  // 少数依赖在运行时读 process.emit / nextTick；给一个最小浏览器 shim，避免整幕静默失败。
  banner: {js: 'var process={env:{NODE_ENV:"production"},emit:function(){},emitWarning:function(){},nextTick:function(fn){Promise.resolve().then(fn);},browser:true,version:"",platform:"browser",cwd:function(){return "/";}};'},
  outfile: path.join(output, 'scene.js'), nodePaths: [path.join(web, 'node_modules')],
  loader: {'.png': 'dataurl', '.jpg': 'dataurl', '.jpeg': 'dataurl', '.webp': 'dataurl', '.svg': 'dataurl', '.woff2': 'dataurl', '.ttf': 'dataurl', '.otf': 'dataurl'},
  plugins: [{name: 'project-boundary', setup(builder) {
    // 与 Vite 的 ?raw 保持一致；KaTeX 只读取排版 CSS，字体走受控恢复目标。
    builder.onResolve({filter: /^katex\/dist\/katex.min.css\?raw$/}, args => {
      if (args.importer !== path.join(web, 'src/code-scene/math.tsx')) return;
      return {path: require.resolve('katex/dist/katex.min.css'), namespace: 'raw-css'};
    });
    builder.onLoad({filter: /.*/, namespace: 'raw-css'}, args => ({
      contents: `export default ${JSON.stringify(fs.readFileSync(args.path, 'utf8'))}`, loader: 'js',
    }));
    builder.onResolve({filter: /^m2v\/style(?:\/|$)/}, args => {
      throw new Error(`风格包入口已移除：${args.path}；请使用共享场景组件`);
    });
    builder.onResolve({filter: /.*/}, args => {
      const fromProject = args.importer && within(project, args.importer);
      if (!fromProject) return;
      if (sdkEntries.has(args.path)) {
        if (args.path === 'm2v/code-scene/math') checkMathFonts();
        return {path: sdkEntries.get(args.path)};
      }
      if (args.path.startsWith('.')) {
        const candidate = path.resolve(args.resolveDir, args.path);
        const choices = [candidate, ...['.tsx', '.ts', '.jsx', '.js', '.json', '/index.tsx', '/index.ts'].map(ext => candidate + ext)];
        const file = choices.find(item => fs.existsSync(item) && fs.statSync(item).isFile());
        if (!file || !within(project, fs.realpathSync(file))) throw new Error(`作品导入越界或不存在：${args.path}`);
        return {path: fs.realpathSync(file)};
      }
      const name = args.path.startsWith('@') ? args.path.split('/').slice(0, 2).join('/') : args.path.split('/')[0];
      if (!approved.has(name)) throw new Error(`未批准的作品依赖：${args.path}`);
      return {path: require.resolve(args.path)};
    });
  }}],
});
const inputs = Object.keys(result.metafile.inputs).filter(file => file !== '<stdin>')
  .map(file => file.replace(/^raw-css:/, ''))
  .map(file => fs.realpathSync(path.resolve(process.cwd(), file)));
fs.writeFileSync(path.join(output, 'inputs.json'), JSON.stringify([...new Set(inputs)]));
