import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const semver = require(path.join(process.env.TEMP, 'serp-m7l-node/node-v22.22.0-win-x64/node_modules/npm/node_modules/semver'));
const root = path.resolve('.tools/m7l-final-release');
const frontend = path.join(root, 'frontend');
const evidence = path.join(root, 'docs/verification-artifacts/milestone-7l-final/linux-20261101');
const beforeText = fs.readFileSync(path.join(frontend, 'package-lock.json'), 'utf8');
const before = JSON.parse(beforeText);
const updated = JSON.parse(fs.readFileSync(path.join(process.env.TEMP, 'serp-m7l-final-minimal-dev-patch/package-lock.json')));
const result = structuredClone(before);
const changes = [];
for (const [name, data] of Object.entries(updated.packages)) {
  if (!(['node_modules/vitest', 'node_modules/vite', 'node_modules/zod'].includes(name) || /^node_modules\/@vitest\/[^/]+$/.test(name))) continue;
  if (!before.packages[name]?.dev || !data.dev) throw new Error(`Not development-only: ${name}`);
  if (data.version === before.packages[name].version) continue;
  result.packages[name] = data;
  changes.push({ name, before: before.packages[name].version, after: data.version });
}
result.packages[''].devDependencies.vitest = '4.1.12';
function resolveDependency(packageName, dependencyName) {
  let scope = packageName;
  while (true) {
    const candidate = (scope ? scope + '/' : '') + 'node_modules/' + dependencyName;
    if (result.packages[candidate]) return result.packages[candidate];
    if (!scope) return;
    scope = scope.replace(/(?:^|\/)node_modules\/(?:@[^/]+\/)?[^/]+$/, '');
  }
}
for (const change of changes) {
  for (const [name, range] of Object.entries(result.packages[change.name].dependencies ?? {})) {
    const dependency = resolveDependency(change.name, name);
    if (!dependency || !semver.satisfies(dependency.version, range, { includePrerelease: true })) throw new Error(`${change.name}: ${name} ${dependency?.version} does not satisfy ${range}`);
  }
}
for (const [name, data] of Object.entries(before.packages)) {
  if (name && !data.dev && JSON.stringify(data) !== JSON.stringify(result.packages[name])) throw new Error(`Runtime entry changed: ${name}`);
}
const manifestText = fs.readFileSync(path.join(frontend, 'package.json'), 'utf8');
const manifest = JSON.parse(manifestText);
manifest.devDependencies.vitest = '4.1.12';
fs.writeFileSync(path.join(evidence, 'package-before.json'), manifestText);
fs.writeFileSync(path.join(evidence, 'package-lock-before.json'), beforeText);
fs.writeFileSync(path.join(frontend, 'package.json'), JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(path.join(frontend, 'package-lock.json'), JSON.stringify(result, null, 2) + '\n');
fs.writeFileSync(path.join(evidence, 'minimal-dev-patch.json'), JSON.stringify({ changes, selectedDirectDependenciesSatisfyLockedRanges: true, allRuntimeLockEntriesUnchanged: true, temporaryRootPinsNotAdopted: true }, null, 2));
console.log(JSON.stringify(changes, null, 2));
