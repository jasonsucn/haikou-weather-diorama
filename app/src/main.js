// Entry point: Three.js scene, city, weather, timeline, interaction.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { loadCity, updateCity } from './city.js';
import { initUI, windName } from './ui.js';
import {
  createSky, createSea, createRain, createBirds, updateBirds,
  flashLightning, createLights, updateSky,
} from './effects.js';
import { SoundEngine } from './sound.js';
import {
  getCredentials, saveCredentials, clearCredentials, fetchDirect,
} from './weather-client.js';

const HOME_POS = new THREE.Vector3(-142, 168, 182);
const HOME_TARGET = new THREE.Vector3(0, 8, 0);

const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.18;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xb8d4e6, 0.0007);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 10, 4000);
camera.position.copy(HOME_POS);

const controls = new OrbitControls(camera, canvas);
controls.target.copy(HOME_TARGET);
controls.minPolarAngle = 0.18;
controls.maxPolarAngle = Math.PI / 2 - 0.05;
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.enablePan = false;
controls.minDistance = 62;
controls.maxDistance = 620;
controls.maxPolarAngle = Math.PI * 0.48;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.35;

const lights = createLights(scene);
const sky = createSky(scene);
const sound = new SoundEngine();

let city = null;
let seaMat = null;
let rain = null;
let birds = [];
let data = null;
let mode = 'hour';
let hourItems = [];
let dayItems = [];
let items = [];
let index = 0;
let playing = false;
let playTimer = 0;
let demo = false;
let demoIndex = 0;
let demoClock = 0;
let forceNight = null;
let nightFactor = 0;
let currentHour = new Date().getHours();
let sunDir = new THREE.Vector3(0.4, 0.7, 0.4).normalize();
let camTween = null;
let proxies = [];
let hovered = null;
let ray = new THREE.Raycaster();
let pointer = new THREE.Vector2();
let downAt = null;
let mutedOnce = false;

const cityLights = [];
for (const [x, y, z] of [[-52, 22, 46], [-54, 10, 2], [18, 8, -30], [50, 14, -26]]) {
  const l = new THREE.PointLight(0xffc98a, 0, 110, 2);
  l.position.set(x, y, z);
  scene.add(l);
  cityLights.push(l);
}

// ---------------------------------------------------------------- UI handlers
const ui = initUI({
  onSound: () => {
    sound.unlock();
    sound.setEnabled(!sound.enabled);
    ui.setSound(sound.enabled);
    ui.toast(sound.enabled ? '声音已开启' : '已静音');
  },
  onNight: () => {
    forceNight = nightFactor > 0.5 ? false : true;
    applyLighting(currentHour, weatherState?.cloud ?? 30);
    ui.toast(forceNight ? '切换到夜晚' : '切换到白天');
  },
  onDemo: () => {
    demo = !demo;
    demoIndex = 0;
    demoClock = 0;
    ui.setDemo(demo);
    if (demo) {
      stopPlaying();
      ui.toast('天气演示：晴 → 多云 → 小雨 → 雷雨 → 雾');
      stepDemo();
      scheduleDemo();
    } else {
      clearTimeout(demoTimerId);
      ui.toast('已退出演示');
      if (data) { applyWeather(data.current, hourOf(data.current.time)); ui.setLive(data); }
    }
  },
  onKey: () => openKeyModal(),
  onMode: (m) => {
    mode = m;
    index = 0;
    applyTimeline();
  },
  onScrub: (i) => {
    stopPlaying();
    demo = false; ui.setDemo(false);
    index = i;
    applyTimeline();
  },
  onPlay: () => {
    if (playing) stopPlaying();
    else startPlaying();
  },
  onLandmark: (name, btn) => {
    const lm = city?.landmarks.find((l) => l.name === name);
    if (!lm) { ui.toast('地标尚未载入'); return; }
    focusLandmark(lm);
    ui.setActive(name);
    const c = weatherState || data?.current || {};
    const text = `${Math.round(c.temp ?? 0)}° ${c.text ?? ''} · 风 ${windName(c.windDeg, c.windDir)} ${c.windSpeed?.toFixed?.(1) ?? '--'} m/s · 湿度 ${c.humidity ?? '--'}%`;
    ui.showLandmark(lm, text, lm.sub);
  },
  onLandmarkClose: () => { ui.setActive(null); },
  onReset: () => {
    ui.hideLandmark();
    ui.setActive(null);
    tweenCamera(HOME_POS.clone(), HOME_TARGET.clone());
  },
});

