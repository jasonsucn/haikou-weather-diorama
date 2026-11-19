// Direct-to-QWeather client for static hosting (GitHub Pages), where the
// Node proxy in server.mjs is unavailable. The user's own API host/key are
// kept in localStorage on their own device — never in the repository.
import * as THREE from 'three';

const LAT = 20.04;
const LON = 110.34;
const LS_HOST = 'haikou.qweather.host';
const LS_KEY = 'haikou.qweather.key';

const num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

export function getCredentials() {
  return { host: localStorage.getItem(LS_HOST) || '', key: localStorage.getItem(LS_KEY) || '' };
}
export function saveCredentials(host, key) {
  localStorage.setItem(LS_HOST, host.trim().replace(/^https?:\/\//, '').replace(/\/+$/, ''));
  localStorage.setItem(LS_KEY, key.trim());
}
export function clearCredentials() {
  localStorage.removeItem(LS_HOST);
  localStorage.removeItem(LS_KEY);
}

function localIso(d = new Date()) {
  const t = new Date(d.getTime() + 8 * 3600 * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}T${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}+08:00`;
}

async function qwGet(host, key, p) {
  const res = await fetch(`https://${host}${p}`, {
    headers: { 'X-QW-Api-Key': key, 'Accept-Encoding': 'gzip' },
    signal: AbortSignal.timeout(12000),
  });
  if (!res.ok) throw new Error(`QWeather HTTP ${res.status}`);
  const json = await res.json();
  if (json?.code && json.code !== '200') throw new Error(`QWeather code ${json.code}`);
  return json;
}

function mapCurrent(c) {
  return {
    time: c.validTime || localIso(), temp: num(c.temperature?.value),
    feels: num(c.feelsLike?.value), humidity: Math.round(num(c.humidity) * 100),
    windSpeed: num(c.wind?.speed?.value), windScale: num(c.wind?.scale),
    windDeg: num(c.wind?.direction?.degree), windDir: c.wind?.direction?.compass || '',
    gust: num(c.windGust?.value), precip: num(c.precipitation?.amount?.value),
    precipRate: num(c.precipitation?.intensity?.value), precipType: c.precipitation?.type || 'none',
    cloud: Math.round(num(c.cloudCover) * 100), visibility: num(c.visibility?.value),
    pressure: num(c.pressure?.value), uv: num(c.uvIndex), dew: num(c.dewPoint?.value),
    code: String(c.condition?.code || '100'), text: c.condition?.text || '',
  };
}
function mapHour(h) {
  return {
    time: h.forecastTime, hour: new Date(h.forecastTime).getHours(),
    temp: num(h.temperature?.value), feels: num(h.feelsLike?.value),
    humidity: Math.round(num(h.humidity) * 100),
    code: String(h.condition?.code || '100'), text: h.condition?.text || '',
    precip: num(h.precipitation?.amount?.value), precipRate: num(h.precipitation?.intensity?.value),
    precipType: cType(h), cloud: Math.round(num(h.cloudCover) * 100),
    windSpeed: num(h.wind?.speed?.value), windScale: num(h.wind?.scale),
    windDeg: num(h.wind?.direction?.degree), visibility: num(h.visibility?.value), uv: num(h.uvIndex),
  };
}
function cType(h) { return h.precipitation?.type || 'none'; }
function mapDay(d) {
  const day = d.daytime || {}, night = d.nighttime || {};
  return {
    date: (d.forecastStartTime || '').slice(0, 10),
    code: String(day.condition?.code || '100'), text: day.condition?.text || '',
    nightCode: String(night.condition?.code || day.condition?.code || '100'),
    nightText: night.condition?.text || '',
    max: num(d.temperatureMax?.value), min: num(d.temperatureMin?.value), avg: num(d.temperatureAvg?.value),
    humidity: Math.round(num(day.humidity) * 100), precip: num(day.precipitation?.amount?.value),
    precipProb: Math.round(num(day.precipitation?.probability) * 100),
    cloud: Math.round(num(day.cloudCover) * 100), windScale: num(day.wind?.scale),
    windDeg: num(day.wind?.direction?.degree), windSpeed: num(day.wind?.speed?.value),
    uv: num(d.uvIndexMax), sunrise: d.astro?.sunrise || null, sunset: d.astro?.sunset || null,
    moonPhase: d.astro?.moonPhase || null,
  };
}
function normalize(raw) {
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
    ok: true, degraded: false, direct: true, fetchedAt: new Date().toISOString(),
    city: { name: '海口', lat: LAT, lon: LON }, current,
    astro: { sunrise: astro.sunrise || null, sunset: astro.sunset || null, moonPhase: astro.moonPhase || null },
    hourly, daily,
    air: airIdx ? {
      aqi: num(airIdx.aqi ?? airIdx.aqiDisplay), display: airIdx.aqiDisplay ?? String(airIdx.aqi ?? ''),
      category: airIdx.category || '', level: airIdx.level || '',
      primary: airIdx.primaryPollutant?.name || airIdx.primaryPollutant?.code || '', color: airIdx.color || null,
    } : null,
    alerts: alerts.map((a) => ({
      title: a.headline || a.eventType?.name || '天气预警', event: a.eventType?.name || '',
      severity: a.severity || '', color: a.color || null, text: a.description || a.instruction || '',
      expire: a.expireTime || null,
    })),
    indices, attribution: '数据来源：和风天气 QWeather',
  };
}

// Fetch a full weather summary straight from QWeather using the user's key.
export async function fetchDirect(host, key) {
  const [current, hourly, daily] = await Promise.all([
    qwGet(host, key, `/weather/v1/current/${LAT}/${LON}?localTime=true&lang=zh`),
    qwGet(host, key, `/weather/v1/hourly/${LAT}/${LON}?hours=24&localTime=true&lang=zh`),
    qwGet(host, key, `/weather/v1/daily/${LAT}/${LON}?days=7&localTime=true&lang=zh`),
  ]);
  const [air, alert, indices] = await Promise.all([
    qwGet(host, key, `/airquality/v1/current/${LAT}/${LON}?lang=zh`).catch(() => null),
    qwGet(host, key, `/weatheralert/v1/current/${LAT}/${LON}?lang=zh`).catch(() => null),
    qwGet(host, key, `/v7/indices/1d?type=1,2,3,5,8&location=${LON},${LAT}&lang=zh`).catch(() => null),
  ]);
  return normalize({ current, hourly, daily, air, alert, indices });
}
