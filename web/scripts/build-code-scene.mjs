/** 独立 esbuild 入口：作品代码只能访问本作品与明确批准的包。 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {build} from 'esbuild';

const [projectArg, entry, output] = process.argv.slice(2);
const project = fs.realpathSync(projectArg);
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(web, 'package.json'));
const sdk = path.join(web, 'src/code-scene/sdk.tsx');
const approved = new Set(['react', 'react-dom', 'motion', 'three', '@react-three/fiber', '@react-three/drei', 'gsap', 'echarts']);
const within = (base, file) => {const rel = path.relative(base, file); return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));};
const result = await build({
  stdin: {contents: `import Scene from ${JSON.stringify(path.resolve(project, entry))}; import {mount} from ${JSON.stringify(path.join(web, 'src/code-scene/host.tsx'))}; mount(Scene);`, resolveDir: web, loader: 'tsx'},
  bundle: true, format: 'iife', platform: 'browser', jsx: 'automatic', metafile: true,
  outfile: path.join(output, 'scene.js'), nodePaths: [path.join(web, 'node_modules')],
  loader: {'.png': 'dataurl', '.jpg': 'dataurl', '.jpeg': 'dataurl', '.webp': 'dataurl', '.svg': 'dataurl', '.woff2': 'dataurl'},
  plugins: [{name: 'project-boundary', setup(builder) {
    builder.onResolve({filter: /.*/}, args => {
      const fromProject = args.importer && within(project, args.importer);
      if (!fromProject) return;
      if (args.path === 'm2v/code-scene') return {path: sdk};
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
const inputs = Object.keys(result.metafile.inputs).filter(file => file !== '<stdin>').map(file => fs.realpathSync(path.resolve(process.cwd(), file)));
fs.writeFileSync(path.join(output, 'inputs.json'), JSON.stringify([...new Set(inputs)]));