// ---------------------------------------------------------------- key modal wiring
document.getElementById('keyClose')?.addEventListener('click', closeKeyModal);
document.getElementById('keyModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'keyModal') closeKeyModal();
});
document.getElementById('keyClear')?.addEventListener('click', () => {
  clearCredentials();
  document.getElementById('keyHost').value = '';
  document.getElementById('keySecret').value = '';
  document.getElementById('keyStatus').textContent = '已清除本机 KEY';
  useDirect = false;
  ui.toast('已清除本机天气 KEY');
});
document.getElementById('keySave')?.addEventListener('click', async () => {
  const host = document.getElementById('keyHost').value.trim();
  const key = document.getElementById('keySecret').value.trim();
  const st = document.getElementById('keyStatus');
  if (!host || !key) { st.textContent = '请填写 API Host 和 KEY'; return; }
  saveCredentials(host, key);
  st.textContent = '正在验证…';
  try {
    data = await fetchDirect(host, key);
    useDirect = true;
    ui.setLive(data);
    buildTimeline();
    applyWeather(data.current, hourOf(data.current.time));
    ui.toast('已连接和风天气 · 真实数据');
    st.textContent = '连接成功！';
    setTimeout(closeKeyModal, 600);
  } catch (e) {
    st.textContent = '连接失败：' + (e.message || '请检查 KEY');
    ui.toast('连接失败，请检查 Host/KEY');
  }
});

// ---------------------------------------------------------------- weather helpers
let weatherState = null;

function hourOf(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? new Date().getHours() : d.getHours();
}

function family(code) {
  const c = Number(code);
  if (c >= 300 && c < 400) {
    if ([302, 303, 304].includes(c)) return 'thunder';
    return 'rain';
  }
  if (c >= 400 && c < 500) return 'snow';
  if (c >= 500 && c < 600) return 'fog';
  if ([100, 150].includes(c)) return 'sunny';
  if ([103, 153].includes(c)) return 'partly';
  return 'cloudy';
}

function rainLevel(w) {
  const fam = family(w.code);
  if (fam === 'rain' || fam === 'thunder') {
    const rate = w.precipRate ?? 0;
    const byCode = { 300: 2, 301: 5, 305: 1.6, 306: 3.2, 307: 8, 308: 14, 309: 0.8, 310: 16, 311: 22, 312: 28, 313: 3, 314: 4, 315: 8, 316: 12, 317: 18, 318: 24, 302: 6, 303: 12, 304: 8 };
    const v = Math.max(rate, byCode[Number(w.code)] ?? 1.5);
    return THREE.MathUtils.clamp(v / 10, 0.25, 1);
  }
  if (fam === 'snow') return 0.25;
  return 0;
}

