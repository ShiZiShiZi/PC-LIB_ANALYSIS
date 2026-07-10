#!/usr/bin/env node
// Parity helper for scripts/test_parity.py: normalize one report's dim-9 with the web/server.js
// mirror and write the result to a file (stdout is avoided — requiring server.js prints startup
// probes). Usage: node scripts/_parity_helper.js <reportPath> <outPath>
const fs = require('fs');
const path = require('path');
const srv = require(path.join(__dirname, '..', 'web', 'server.js'));

const inPath = process.argv[2];
const outPath = process.argv[3];
const r = JSON.parse(fs.readFileSync(inPath, 'utf8'));
srv.normalizeHarmony(r);
const meta = r.meta || {};
fs.writeFileSync(outPath, JSON.stringify({
  ha: r.harmony_adaptation,
  meta: {
    confidence_overall: meta.confidence_overall ?? null,
    confidence_overall_model: meta.confidence_overall_model ?? null,
  },
}));
