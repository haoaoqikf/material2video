import fs from 'node:fs';
import path from 'node:path';

const target = path.resolve('.gen/active-composition.tsx');
if (!fs.existsSync(target)) {
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(
    target,
    "// Generated shared scene-tree composition entry.\n" +
      "export { A2VComposition as ActiveComposition } from '../src/compositions/A2VComposition';\n",
    'utf8',
  );
}