function applyWeather(w, hour) {
  weatherState = w;
  currentHour = hour;
  const fam = family(w.code);
  const rainAmt = rainLevel(w);
  const windVec = new THREE.Vector2(
    Math.sin(THREE.MathUtils.degToRad((w.windDeg ?? 0) + 180)) * (w.windSpeed ?? 4),
    Math.cos(THREE.MathUtils.degToRad((w.windDeg ?? 0) + 180)) * (w.windSpeed ?? 4)
  );

  if (rain) {
    rain.material.uniforms.uOpacity.value = rainAmt > 0 ? 0.48 + rainAmt * 0.52 : 0;
    rain.material.uniforms.uWind.value.set(windVec.x * 0.06, windVec.y * 0.06);
    const count = Math.floor(rain.maxCount * (rainAmt > 0 ? Math.max(0.55, rainAmt) : 0));
    rain.geo.setDrawRange(0, count * 2);
  }

  if (seaMat) {
    seaMat.uniforms.uWind.value = THREE.MathUtils.clamp((w.windSpeed ?? 4) / 10, 0.25, 1.8);
  }

  const vis = w.visibility ?? 20000;
  const density = THREE.MathUtils.clamp(1.15 / Math.max(vis, 600), 0.00022, 0.0036) + rainAmt * 0.00035;
  scene.fog.density = density;

  // clouds scale/opacity
  const cloud = THREE.MathUtils.clamp((w.cloud ?? 30) / 100, 0.05, 1);
  if (city) {
    for (const c of city.clouds) {
      const s = 0.6 + cloud * 0.9;
      c.scale.setScalar(s);
      c.traverse((o) => { if (o.isMesh) o.material.opacity = 0.35 + cloud * 0.6; });
    }
  }

  applyLighting(hour, w.cloud ?? 30);
  sound.setWeather({ rain: rainAmt, wind: w.windSpeed ?? 4, night: nightFactor > 0.5 });
}

function applyLighting(hour, cloud) {
  if (forceNight === false) hour = 12;
  if (forceNight === true) hour = 22;
  const rise = data?.astro?.sunrise ? hourOf(data.astro.sunrise) : 6.8;
  const set = data?.astro?.sunset ? hourOf(data.astro.sunset) : 18.2;
  let day = hour >= rise && hour < set;
  if (forceNight !== null) day = !forceNight;
  nightFactor = day ? 0 : 1;
  const frac = THREE.MathUtils.clamp((hour - rise) / Math.max(0.1, set - rise), 0, 1);
  const elev = Math.sin(frac * Math.PI) * 1.05;
  const az = -2.35 + frac * 4.0;
  sunDir.set(Math.cos(elev) * Math.sin(az), Math.sin(elev), Math.cos(elev) * Math.cos(az)).normalize();
  if (!day) sunDir.set(0.35, 0.55, -0.5).normalize();

  lights.sun.position.copy(sunDir).multiplyScalar(320);
  lights.sun.intensity = day ? 2.4 + Math.sin(frac * Math.PI) * 1.4 : 0.22;
  lights.sun.color.set(day ? (frac < 0.14 || frac > 0.86 ? '#ffb27a' : '#fff0d6') : '#8fb6d8');
  lights.hemi.intensity = day ? 1.1 : 0.28;
  lights.rim.intensity = day ? 0.45 : 0.18;
  renderer.toneMappingExposure = day ? 1.18 : 0.86;

  for (const l of cityLights) l.intensity = day ? 0 : 85;
  if (city) {
    for (const c of city.cars) (c.userData.lights || []).forEach((l) => { l.visible = !day; });
    for (const b of city.boats) if (b.userData.light) b.userData.light.visible = !day;
  }
  if (city?.merged) {
    for (const mesh of city.merged.children) {
      const m = mesh.material;
      if (!m) continue;
      if (m.name === 'window' || m.name === 'glass') {
        m.emissive = m.emissive || new THREE.Color();
        m.emissive.set(day ? '#000000' : '#ffcc88');
        m.emissiveIntensity = day ? 0 : 1.1;
      } else if (m.name === 'cream' || m.name === 'white') {
        m.emissive = m.emissive || new THREE.Color();
        m.emissive.set(day ? '#000000' : '#5a4630');
        m.emissiveIntensity = day ? 0 : 0.08;
      }
    }
  }

  const wet = weatherState ? rainLevel(weatherState) : 0;
  const wetSky = Math.min(1, wet * 2.5);
  if (!day) {
    lights.sun.intensity *= 1;
  } else if (wet > 0) {
    lights.sun.intensity *= 1 - wetSky * 0.7;
    lights.hemi.intensity *= 1 - wetSky * 0.4;
    renderer.toneMappingExposure = 1.18 * (1 - wetSky * 0.24);
    scene.fog.color.lerp(new THREE.Color('#9fb2bd'), wetSky * 0.8);
  }
  if (sky) {
    updateSky(sky, sunDir, nightFactor, Math.max((cloud ?? 30) / 100, wet * 0.8));
    if (wet > 0) {
      sky.material.uniforms.uTop.value.lerp(new THREE.Color('#46586b'), wetSky * 0.95);
      sky.material.uniforms.uHorizon.value.lerp(new THREE.Color('#8396a4'), wetSky * 0.95);
    }
  }
  if (seaMat) {
    seaMat.uniforms.uSunDir.value.copy(sunDir);
    seaMat.uniforms.uNight.value = nightFactor;
  }
  ui.setNight(!day);
}

