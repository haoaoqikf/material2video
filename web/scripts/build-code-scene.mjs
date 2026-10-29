/** 独立 esbuild 入口：作品代码只能访问本作品与明确批准的包。 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {build} from 'esbuild';

const [projectArg, entry, output, styleConfig] = process.argv.slice(2);
const style = styleConfig ? JSON.parse(fs.readFileSync(styleConfig, 'utf8')) : null;
const project = fs.realpathSync(projectArg);
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(web, 'package.json'));
const sdk = path.join(web, 'src/code-scene/sdk.tsx');
const approved = new Set(['react', 'react-dom', 'motion', 'three', '@react-three/fiber', '@react-three/drei', 'gsap', 'echarts',
  'postprocessing', '@react-three/postprocessing']);
const within = (base, file) => {const rel = path.relative(base, file); return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));};
// 示例虽位于风格目录内，仍是独立作品。共享实现不能引用被风格指纹排除的示例。
const sharedStyleFile = file => style && within(style.root, file) && !within(path.join(style.root, 'examples'), file);
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
    builder.onResolve({filter: /^m2v\/style$/}, () => ({path: 'style', namespace: 'm2v-style'}));
    builder.onLoad({filter: /.*/, namespace: 'm2v-style'}, () => ({contents:
      `const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
       export const identity=freeze(JSON.parse(${JSON.stringify(JSON.stringify(style?.identity ?? null))}));
       export const tokens=freeze(JSON.parse(${JSON.stringify(JSON.stringify(style?.tokens ?? {}))}));`, loader: 'js'}));
    builder.onResolve({filter: /.*/}, args => {
      const fromProject = args.importer && within(project, args.importer);
      const fromStyle = args.importer && !fromProject && sharedStyleFile(args.importer);
      if (!fromProject && !fromStyle) return;
      if (args.path === 'm2v/code-scene') return {path: sdk};
      if (args.path.startsWith('m2v/style/')) {
        const match = /^m2v\/style\/(components|assets)\/([a-z0-9][a-z0-9-]{0,62})$/.exec(args.path);
        const file = match && style?.[match[1]]?.[match[2]];
        if (!file || !sharedStyleFile(fs.realpathSync(file))) throw new Error(`未登记的风格入口：${args.path}`);
        return {path: fs.realpathSync(file)};
      }
      if (args.path.startsWith('.')) {
        const candidate = path.resolve(args.resolveDir, args.path);
        const choices = [candidate, ...['.tsx', '.ts', '.jsx', '.js', '.json', '/index.tsx', '/index.ts'].map(ext => candidate + ext)];
        const file = choices.find(item => fs.existsSync(item) && fs.statSync(item).isFile());
        const boundary = fromStyle ? style.root : project;
        if (!file || !within(boundary, fs.realpathSync(file)) || (fromStyle && !sharedStyleFile(fs.realpathSync(file)))) throw new Error(`${fromStyle ? '风格' : '作品'}导入越界或不存在：${args.path}`);
        // 风格资产只能来自清单登记文件，避免相对导入绕过来源许可登记。
        if (fromStyle && /\.(png|jpe?g|webp|svg|woff2|ttf|otf)$/i.test(file)
            && !Object.values(style.assets).includes(fs.realpathSync(file))) throw new Error(`未登记的风格资产：${args.path}`);
        return {path: fs.realpathSync(file)};
      }
      const name = args.path.startsWith('@') ? args.path.split('/').slice(0, 2).join('/') : args.path.split('/')[0];
      if (!approved.has(name)) throw new Error(`未批准的作品依赖：${args.path}`);
      return {path: require.resolve(args.path)};
    });
  }}],
});
const inputs = Object.keys(result.metafile.inputs).filter(file => file !== '<stdin>' && !file.startsWith('m2v-style:'))
  .map(file => fs.realpathSync(path.resolve(process.cwd(), file)));
fs.writeFileSync(path.join(output, 'inputs.json'), JSON.stringify([...new Set(inputs)]));
