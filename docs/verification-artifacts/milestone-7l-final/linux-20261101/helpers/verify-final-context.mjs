import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const root = path.resolve('.tools/m7l-final-release');
const context = path.resolve('.tools/m7l-final-linux-context');
const evidence = path.join(root, 'docs/verification-artifacts/milestone-7l-final/linux-20261101');
const original = JSON.parse(fs.readFileSync(path.join(evidence, 'build-context-manifest.json'), 'utf8').replace(/^\uFEFF/, ''));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase();
const result = original.map(({path: name}) => {
  const candidateHash = hash(path.join(root, name));
  if (candidateHash !== hash(path.join(context, name))) throw new Error(`Final build context mismatch: ${name}`);
  return { path: name, sha256: candidateHash };
});
fs.writeFileSync(path.join(evidence, 'build-context-final-manifest.json'), JSON.stringify(result, null, 2));
console.log(`Final candidate and build context identical: ${result.length} tracked files.`);