function buildTimeline() {
  if (!data) return;
  const c = data.current;
  const nowItem = {
    time: c.time, hour: hourOf(c.time), temp: c.temp, code: c.code, text: c.text,
    precip: c.precip, precipRate: c.precipRate, cloud: c.cloud, humidity: c.humidity,
    windSpeed: c.windSpeed, windDeg: c.windDeg, windDir: c.windDir, visibility: c.visibility,
  };
  hourItems = [nowItem, ...data.hourly].slice(0, 24);
  dayItems = data.daily;
  applyTimeline();
}

function applyTimeline() {
  items = mode === 'hour' ? hourItems : dayItems;
  if (!items.length) return;
  index = THREE.MathUtils.clamp(index, 0, items.length - 1);
  ui.setTimeline(mode, items, index);
  const it = items[index];
  if (mode === 'hour') {
    applyWeather(it, it.hour ?? hourOf(it.time));
  } else {
    applyWeather({
      code: it.code, text: it.text, temp: (it.max + it.min) / 2,
      precip: it.precip, precipRate: it.precip, cloud: it.cloud, humidity: it.humidity ?? 70,
      windSpeed: it.windSpeed ?? 4, windDeg: it.windDeg ?? 90, visibility: 20000,
    }, 12);
  }
  ui.updateTimelineReadout(mode, items, index);
}

function startPlaying() {
  playing = true;
  ui.setPlay(true);
  playTimer = window.setInterval(() => {
    if (!items.length) return;
    index = (index + 1) % items.length;
    applyTimeline();
  }, 1400);
}
function stopPlaying() {
  playing = false;
  ui.setPlay(false);
  clearInterval(playTimer);
}

// ---------------------------------------------------------------- demo
const DEMO = [
  { code: '100', text: '晴', temp: 29, precip: 0, precipRate: 0, cloud: 12, humidity: 62, windSpeed: 4, windDeg: 130, visibility: 30000 },
  { code: '104', text: '多云', temp: 28, precip: 0, precipRate: 0, cloud: 65, humidity: 70, windSpeed: 5, windDeg: 120, visibility: 22000 },
  { code: '305', text: '小雨', temp: 26, precip: 1.2, precipRate: 2.2, cloud: 88, humidity: 86, windSpeed: 6.5, windDeg: 110, visibility: 9000 },
  { code: '302', text: '雷阵雨', temp: 25, precip: 6, precipRate: 11, cloud: 96, humidity: 92, windSpeed: 10, windDeg: 100, visibility: 5000 },
  { code: '501', text: '雾', temp: 24, precip: 0, precipRate: 0, cloud: 55, humidity: 96, windSpeed: 2, windDeg: 80, visibility: 900 },
];
function stepDemo() {
  const d = DEMO[demoIndex % DEMO.length];
  demoIndex += 1;
  applyWeather(d, 15);
  ui.toast(`演示天气 · ${d.text}`);
}

function scheduleDemo() {
  clearTimeout(demoTimerId);
  if (!demo) return;
  demoTimerId = setTimeout(() => {
    if (!demo) return;
    stepDemo();
    scheduleDemo();
  }, 5200);
}

