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
// 仅用于仓库内参考场景与测试夹具；作品构建器不接受这些说明符。
const reference = path.join(path.dirname(web), 'tests/support/code-scene-reference.tsx');
const sdkEntries = new Map([
  ['m2v/code-scene', reference],
  ['m2v/code-scene/diagram', path.join(web, 'src/code-scene/diagram.tsx')],
  ['m2v/code-scene/math', path.join(web, 'src/code-scene/math.tsx')],
  ['m2v/code-scene/icons', path.join(web, 'src/code-scene/icons.ts')],
  ['m2v/code-scene/sources', path.join(web, 'src/code-scene/sources.tsx')],
  ['m2v/code-scene/serif', path.join(web, 'src/code-scene/serif.ts')],
]);
const loaders = {'.png':'dataurl','.jpg':'dataurl','.jpeg':'dataurl','.webp':'dataurl','.svg':'dataurl',
  '.woff2':'dataurl','.woff':'dataurl','.ttf':'dataurl','.otf':'dataurl','.glb':'file','.gltf':'file','.bin':'file',
  '.wasm':'file','.hdr':'file','.exr':'file','.glsl':'text','.vert':'text','.frag':'text',
  '.wgsl':'text','.tza':'file'};
const manifest = JSON.parse(fs.readFileSync(path.join(web, 'package.json'), 'utf8'));
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
const checkedPackages = new Map();
const inputDigests = new Map();
const hash = contents => createHash('sha256').update(contents).digest('hex');
const builtinLoaders = {'.js':'js','.jsx':'jsx','.mjs':'js','.cjs':'js','.ts':'ts','.tsx':'tsx','.css':'css','.json':'json','.txt':'text'};
const within = (base, file) => {const rel = path.relative(base, file); return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));};
const result = await build({
  stdin: {contents: `import Scene from ${JSON.stringify(path.resolve(project, entry))}; import {mount} from ${JSON.stringify(path.join(web, 'src/code-scene/host.tsx'))}; mount(Scene);`, resolveDir: web, loader: 'tsx'},
  bundle: true, format: 'iife', platform: 'browser', jsx: 'automatic', metafile: true,
  // 禁止隐式发现作品/父目录tsconfig；实际编译配置留在已绑定的构建脚本内。
  tsconfigRaw: {compilerOptions: {target: 'ES2022', jsx: 'react-jsx', verbatimModuleSyntax: true,
    useDefineForClassFields: true}},
  // 依赖里仍有 process.env.NODE_ENV 分支；浏览器没有 process，构建期直接折成 production。
  define: {'process.env.NODE_ENV': '"production"'},
  // 少数依赖在运行时读 process.emit / nextTick；给一个最小浏览器 shim，避免整幕静默失败。
  banner: {js: 'var process={env:{NODE_ENV:"production"},emit:function(){},emitWarning:function(){},nextTick:function(fn){Promise.resolve().then(fn);},browser:true,version:"",platform:"browser",cwd:function(){return "/";}};'},
  outfile: path.join(output, 'scene.js'), nodePaths: [path.join(web, 'node_modules')],
  loader: loaders,
  plugins: [{name: 'project-boundary', setup(builder) {
    // 与 Vite 的 ?raw 保持一致；KaTeX 只读取排版 CSS，字体走受控恢复目标。
    builder.onResolve({filter: /^katex\/dist\/katex.min.css\?raw$/}, args => {
      if (!args.importer.endsWith('/math.tsx')) return;
      return {path: require.resolve('katex/dist/katex.min.css'), namespace: 'raw-css'};
    });
    builder.onLoad({filter: /.*/, namespace: 'raw-css'}, args => {
      const contents = fs.readFileSync(args.path);
      inputDigests.set(fs.realpathSync(args.path), hash(contents));
      return {contents: `export default ${JSON.stringify(contents.toString('utf8'))}`, loader: 'js'};
    });
    builder.onLoad({filter: /.*/, namespace: 'file'}, args => {
      const extension = path.extname(args.path);
      const loader = loaders[extension] ?? builtinLoaders[extension];
      if (!loader) throw new Error(`未登记的场景资源加载方式：${extension}`);
      const contents = fs.readFileSync(args.path);
      inputDigests.set(fs.realpathSync(args.path), hash(contents));
      return {contents, loader, resolveDir: path.dirname(args.path)};
    });
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
      if (!checkedPackages.has(name)) {
        if (typeof manifest.dependencies?.[name] !== 'string') throw new Error(`参考构建未登记依赖：${name}`);
        const directory = path.join(web, 'node_modules', ...name.split('/'));
        const actual = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8'));
        const real = fs.realpathSync(directory);
        const declared = manifest.dependencies[name].replace(/^[\^~]/, '');
        if (!within(web, real) || actual.name !== name || actual.version !== declared) {
          throw new Error(`依赖版本失配或越界：${name}，要求 ${declared}，实际 ${actual.version}`);
        }
        checkedPackages.set(name, real);
      }
      const resolved = fs.realpathSync(require.resolve(args.path));
      if (!within(checkedPackages.get(name), resolved)) throw new Error(`作品依赖导出越界：${args.path}`);
      return {path: resolved};
    });
  }}],
});
const inputs = Object.keys(result.metafile.inputs).filter(file => file !== '<stdin>')
  .map(file => file.replace(/^raw-css:/, ''))
  .map(file => fs.realpathSync(path.resolve(process.cwd(), file)));
fs.writeFileSync(path.join(output, 'inputs.json'), JSON.stringify([...new Set(inputs)]));
fs.writeFileSync(path.join(output, 'input-digests.json'), JSON.stringify(Object.fromEntries(inputDigests)));
fs.writeFileSync(path.join(output, 'outputs.json'), JSON.stringify(Object.keys(result.metafile.outputs)
  .map(file => path.relative(output, path.resolve(process.cwd(), file)))));
