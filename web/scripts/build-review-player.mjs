import {build} from 'esbuild';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outdir = process.argv[2];
if (!outdir) throw new Error('需要评审包输出目录');
await build({entryPoints:[path.join(web, 'src/production/player.tsx')], bundle:true,
  outfile:path.join(outdir, 'player.js'), platform:'browser', format:'iife', minify:true,
  sourcemap:false, define:{'process.env.NODE_ENV':'"production"'},
  alias:{'@':path.join(web, 'src')}, tsconfig:path.join(web, 'tsconfig.json')});
