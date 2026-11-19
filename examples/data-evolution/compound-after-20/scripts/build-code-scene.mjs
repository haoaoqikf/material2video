/** 本作品的场景构建器：仅解析本地文件和本作品声明且安装匹配的依赖。 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';

const [projectArg, entry, outputArg] = process.argv.slice(2);
const root = fs.realpathSync(projectArg);
const owner = fs.realpathSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'));
if (root !== owner) throw new Error('构建器必须属于当前作品，不能借用其他工程的依赖');
const output = path.resolve(outputArg);
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const assets = JSON.parse(fs.readFileSync(path.join(root, 'asset-loaders.json'), 'utf8'));
const hash = data => createHash('sha256').update(data).digest('hex');
const within = (base, file) => {
  const relative = path.relative(base, file);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
};
const inputs = new Map();
const checked = new Map();
const codeLoaders = {'.js':'js', '.jsx':'jsx', '.mjs':'js', '.cjs':'js', '.ts':'ts', '.tsx':'tsx', '.css':'css', '.json':'json', '.txt':'text'};
for (const [extension, loader] of Object.entries(assets)) {
  if (!/^\.[a-z0-9]+$/.test(extension) || Object.hasOwn(codeLoaders, extension)
      || !['dataurl', 'file', 'binary', 'text', 'json'].includes(loader)) {
    throw new Error(`无效资源加载登记：${extension}`);
  }
}
function localDependency(name) {
  if (checked.has(name)) return checked.get(name);
  const expected = manifest.dependencies?.[name];
  if (typeof expected !== 'string' || !/^\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?$/.test(expected)) {
    throw new Error(`作品直接依赖未声明精确版本：${name}`);
  }
  const directory = path.join(root, 'node_modules', ...name.split('/'));
  const actual = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8'));
  const real = fs.realpathSync(directory);
  if (!within(root, real) || actual.name !== name || actual.version !== expected) {
    throw new Error(`作品依赖版本失配或越界：${name}，要求 ${expected}，实际 ${actual.version}`);
  }
  checked.set(name, real);
  return real;
}
function resolveSource(specifier, directory) {
  const candidate = path.resolve(directory, specifier);
  const choices = [candidate, ...['.tsx','.ts','.jsx','.js','.json','.css','/index.tsx','/index.ts'].map(s => candidate+s)];
  const selected = choices.find(file => fs.existsSync(file) && fs.statSync(file).isFile());
  if (!selected || !within(root, fs.realpathSync(selected))) throw new Error(`作品导入越界或不存在：${specifier}`);
  return fs.realpathSync(selected);
}
const entryFile = resolveSource(entry.startsWith('.') ? entry : './'+entry, root);
const result = await build({
  stdin: {contents: `import Scene from ${JSON.stringify(entryFile)}; import {mount} from ${JSON.stringify(path.join(root,'src/code-scene/host.tsx'))}; mount(Scene);`, resolveDir: root, loader:'tsx'},
  outfile: path.join(output, 'scene.js'), bundle:true, format:'iife', platform:'browser', jsx:'automatic', metafile:true,
  nodePaths: [], tsconfigRaw:{compilerOptions:{target:'ES2022', jsx:'react-jsx', verbatimModuleSyntax:true, useDefineForClassFields:true}},
  define:{'process.env.NODE_ENV':'"production"'},
  banner:{js:'var process={env:{NODE_ENV:"production"},emit:function(){},emitWarning:function(){},nextTick:function(fn){Promise.resolve().then(fn);},browser:true,version:"",platform:"browser",cwd:function(){return "/";}};'},
  loader:assets,
  plugins:[{name:'local-project',setup(builder) {
    builder.onResolve({filter:/.*/}, async args => {
      if (args.pluginData?.localResolution) return;
      if (!args.importer || args.importer === '<stdin>' || !within(root,args.importer) || args.importer.split(path.sep).includes('node_modules')) return;
      if (/^(?:m2v\/|https?:|\/\/)/.test(args.path)) throw new Error(`独立作品不接受主项目SDK或远程导入：${args.path}`);
      const raw = args.path.endsWith('?raw');
      const specifier = raw ? args.path.slice(0,-4) : args.path;
      let resolved;
      if (specifier.startsWith('.')) resolved = resolveSource(specifier,args.resolveDir);
      else {
        if (path.isAbsolute(specifier)) throw new Error(`作品不得使用绝对导入：${specifier}`);
        const name = specifier.startsWith('@') ? specifier.split('/').slice(0,2).join('/') : specifier.split('/')[0];
        const base = localDependency(name);
        // 使用打包器的browser/import条件；require.resolve会误选CJS甚至拒绝import-only包。
        const resolution = await builder.resolve(specifier, {resolveDir:root, kind:args.kind,
          pluginData:{localResolution:true}});
        if (resolution.errors.length || !resolution.path) {
          throw new Error(`作品依赖无法解析：${specifier}；${resolution.errors.map(e=>e.text).join('; ')}`);
        }
        resolved = fs.realpathSync(resolution.path);
        if (!within(base,resolved)) throw new Error(`依赖导出越界：${specifier}`);
      }
      return {path:resolved, ...(raw ? {namespace:'raw-text'} : {})};
    });
    builder.onLoad({filter:/.*/}, args => {
      const file = fs.realpathSync(args.path);
      if (!within(root,file)) throw new Error(`构建输入越过作品：${file}`);
      const data = fs.readFileSync(file);
      inputs.set(file,hash(data));
      if (args.namespace === 'raw-text') return {contents:`export default ${JSON.stringify(data.toString('utf8'))}`,loader:'js'};
      const extension = path.extname(file);
      const loader = assets[extension] ?? codeLoaders[extension];
      if (!loader) throw new Error(`未登记资源加载方式：${extension}`);
      return {contents:data,loader,resolveDir:path.dirname(file)};
    });
  }}],
});
fs.writeFileSync(path.join(output,'inputs.json'),JSON.stringify([...inputs.keys()]));
fs.writeFileSync(path.join(output,'input-digests.json'),JSON.stringify(Object.fromEntries(inputs)));
fs.writeFileSync(path.join(output,'outputs.json'),JSON.stringify(Object.keys(result.metafile.outputs).map(file=>path.relative(output,path.resolve(file)))));
