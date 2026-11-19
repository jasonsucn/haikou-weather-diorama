// Haikou Weather Miniature — local server + QWeather proxy.
// Static site + cached API. The API key never reaches the browser.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8787);
const LAT = 20.04;
const LON = 110.34;

// ---------------------------------------------------------------- env
function loadEnv() {
  const file = path.join(ROOT, '.env.qweather');
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}
loadEnv();
const API_HOST = (process.env.QW_API_HOST || '').replace(/^https?:\/\//, '').replace(/\/+$/, '');
const API_KEY = process.env.QW_API_KEY || '';

// ---------------------------------------------------------------- helpers
const num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const pad = (n) => String(n).padStart(2, '0');

function localIso(d = new Date()) {
  const t = new Date(d.getTime() + 8 * 3600 * 1000);
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}T${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}+08:00`;
}

async function qwGet(p) {
  const url = `https://${API_HOST}${p}`;
  const res = await fetch(url, {
    headers: { 'X-QW-Api-Key': API_KEY, 'Accept-Encoding': 'gzip' },
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`QWeather HTTP ${res.status} ${p}`);
  const json = await res.json();
  if (json?.code && json.code !== '200') throw new Error(`QWeather code ${json.code} ${p}`);
  return json;
}

const pCurrent = () => qwGet(`/weather/v1/current/${LAT}/${LON}?localTime=true&lang=zh`);
const pHourly = () => qwGet(`/weather/v1/hourly/${LAT}/${LON}?hours=24&localTime=true&lang=zh`);
const pDaily = () => qwGet(`/weather/v1/daily/${LAT}/${LON}?days=7&localTime=true&lang=zh`);
const pAir = () => qwGet(`/airquality/v1/current/${LAT}/${LON}?lang=zh`);
const pAlert = () => qwGet(`/weatheralert/v1/current/${LAT}/${LON}?lang=zh`);
const pIndices = () => qwGet(`/v7/indices/1d?type=1,2,3,5,8&location=${LON},${LAT}&lang=zh`);

// ---------------------------------------------------------------- normalize
function mapCurrent(c) {
  return {
    time: c.validTime || localIso(),
    temp: num(c.temperature?.value),
    feels: num(c.feelsLike?.value),
    humidity: Math.round(num(c.humidity) * 100),
    windSpeed: num(c.wind?.speed?.value),
    windScale: num(c.wind?.scale),
    windDeg: num(c.wind?.direction?.degree),
    windDir: c.wind?.direction?.compass || '',
    gust: num(c.windGust?.value),
    precip: num(c.precipitation?.amount?.value),
    precipRate: num(c.precipitation?.intensity?.value),
    precipType: c.precipitation?.type || 'none',
    cloud: Math.round(num(c.cloudCover) * 100),
    visibility: num(c.visibility?.value),
    pressure: num(c.pressure?.value),
    uv: num(c.uvIndex),
    dew: num(c.dewPoint?.value),
    code: String(c.condition?.code || '100'),
    text: c.condition?.text || '',
  };
}

function mapHour(h) {
  return {
    time: h.forecastTime,
    hour: new Date(h.forecastTime).getHours(),
    temp: num(h.temperature?.value),
    feels: num(h.feelsLike?.value),
    humidity: Math.round(num(h.humidity) * 100),
    code: String(h.condition?.code || '100'),
    text: h.condition?.text || '',
    precip: num(h.precipitation?.amount?.value),
    precipRate: num(h.precipitation?.intensity?.value),
    precipType: h.precipitation?.type || 'none',
    cloud: Math.round(num(h.cloudCover) * 100),
    windSpeed: num(h.wind?.speed?.value),
    windScale: num(h.wind?.scale),
    windDeg: num(h.wind?.direction?.degree),
    visibility: num(h.visibility?.value),
    uv: num(h.uvIndex),
  };
}

function mapDay(d) {
  const day = d.daytime || {};
  const night = d.nighttime || {};
  return {
    date: (d.forecastStartTime || '').slice(0, 10),
    code: String(day.condition?.code || '100'),
    text: day.condition?.text || '',
    nightCode: String(night.condition?.code || day.condition?.code || '100'),
    nightText: night.condition?.text || '',
    max: num(d.temperatureMax?.value),
    min: num(d.temperatureMin?.value),
    avg: num(d.temperatureAvg?.value),
    humidity: Math.round(num(day.humidity) * 100),
    precip: num(day.precipitation?.amount?.value),
    precipProb: Math.round(num(day.precipitation?.probability) * 100),
    cloud: Math.round(num(day.cloudCover) * 100),
    windScale: num(day.wind?.scale),
    windDeg: num(day.wind?.direction?.degree),
    windSpeed: num(day.wind?.speed?.value),
    uv: num(d.uvIndexMax),
    sunrise: d.astro?.sunrise || null,
    sunset: d.astro?.sunset || null,
    moonPhase: d.astro?.moonPhase || null,
  };
}

function normalize(raw, degraded = false) {
  const hourly = (raw.hourly?.hours || []).map(mapHour);
  const daily = (raw.daily?.days || []).map(mapDay);
  const airIdx = raw.air?.indexes?.[0];
  const alerts = raw.alert?.alerts || [];
  const indices = (raw.indices?.daily || []).map((d) => ({
    name: d.name, category: d.category, level: d.level, text: d.text,
  }));
  const current = mapCurrent(raw.current || {});
  const astro = daily[0] || {};
  return {
    ok: true,
    degraded,
    fetchedAt: new Date().toISOString(),
    city: { name: '海口', lat: LAT, lon: LON },
    current,
    astro: {
      sunrise: astro.sunrise || null,
      sunset: astro.sunset || null,
      moonPhase: astro.moonPhase || null,
    },
    hourly,
    daily,
    air: airIdx ? {
      aqi: num(airIdx.aqi ?? airIdx.aqiDisplay),
      display: airIdx.aqiDisplay ?? String(airIdx.aqi ?? ''),
      category: airIdx.category || '',
      level: airIdx.level || '',
      primary: airIdx.primaryPollutant?.name || airIdx.primaryPollutant?.code || '',
      color: airIdx.color || null,
    } : null,
    alerts: alerts.map((a) => ({
      title: a.headline || a.eventType?.name || '天气预警',
      event: a.eventType?.name || '',
      severity: a.severity || '',
      color: a.color || null,
      text: a.description || a.instruction || '',
      expire: a.expireTime || null,
    })),
    indices,
    attribution: '数据来源：和风天气 QWeather',
  };
}

// ---------------------------------------------------------------- cache
const cache = new Map();
async function cached(key, ttl, loader) {
  const hit = cache.get(key);
  const now = Date.now();
  if (hit && now - hit.at < ttl) return { ...hit.value, cache: 'hit', age: Math.round((now - hit.at) / 1000) };
  const value = await loader();
  cache.set(key, { at: now, value });
  return { ...value, cache: 'miss', age: 0 };
}

let snapshot = null;
function getSnapshot() {
  if (snapshot) return snapshot;
  try {
    snapshot = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'qweather', 'snapshot-haikou.json'), 'utf8'));
  } catch { snapshot = null; }
  return snapshot;
}

