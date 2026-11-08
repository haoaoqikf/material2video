/** 本作品的盲审播放器：只读本目录时间线与片段，不依赖主项目。 */
import {build} from 'esbuild';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outdir = process.argv[2];
if (!outdir) throw new Error('需要评审包输出目录');
await build({entryPoints:[path.join(root, 'src/production/player.tsx')], bundle:true,
  outfile:path.join(outdir, 'player.js'), platform:'browser', format:'iife', minify:true,
  sourcemap:false, define:{'process.env.NODE_ENV':'"production"'},
  alias:{'@':path.join(root, 'src')}, tsconfig:path.join(root, 'tsconfig.json'),
  resolveExtensions:['.tsx', '.ts', '.jsx', '.js', '.json']});
