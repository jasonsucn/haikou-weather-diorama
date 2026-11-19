#!/usr/bin/env node
/**
 * QWeather (和风天气) probe for Haikou.
 *
 * Verifies, with a real key + API Host, that Haikou weather (current, hourly,
 * daily forecast, air quality, warnings, indices) is reachable and returns
 * usable data. Writes a JSON report under data/qweather/.
 *
 * Usage:
 *   Copy .env.example to .env.qweather and fill QW_API_HOST / QW_API_KEY
 *   node tools/qweather-probe.mjs
 *
 *   # or
 *   node tools/qweather-probe.mjs --host abc123.qweatherapi.com --key ...
 *
 * Notes:
 *  - Since 2026 the public hosts devapi/geoapi.qweather.com are retired; every
 *    account gets its own API Host (控制台 → 设置 → API Host).
 *  - Forecast APIs are /weather/v1/{current|hourly|daily}/{lat}/{lon} and return
 *    arrays named hours / days (not hourly / daily).
 *  - Warnings: /weatheralert/v1/current/{lat}/{lon}
 *  - Life indices still use /v7/indices/{1d|3d}?type=...&location=lon,lat
 *  - The key is never printed in the report.
 */
import fs from 'node:fs/promises';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';

// Optional local credentials file (kept out of git): .env.qweather
if (existsSync('.env.qweather')) {
  for (const line of readFileSync('.env.qweather', 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}

const args = process.argv.slice(2);
const getArg = (name) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
};

let host = getArg('host') || process.env.QW_API_HOST || '';
const key = getArg('key') || process.env.QW_API_KEY || '';
host = host.replace(/^https?:\/\//, '').replace(/\/+$/, '');

if (!host || !key) {
  console.error('missing --host/--key (or QW_API_HOST / QW_API_KEY)');
  process.exit(2);
}

// Haikou city centre (骑楼老街 / 钟楼 waterfront). QWeather city id: 101310101.
const LAT = 20.04;
const LON = 110.34;
const loc = `${LON},${LAT}`;

const probes = [
  {
    name: 'GeoAPI 城市搜索（海口）',
    path: `/geo/v2/city/lookup?location=${encodeURIComponent('海口')}&range=cn&lang=zh`,
    expect: (j) => Array.isArray(j?.location) && j.location.length > 0,
    summarize: (j) => j.location.slice(0, 3).map((l) => `${l.name}/${l.id} (${l.lat},${l.lon})`).join(' | '),
  },
  {
    name: 'GeoAPI 坐标反查（20.04,110.34）',
    path: `/geo/v2/city/lookup?location=${loc}&lang=zh`,
    expect: (j) => Array.isArray(j?.location) && j.location.length > 0,
    summarize: (j) => j.location.slice(0, 2).map((l) => `${l.name}/${l.id}`).join(' | '),
  },
  {
    name: '实时天气 current',
    path: `/weather/v1/current/${LAT}/${LON}?localTime=true&lang=zh`,
    expect: (j) => j?.temperature != null,
    summarize: (j) => `${j.condition?.text} ${j.temperature?.value}°C 体感${j.feelsLike?.value}°C 湿度${Math.round((j.humidity ?? 0) * 100)}% 风${j.wind?.direction?.compass}${j.wind?.speed?.value}m/s(${j.wind?.scale}级) 云量${j.cloudCover} 能见度${Math.round((j.visibility?.value ?? 0) / 1000)}km`,
  },
  {
    name: '逐小时预报 hourly 24h',
    path: `/weather/v1/hourly/${LAT}/${LON}?hours=24&localTime=true&lang=zh`,
    expect: (j) => Array.isArray(j?.hours) && j.hours.length > 0,
    summarize: (j) => `${j.hours.length} 条，首条 ${j.hours[0].forecastTime} ${j.hours[0].condition?.text} ${j.hours[0].temperature?.value}°C`,
  },
  {
    name: '每日预报 daily 3 天',
    path: `/weather/v1/daily/${LAT}/${LON}?days=3&localTime=true&lang=zh`,
    expect: (j) => Array.isArray(j?.days) && j.days.length >= 3,
    summarize: (j) => j.days.map((d) => `${d.forecastStartTime.slice(0, 10)} ${d.daytime?.condition?.text} ${Math.round(d.temperatureMin?.value)}~${Math.round(d.temperatureMax?.value)}°C`).join(' | '),
  },
  {
    name: '每日预报 daily 7 天',
    path: `/weather/v1/daily/${LAT}/${LON}?days=7&localTime=true&lang=zh`,
    expect: (j) => Array.isArray(j?.days) && j.days.length >= 7,
    summarize: (j) => `${j.days.length} 天：${j.days.map((d) => d.forecastStartTime.slice(0, 10)).join(',')}`,
  },
  {
    name: '每日预报 daily 10 天',
    path: `/weather/v1/daily/${LAT}/${LON}?days=10&localTime=true&lang=zh`,
    expect: (j) => Array.isArray(j?.days) && j.days.length >= 7,
    summarize: (j) => `${j.days.length} 天（免费计划上限可能为 7）`,
  },
  {
    name: '空气质量 AQI',
    path: `/airquality/v1/current/${LAT}/${LON}?lang=zh`,
    expect: (j) => Array.isArray(j?.indexes) && j.indexes.length > 0,
    summarize: (j) => `${j.indexes[0].code} ${j.indexes[0].aqiDisplay} ${j.indexes[0].category}`,
  },
  {
    name: '灾害预警 weatheralert',
    path: `/weatheralert/v1/current/${LAT}/${LON}?lang=zh`,
    expect: (j) => Array.isArray(j?.alerts),
    summarize: (j) => `${j.alerts.length} 条生效预警`,
  },
  {
    name: '天气指数 indices 1d',
    path: `/v7/indices/1d?type=1,2,3&location=${loc}&lang=zh`,
    expect: (j) => Array.isArray(j?.daily) && j.daily.length > 0,
    summarize: (j) => `${j.daily.length} 条：${j.daily.map((d) => `${d.name}${d.category}`).join(' / ')}`,
  },
];

const report = {
  generatedAt: new Date().toISOString(),
  apiHost: host,
  location: { city: '海口', locationId: '101310101', lat: LAT, lon: LON },
  probes: [],
};

for (const p of probes) {
  const url = `https://${host}${p.path}`;
  const started = Date.now();
  const rec = { name: p.name, path: p.path };
  try {
    const res = await fetch(url, {
      headers: { 'X-QW-Api-Key': key, 'Accept-Encoding': 'gzip' },
      signal: AbortSignal.timeout(15_000),
    });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* keep raw */ }
    rec.http = res.status;
    rec.ms = Date.now() - started;
    rec.code = json?.code ?? json?.metadata ? 'ok' : json?.code;
    rec.ok = res.ok && p.expect(json);
    if (json) rec.summary = p.summarize(json);
    if (!rec.ok) rec.raw = json ?? text.slice(0, 300);
  } catch (err) {
    rec.http = 0;
    rec.ms = Date.now() - started;
    rec.ok = false;
    rec.error = err.message;
  }
  report.probes.push(rec);
  const mark = rec.ok ? 'PASS' : 'FAIL';
  console.log(`[${mark}] ${p.name}  ${rec.http ?? ''}  ${rec.ms}ms  ${rec.summary ?? rec.error ?? (rec.raw ? JSON.stringify(rec.raw).slice(0, 160) : '')}`);
  if (rec.raw) console.log(`        ${JSON.stringify(rec.raw).slice(0, 400)}`);
}

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const out = path.resolve('data/qweather', `probe-${stamp}.json`);
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, JSON.stringify(report, null, 2));
console.log(`\nreport: ${out}`);
const passes = report.probes.filter((p) => p.ok).length;
console.log(`passed ${passes}/${report.probes.length}`);
process.exit(passes === report.probes.length ? 0 : 1);