// ---------------------------------------------------------------- camera
function tweenCamera(pos, target, dur = 1.25) {
  camTween = {
    t: 0, dur,
    fromPos: camera.position.clone(), toPos: pos,
    fromTarget: controls.target.clone(), toTarget: target,
  };
  controls.autoRotate = false;
}
function focusLandmark(lm) {
  const dir = camera.position.clone().sub(controls.target).normalize();
  const dist = Math.max(70, lm.radius * 2.15 + 26);
  const pos = lm.center.clone().add(dir.multiplyScalar(dist));
  pos.y = lm.center.y + dist * 0.42;
  tweenCamera(pos, lm.center.clone());
}

function updateCamera(dt) {
  if (!camTween) {
    controls.update();
    return;
  }
  camTween.t += dt;
  const k = Math.min(1, camTween.t / camTween.dur);
  const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
  camera.position.lerpVectors(camTween.fromPos, camTween.toPos, e);
  controls.target.lerpVectors(camTween.fromTarget, camTween.toTarget, e);
  controls.update();
  if (k >= 1) {
    camTween = null;
    controls.autoRotate = true;
  }
}

// ---------------------------------------------------------------- picking
function makeProxies() {
  if (!city) return;
  for (const lm of city.landmarks) {
    const geo = new THREE.SphereGeometry(Math.max(9, lm.radius * 0.65), 12, 10);
    const mat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
    const p = new THREE.Mesh(geo, mat);
    p.position.copy(lm.center);
    p.userData.landmark = lm;
    scene.add(p);
    proxies.push(p);
  }
}

function updatePointer(e) {
  pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
  pointer.y = -(e.clientY / window.innerHeight) * 2 + 1;
}

canvas.addEventListener('pointermove', (e) => {
  updatePointer(e);
  if (!proxies.length) return;
  ray.setFromCamera(pointer, camera);
  const hit = ray.intersectObjects(proxies, false)[0];
  if (hit) {
    const lm = hit.object.userData.landmark;
    hovered = lm;
    const tip = document.getElementById('tip');
    tip.textContent = `${lm.title} · 点击查看`;
    tip.style.left = `${e.clientX}px`;
    tip.style.top = `${e.clientY}px`;
    tip.classList.add('show');
    canvas.style.cursor = 'pointer';
  } else {
    hovered = null;
    document.getElementById('tip').classList.remove('show');
    canvas.style.cursor = 'grab';
  }
});

canvas.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY }; });
canvas.addEventListener('pointerup', (e) => {
  if (!downAt) return;
  const moved = Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y);
  downAt = null;
  if (moved > 6) return;
  updatePointer(e);
  ray.setFromCamera(pointer, camera);
  const hit = proxies.length ? ray.intersectObjects(proxies, false)[0] : null;
  if (hit) {
    const lm = hit.object.userData.landmark;
    const found = city.landmarks.find((l) => l.name === lm.name);
    if (found) {
      focusLandmark(found);
      ui.setActive(found.name);
      const c = weatherState || data?.current || {};
      ui.showLandmark(found, `${Math.round(c.temp ?? 0)}° ${c.text ?? ''} · 风 ${windName(c.windDeg, c.windDir)} ${c.windSpeed?.toFixed?.(1) ?? '--'} m/s`, found.sub);
    }
  }
});

// ---------------------------------------------------------------- sound unlock
function unlockSound() {
  if (!sound.unlocked) {
    sound.unlock();
    sound.setEnabled(true);
    ui.setSound(true);
    if (!mutedOnce) { ui.toast('🔊 声音已开启 · 点击右上角可静音'); mutedOnce = true; }
  }
}
document.addEventListener('pointerdown', unlockSound, { once: true });
document.addEventListener('keydown', unlockSound, { once: true });

