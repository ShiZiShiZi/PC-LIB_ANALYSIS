#!/usr/bin/env node
/**
 * CLI over web/harmony-mirror.js — check if packages are adapted to HarmonyOS PC,
 * or stamp a report.json's dependencies in place. Used by the analyzer agent:
 *   node scripts/harmony_adapted.js --report runs/<lib>/<ts>/report.json
 *   node scripts/harmony_adapted.js --ecosystem python --names numpy,scipy
 */
'use strict';

const mirror = require('../web/harmony-mirror');

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

(async () => {
  const report = arg('--report');
  if (report) {
    const r = await mirror.stampReport(report);
    console.log(`stamped ${r.stamped}/${r.total} dependencies as harmony_adapted in ${report}`);
    return;
  }
  const eco = arg('--ecosystem', 'python');
  const names = (arg('--names', '') || '').split(',').map((s) => s.trim()).filter(Boolean);
  const refresh = process.argv.includes('--refresh');
  const out = await mirror.statusFor(eco, names, refresh);
  console.log(JSON.stringify(out.results));
})().catch((e) => { console.error(String(e && e.message || e)); process.exit(1); });
