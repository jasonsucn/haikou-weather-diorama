#!/usr/bin/env node
/**
 * Download an OpenStreetMap extract (Overpass JSON) for the Haikou model.
 *
 * Usage:
 *   node tools/fetch-osm.mjs [--bbox south,west,north,east] [--out data/osm/haikou-core.json]
 *
 * Default bbox covers central Haikou: the old arcade quarter, the clock tower,
 * Haidian Island's south shore, the Century Bridge corridor and the Wanlv Park
 * waterfront.
 */
import fs from 'node:fs/promises';
import path from 'node:path';

const args = process.argv.slice(2);
const get = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};

const bbox = get('bbox', '20.0330,110.3010,20.0680,110.3550');
const out = path.resolve(get('out', 'data/osm/haikou-core.json'));

const [s, w, n, e] = bbox.split(',').map(Number);
if ([s, w, n, e].some((v) => !Number.isFinite(v))) {
  console.error('bad --bbox');
  process.exit(2);
}

const query = `[out:json][timeout:240];
(
  way["building"](${s},${w},${n},${e});
  relation["building"](${s},${w},${n},${e});
  way["highway"](${s},${w},${n},${e});
  way["waterway"](${s},${w},${n},${e});
  way["natural"="water"](${s},${w},${n},${e});
  relation["natural"="water"](${s},${w},${n},${e});
  way["landuse"](${s},${w},${n},${e});
  way["leisure"~"park|garden"](${s},${w},${n},${e});
  way["natural"="coastline"](${s},${w},${n},${e});
  way["railway"](${s},${w},${n},${e});
  way["bridge"](${s},${w},${n},${e});
  way["man_made"="bridge"](${s},${w},${n},${e});
  way["place"](${s},${w},${n},${e});
);
out body;
>;
out skel qt;`;

const mirrors = [
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass-api.de/api/interpreter',
];

async function fetchMirror(url) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'User-Agent': 'haikou-weather-diorama/0.1 (research prototype)',
      'Accept': 'application/json',
    },
    body: `data=${encodeURIComponent(query)}`,
    signal: AbortSignal.timeout(300_000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  // Overpass returns HTML error pages with HTTP 200 in some cases.
  if (!text.trimStart().startsWith('{')) throw new Error(`non-JSON body: ${text.slice(0, 120)}`);
  return text;
}

let json = null;
for (const m of mirrors) {
  process.stdout.write(`fetching ${m} ... `);
  try {
    json = await fetchMirror(m);
    console.log(`ok (${(json.length / 1024 / 1024).toFixed(1)} MB)`);
    break;
  } catch (err) {
    console.log(`failed: ${err.message}`);
  }
}
if (!json) {
  console.error('all Overpass mirrors failed');
  process.exit(1);
}

await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, json);
const doc = JSON.parse(json);
const counts = doc.elements.reduce((acc, el) => {
  acc[el.type] = (acc[el.type] || 0) + 1;
  return acc;
}, {});
console.log(`saved ${out}`);
console.log('elements', counts);