// ---------------------------------------------------------------- load
// Local server mode (server.mjs proxy) is preferred. On static hosting
// (GitHub Pages) /api/* is unavailable, so use the user's own key — stored
// only in their browser — to fetch straight from QWeather.
let useDirect = false;
async function fetchWeather() {
  ui.setLoading('连接和风天气…');
  const forceDirect = new URLSearchParams(location.search).has('direct');
  try {
    if (forceDirect) throw new Error('direct forced');
    const res = await fetch('/api/weather/summary', { signal: AbortSignal.timeout(4000) });
    const ct = res.headers.get('content-type') || '';
    if (!res.ok || !ct.includes('json')) throw new Error('no local proxy');
    const json = await res.json();
    if (!json.ok) throw new Error(json.error || 'API error');
    data = json;
    useDirect = false;
  } catch (err) {
    const { host, key } = getCredentials();
    if (host && key) {
      try {
        ui.setLoading('直连和风天气…');
        data = await fetchDirect(host, key);
        useDirect = true;
      } catch (e2) {
        console.warn('[weather] direct failed', e2);
        data = fallbackData();
        ui.toast('直连失败：' + (e2.message || '请检查 KEY') + '，已用演示数据');
        openKeyModal('直连失败，请检查 Host/KEY 后重试');
      }
    } else {
      data = fallbackData();
      ui.toast('在线版需设置你的和风天气 KEY，点击右上角⚙');
      openKeyModal();
    }
  }
  ui.setLive(data);
  buildTimeline();
  applyWeather(data.current, hourOf(data.current.time));
}

function openKeyModal(msg = '') {
  const m = document.getElementById('keyModal');
  if (!m) return;
  const { host, key } = getCredentials();
  document.getElementById('keyHost').value = host;
  document.getElementById('keySecret').value = key;
  const st = document.getElementById('keyStatus');
  if (st) st.textContent = msg || '';
  const intro = document.getElementById('keyIntro');
  if (intro) intro.textContent = useDirect
    ? '当前使用你自己的 KEY 直连和风天气。KEY 只保存在此浏览器，不会上传。'
    : '在线版没有服务端代理，填入你自己的和风天气 KEY 即可获取真实天气。KEY 只保存在此浏览器，不会上传。';
  m.hidden = false;
}
function closeKeyModal() {
  const m = document.getElementById('keyModal');
  if (m) m.hidden = true;
}

function fallbackData() {
  const now = new Date();
  const iso = now.toISOString();
  const hourly = Array.from({ length: 24 }, (_, i) => {
    const d = new Date(now.getTime() + i * 3600e3);
    return {
      time: d.toISOString(), hour: d.getHours(), temp: 27 + Math.sin(i / 4) * 2,
      code: i % 7 === 0 ? '305' : '103', text: i % 7 === 0 ? '小雨' : '晴间多云',
      precip: i % 7 === 0 ? 0.6 : 0, precipRate: i % 7 === 0 ? 1.2 : 0,
      cloud: i % 7 === 0 ? 80 : 30, humidity: 75, windSpeed: 4.5, windDeg: 120, visibility: 20000,
    };
  });
  const daily = Array.from({ length: 7 }, (_, i) => ({
    date: new Date(now.getTime() + i * 86400e3).toISOString().slice(0, 10),
    code: i % 3 === 0 ? '305' : '104', text: i % 3 === 0 ? '小雨' : '多云',
    max: 30 - i * 0.3, min: 24, precip: i % 3 === 0 ? 2 : 0, precipProb: i % 3 === 0 ? 60 : 20,
    cloud: 60, humidity: 76, windScale: 3, windSpeed: 4.5, windDeg: 120,
    sunrise: null, sunset: null,
  }));
  return {
    ok: true, degraded: true, fetchedAt: now.toISOString(), city: { name: '海口' },
    current: { time: iso, temp: 27.5, feels: 29, humidity: 75, windSpeed: 4.5, windScale: 3, windDeg: 120, windDir: 'se', precip: 0, precipRate: 0, cloud: 40, visibility: 22000, pressure: 1012, uv: 5, code: '103', text: '晴间多云' },
    astro: { sunrise: null, sunset: null }, hourly, daily,
    air: { aqi: 32, display: '32', category: '优' }, alerts: [], indices: [],
  };
}

