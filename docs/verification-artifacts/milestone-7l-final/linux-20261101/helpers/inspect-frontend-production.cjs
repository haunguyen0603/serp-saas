const fs = require('node:fs');
const { createRequire } = require('node:module');
const assert = require('node:assert/strict');
const requireApp = createRequire('/app/package.json');
const paths = JSON.parse(fs.readFileSync('/app/.next/server/app-paths-manifest.json'));
const alertRoutes = Object.entries(paths).filter(([key]) => key.includes('ranking-alerts'));
assert(alertRoutes.length > 0);
for (const [, file] of alertRoutes) assert(fs.existsSync('/app/.next/server/' + file));
const absentDevelopmentPackages = {};
for (const name of ['vitest', 'vite', 'eslint', 'eslint-config-next', 'minimatch', 'zod']) {
  try { requireApp.resolve(name); absentDevelopmentPackages[name] = false; }
  catch (error) { if (error.code !== 'MODULE_NOT_FOUND') throw error; absentDevelopmentPackages[name] = true; }
}
assert.equal(process.platform, 'linux');
assert.notEqual(process.getuid(), 0);
assert.equal(requireApp('next/package.json').version, '16.4.3');
console.log(JSON.stringify({ platform: process.platform, arch: process.arch, node: process.version, uid: process.getuid(), next: requireApp('next/package.json').version, react: requireApp('react/package.json').version, sharp: JSON.parse(fs.readFileSync('/app/node_modules/sharp/package.json')).version, buildId: fs.readFileSync('/app/.next/BUILD_ID', 'utf8').trim(), alertRoutes, prerenderedAlertRoute: JSON.parse(fs.readFileSync('/app/.next/prerender-manifest.json')).routes['/app/ranking-alerts'], absentDevelopmentPackages }, null, 2));
