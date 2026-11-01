import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const root = path.resolve('.tools/m7l-final-release');
const context = path.resolve('.tools/m7l-final-linux-context');
const shellOnly = process.argv.includes('--shell-only');
const files = execFileSync('git', ['ls-files', '-z', ...(shellOnly ? ['*.sh'] : ['frontend'])], { cwd: root }).toString().split('\0').filter(Boolean);
const changed = [];
for (const file of files) {
  if (!shellOnly && !/\.(?:[cm]?js|jsx|ts|tsx|css|md|mdx|json|html|txt|svg|ya?ml)$/.test(file) && !/\.(?:gitignore|prettierignore)$/.test(file)) continue;
  const source = path.join(root, file);
  const bytes = fs.readFileSync(source);
  if (bytes.includes(0)) continue;
  const text = bytes.toString('utf8');
  if (!text.includes('\r\n')) continue;
  const beforeBlob = execFileSync('git', ['hash-object', `--path=${file}`, '--', file], { cwd: root }).toString().trim();
  fs.writeFileSync(source, text.replaceAll('\r\n', '\n'));
  const afterBlob = execFileSync('git', ['hash-object', `--path=${file}`, '--', file], { cwd: root }).toString().trim();
  if (beforeBlob !== afterBlob) throw new Error(`Semantic Git blob drift: ${file}`);
  fs.copyFileSync(source, path.join(context, file));
  changed.push({ path: file, beforeBlob, afterBlob });
}
fs.writeFileSync(path.join(root, `docs/verification-artifacts/milestone-7l-final/linux-20261101/${shellOnly ? 'shell' : 'frontend'}-eol-normalization.json`), JSON.stringify({ changed, allGitBlobsUnchanged: true }, null, 2));
console.log(`Normalized CRLF to LF in ${changed.length} files; all Git blob identities unchanged.`);