async function summary() {
  try {
    const [current, hourly, daily] = await Promise.all([pCurrent(), pHourly(), pDaily()]);
    const [air, alert, indices] = await Promise.all([
      pAir().catch(() => null),
      pAlert().catch(() => null),
      pIndices().catch(() => null),
    ]);
    return normalize({ current, hourly, daily, air, alert, indices }, false);
  } catch (err) {
    const snap = getSnapshot();
    if (!snap) throw err;
    const data = normalize(snap, true);
    data.error = String(err.message || err);
    return data;
  }
}

// ---------------------------------------------------------------- http
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2',
};

function send(res, status, body, type = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': status === 200 ? 'no-cache' : 'no-store' });
  res.end(body);
}

// Only these public prefixes are served. Everything else (dotfiles, .env.qweather,
// server.mjs, tools/, data/, git metadata) is hidden — important because the
// server can be reached from the LAN when started with HOST=0.0.0.0.
const PUBLIC_PREFIXES = ['/app/', '/assets/', '/vendor/'];

function serveStatic(req, res) {
  let pathname;
  try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
  catch { return send(res, 400, JSON.stringify({ error: 'bad url' })); }
  if (pathname === '/') pathname = '/app/index.html';
  if (!PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return send(res, 404, JSON.stringify({ error: 'not found', path: pathname }));
  }
  const abs = path.normalize(path.join(ROOT, pathname));
  if (!abs.startsWith(ROOT)) return send(res, 403, JSON.stringify({ error: 'forbidden' }));
  if (!fs.existsSync(abs) || fs.statSync(abs).isDirectory()) {
    return send(res, 404, JSON.stringify({ error: 'not found', path: pathname }));
  }
  const ext = path.extname(abs).toLowerCase();
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream', 'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache' });
  fs.createReadStream(abs).pipe(res);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  try {
    if (url.pathname === '/api/health') {
      return send(res, 200, JSON.stringify({
        ok: true, apiHost: API_HOST ? 'configured' : 'missing',
        key: API_KEY ? 'configured' : 'missing', time: localIso(),
      }));
    }
    if (url.pathname === '/api/weather/summary') {
      const data = await cached('summary', 10 * 60 * 1000, summary);
      return send(res, 200, JSON.stringify(data));
    }
    if (url.pathname === '/api/weather/hourly') {
      const data = await cached('summary', 10 * 60 * 1000, summary);
      const n = Math.min(Number(url.searchParams.get('hours') || 24), data.hourly.length);
      return send(res, 200, JSON.stringify({
        ok: true, degraded: data.degraded, fetchedAt: data.fetchedAt,
        hours: data.hourly.slice(0, n),
      }));
    }
    if (url.pathname === '/api/weather/daily') {
      const data = await cached('summary', 10 * 60 * 1000, summary);
      const n = Math.min(Number(url.searchParams.get('days') || 7), data.daily.length);
      return send(res, 200, JSON.stringify({
        ok: true, degraded: data.degraded, fetchedAt: data.fetchedAt,
        days: data.daily.slice(0, n),
      }));
    }
    if (url.pathname.startsWith('/api/')) return send(res, 404, JSON.stringify({ error: 'unknown api' }));
    return serveStatic(req, res);
  } catch (err) {
    console.error('[server]', err);
    return send(res, 500, JSON.stringify({ ok: false, error: String(err.message || err) }));
  }
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`端口 ${PORT} 已被占用：可能已经有一个服务在运行，直接打开 http://127.0.0.1:${PORT} 即可。`);
  } else {
    console.error(err);
  }
  process.exit(1);
});

const HOST = process.env.HOST || '127.0.0.1';
server.listen(PORT, HOST, () => {
  console.log(`海口天气微缩城市  http://127.0.0.1:${PORT}`);
  if (HOST !== '127.0.0.1') console.log(`局域网访问  http://<本机IP>:${PORT}`);
  console.log(`API Host: ${API_HOST || '(missing)'}  Key: ${API_KEY ? 'configured' : '(missing)'}`);
});