async function boot() {
  try {
    ui.setLoading('载入微缩城市模型…');
    const [rig] = await Promise.all([loadCity(scene, (s) => ui.setLoading(s))]);
    city = rig;
    if (city.sea) seaMat = createSea(city.sea, scene);
    rain = createRain(scene, window.innerWidth < 860 ? 2500 : 6000);
    birds = createBirds(scene);
    makeProxies();
    const windShaders = [];
    for (const mesh of city.merged?.children || []) {
      const m = mesh.material;
      if (!m || !['leaf', 'meadow'].includes(m.name)) continue;
      m.onBeforeCompile = (shader) => {
        shader.uniforms.uWindTime = { value: 0 };
        shader.vertexShader = 'uniform float uWindTime;\n' + shader.vertexShader.replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
           float hgt = max(position.y - 3.0, 0.0);
           float sway = sin(uWindTime * 1.25 + position.x * 0.18 + position.z * 0.22);
           transformed.x += sway * hgt * 0.007;
           transformed.z += cos(uWindTime * 0.9 + position.x * 0.2) * hgt * 0.005;`
        );
        windShaders.push(shader);
      };
      m.needsUpdate = true;
    }
    city.windShaders = windShaders;
    city.lavaMaterials = [];
    for (const mesh of city.merged?.children || []) {
      const m = mesh.material;
      if (m && m.name === 'lava') city.lavaMaterials.push(m);
    }
    for (const c of city.clouds) c.traverse((o) => {
      if (o.isMesh) {
        o.material = new THREE.MeshBasicMaterial({ color: 0xf4f9ff, transparent: true, opacity: 0.9 });
      }
    });

    await fetchWeather();
    const forced = new URLSearchParams(location.search).get('wx');
    if (forced) {
      const map = { rain: 2, thunder: 3, fog: 4, cloudy: 1, sunny: 0 };
      const p = DEMO[map[forced] ?? 0];
      applyWeather(p, 15);
      ui.toast('演示天气 · ' + p.text);
      if (forced === 'night') { forceNight = true; applyLighting(22, p.cloud); }
    }
    ui.hideLoading();
    setTimeout(() => ui.toast(city.placeholder ? '模型加载中 · 先展示占位城市' : '拖拽旋转 · 滚轮缩放 · 点击地标查看'), 900);
  } catch (err) {
    console.error(err);
    ui.setLoading('加载失败：' + (err.message || err));
    ui.toast('加载失败，请刷新重试');
  }
}

// Deterministic camera for multi-angle QA: ?az=<0..359>&elev=<height>&dist=<radius>.
// Only active when ?az is present; the default view is untouched.
{
  const q = new URLSearchParams(location.search);
  const az = q.get('az');
  if (az !== null) {
    const deg = Number(az) || 0;
    const elev = Number(q.get('elev') || 120);
    const dist = Number(q.get('dist') || 245);
    const rad = (deg * Math.PI) / 180;
    const horiz = Math.sqrt(Math.max(1, dist * dist - elev * elev));
    controls.autoRotate = false;
    camera.position.set(Math.sin(rad) * horiz, elev, Math.cos(rad) * horiz);
    controls.target.set(0, 8, 0);
    controls.update();
  }
}

// ---------------------------------------------------------------- loop
const showFps = new URLSearchParams(location.search).has('fps');
const showQa = new URLSearchParams(location.search).has('qa');
if (showQa) {
  const el = document.createElement('div');
  el.id = 'qaHud';
  el.style.cssText = 'position:fixed;left:12px;bottom:44px;z-index:9998;padding:6px 10px;border-radius:8px;background:rgba(8,18,28,.9);color:#9ef5c8;font:12px/1.55 monospace;white-space:pre';
  document.body.appendChild(el);
  setInterval(() => {
    const b = city && city.bridge;
    if (!b) { el.textContent = 'bridge QA loading...'; return; }
    const perp = new THREE.Vector3(-b.axis.z, 0, b.axis.x);
    let maxA = 0, maxL = 0, bad = 0;
    for (const c of city.cars) {
      const dx = c.position.x - b.center.x;
      const dz = c.position.z - b.center.z;
      const along = Math.abs(dx * b.axis.x + dz * b.axis.z);
      const lat = Math.abs(dx * perp.x + dz * perp.z);
      maxA = Math.max(maxA, along); maxL = Math.max(maxL, lat);
      if (along + 1.9 > b.halfLength || lat + 1.0 > b.halfWidth) bad += 1;
    }
    el.textContent = `cars ${city.cars.length} outside ${bad}\nmax along ${maxA.toFixed(1)} / 20\nmax lat ${maxL.toFixed(1)} / 4.3`;
  }, 300);
}

const showAudio = new URLSearchParams(location.search).has('audio');
if (showAudio) {
  const el = document.createElement('div');
  el.id = 'audioHud';
  el.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:9998;padding:6px 10px;border-radius:8px;background:rgba(8,18,28,.85);color:#9fd8ff;font:12px/1.5 monospace';
  document.body.appendChild(el);
  setInterval(() => {
    el.textContent = `audio ${sound.enabled ? 'ON' : 'OFF'} · ${sound.unlocked ? 'unlocked' : 'locked'} · ctx ${sound.ctx?.state || '-'}\nmaster ${sound.master?.gain?.value?.toFixed(2) ?? '-'} ocean ${sound.oceanGain?.gain?.value?.toFixed(2) ?? '-'}\nwind ${sound.windGain?.gain?.value?.toFixed(2) ?? '-'} rain ${sound.rainGain?.gain?.value?.toFixed(2) ?? '-'}`;
  }, 500);
}
let fpsFrames = 0, fpsAcc = 0, fpsEl = null;
if (showFps) {
  fpsEl = document.createElement('div');
  fpsEl.id = 'fpsHud';
  fpsEl.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:9998;padding:6px 10px;border-radius:8px;background:rgba(8,18,28,.85);color:#9fe3b0;font:12px/1.5 monospace';
  document.body.appendChild(fpsEl);
}
const clock = new THREE.Clock();
let demoTimer = 0;
let demoTimerId = 0;
let lightningTimer = 0;

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;

  if (city) updateCity(city, t, dt, weatherState || {});
  if (birds.length) updateBirds(birds, t);
  if (rain) {
    rain.material.uniforms.uTime.value = t;
    if (rain.geo.drawRange.count > 0) {
      // keep draw range; shader animates
    }
  }
  if (seaMat) seaMat.uniforms.uTime.value = t;
  for (const sh of city?.windShaders || []) if (sh.uniforms?.uWindTime) sh.uniforms.uWindTime.value = t;
  if (city?.lavaMaterials?.length) {
    const pulse = 0.85 + 0.3 * Math.sin(t * 1.6) + 0.12 * Math.sin(t * 4.3);
    for (const m of city.lavaMaterials) {
      m.emissive = m.emissive || new THREE.Color();
      m.emissive.set('#ff7020');
      m.emissiveIntensity = pulse;
      if (m.color) m.color.set('#7a1e08');
    }
  }
  if (sky) sky.material.uniforms.uSunDir.value.copy(sunDir);


  if (weatherState && family(weatherState.code) === 'thunder') {
    lightningTimer -= dt;
    if (lightningTimer <= 0) {
      lightningTimer = 7 + Math.random() * 9;
      flashLightning(0.8 + Math.random() * 0.6);
      sound.thunder();
    }
  }

  sound.update(dt);
  updateCamera(dt);
  renderer.render(scene, camera);
  if (fpsEl) {
    fpsFrames += 1;
    fpsAcc += dt;
    if (fpsAcc >= 0.5) {
      const fps = Math.round(fpsFrames / fpsAcc);
      fpsEl.textContent = `FPS ${fps} · calls ${renderer.info.render.calls} · tris ${(renderer.info.render.triangles / 1000).toFixed(1)}k`;
      fpsFrames = 0; fpsAcc = 0;
    }
  }
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
});

boot();
animate();
