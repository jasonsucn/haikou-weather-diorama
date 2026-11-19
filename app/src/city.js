// Loads the Haikou GLB, merges static meshes by material, exposes animated rigs.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as BGU from 'three/addons/utils/BufferGeometryUtils.js';

const ANIMATED = /^(Car_\d+|Boat_\d+|Palm_\d+|Cloud_\d+|Sailboat_\d+)/;
const LANDMARK_NAMES = [
  ['CenturyBridge|Bridge|Bridge_Tower_L|Bridge_Root', '世纪大桥', '主跨斜拉桥 · 海口湾地标'],
  ['Arcade_01', '骑楼老街', '连续拱廊 · 南洋商街'],
  ['ClockTower', '海口钟楼', '红砖基座 · 四面钟'],
  ['Library', '云洞图书馆', '白色壳体 · 面朝大海'],
  ['Park', '万绿园', '城市绿肺 · 椰林草坪'],
  ['Volcano', '火山口', '热带火山地貌'],
  ['Haidian', '海甸岛', '椰林渔村 · 灯塔'],
];

function nameOf(obj) { return obj?.name || ''; }

function insideAnimated(obj) {
  let p = obj;
  while (p) {
    if (ANIMATED.test(nameOf(p))) return true;
    p = p.parent;
  }
  return false;
}

function landmarkPose(root, name) {
  let node = null;
  for (const n of name.split('|')) {
    node = root.getObjectByName(n);
    if (node) break;
  }
  if (!node) return null;
  const box = new THREE.Box3().setFromObject(node);
  if (name.startsWith('CenturyBridge')) {
    for (const extra of ['Bridge_Tower_L', 'Bridge_Tower_R', 'Bridge_Deck']) {
      const o = root.getObjectByName(extra);
      if (o) box.expandByObject(o);
    }
  }
  let lighthouseCenter = null;
  if (name === 'Haidian') {
    const lighthouse = root.getObjectByName('Lighthouse');
    if (lighthouse) {
      lighthouseCenter = new THREE.Vector3();
      lighthouse.getWorldPosition(lighthouseCenter);
      box.expandByObject(lighthouse);
    }
  }
  if (box.isEmpty()) return null;
  const center = box.getCenter(new THREE.Vector3());
  if (lighthouseCenter) center.lerp(lighthouseCenter, 0.55);
  const size = box.getSize(new THREE.Vector3());
  return { name, center, size, radius: Math.max(size.x, size.z, size.y) * 0.55 + 4 };
}

function mergeStatic(root, sea) {
  const buckets = new Map();
  const remove = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh || o === sea) return;
    if (insideAnimated(o)) return;
    const mat = Array.isArray(o.material) ? o.material[0] : o.material;
    if (!mat) return;
    let g = o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    if (g.index) g = g.toNonIndexed();
    for (const key of Object.keys(g.attributes)) {
      if (key !== 'position' && key !== 'normal') g.deleteAttribute(key);
    }
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!buckets.has(mat.uuid)) buckets.set(mat.uuid, { mat, list: [] });
    buckets.get(mat.uuid).list.push(g);
    remove.push(o);
  });

  const group = new THREE.Group();
  group.name = 'StaticCity';
  for (const { mat, list } of buckets.values()) {
    if (!list.length) continue;
    const merged = list.length === 1 ? list[0] : BGU.mergeGeometries(list, false);
    if (!merged) continue;
    const mesh = new THREE.Mesh(merged, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  for (const o of remove) o.removeFromParent();
  return group;
}


function mergeChildren(group) {
  group.updateWorldMatrix(true, true);
  const inv = new THREE.Matrix4().copy(group.matrixWorld).invert();
  const buckets = new Map();
  const meshes = [];
  group.traverse((o) => { if (o.isMesh) meshes.push(o); });
  for (const o of meshes) {
    const mat = Array.isArray(o.material) ? o.material[0] : o.material;
    if (!mat) continue;
    let g = o.geometry.clone();
    g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    if (g.index) g = g.toNonIndexed();
    for (const key of Object.keys(g.attributes)) {
      if (key !== 'position' && key !== 'normal') g.deleteAttribute(key);
    }
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!buckets.has(mat.uuid)) buckets.set(mat.uuid, { mat, list: [] });
    buckets.get(mat.uuid).list.push(g);
    o.removeFromParent();
  }
  for (const { mat, list } of buckets.values()) {
    if (!list.length) continue;
    const merged = list.length === 1 ? list[0] : BGU.mergeGeometries(list, false);
    if (!merged) continue;
    const mesh = new THREE.Mesh(merged, mat);
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    group.add(mesh);
  }
}


function glowTexture() {
  if (glowTexture._tex) return glowTexture._tex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 1, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,232,180,1)');
  grd.addColorStop(0.35, 'rgba(255,196,110,0.55)');
  grd.addColorStop(1, 'rgba(255,170,70,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c);
  glowTexture._tex = tex;
  return tex;
}

function makeGlow(scale = 2.2) {
  const mat = new THREE.SpriteMaterial({
    map: glowTexture(), color: 0xffd6a0, transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const sp = new THREE.Sprite(mat);
  sp.scale.setScalar(scale);
  return sp;
}
function buildPlaceholder() {
  const g = new THREE.Group();
  g.name = 'PlaceholderCity';
  const base = new THREE.Mesh(new THREE.CylinderGeometry(112, 112, 8, 64), new THREE.MeshStandardMaterial({ color: 0x7a6247, roughness: 0.8 }));
  base.position.y = -3;
  const island = new THREE.Mesh(new THREE.CylinderGeometry(84, 88, 6, 48), new THREE.MeshStandardMaterial({ color: 0x67954b, roughness: 0.9 }));
  island.position.y = 3;
  const sea = new THREE.Mesh(new THREE.CylinderGeometry(107, 107, 1, 64), new THREE.MeshStandardMaterial({ color: 0x1c6a83, roughness: 0.2 }));
  sea.name = 'Sea';
  sea.position.y = 1.6;
  g.add(base, sea, island);
  return { root: g, sea, landmarks: [], cars: [], boats: [], palms: [], clouds: [], sailboats: [], merged: null, placeholder: true };
}

export async function loadCity(scene, onStatus = () => {}) {
  const loader = new GLTFLoader();
  let gltf = null;
  try {
    onStatus('载入微缩城市模型…');
    gltf = await loader.loadAsync(new URL('../assets/models/haikou_v1.glb', import.meta.url).href);
  } catch (err) {
    console.warn('[city] GLB failed, placeholder used', err);
    const ph = buildPlaceholder();
    scene.add(ph.root);
    return ph;
  }

  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const sea = root.getObjectByName('Sea');

  // `Coastal_Shallow` is a thin ring at exactly the same height as the Sea top
  // surface (both y≈1.08). The two coplanar surfaces z-fight; at grazing angles
  // the sea's warm specular and the ring's blue stipple blend into tan/ochre
  // patches that look like the base punching through the water. The shader
  // already draws a shore gradient, so the ring is redundant — drop it.
  const shallow = root.getObjectByName('Coastal_Shallow');
  if (shallow) shallow.parent?.remove(shallow);
  // `Shore_Sand` sits at y=1.10 versus the sea top at y=1.08 — only 0.02 apart.
  // That is enough for mobile depth precision to z-fight, painting tan sand
  // patches over the water. The sea shader already shades the shoreline.
  const beach = root.getObjectByName('Shore_Sand');
  if (beach) beach.parent?.remove(beach);
  // Keep the foam ribbon well clear of the sea surface.
  const foamRing = root.getObjectByName('Foam');
  if (foamRing) foamRing.position.y += 0.15;

  const landmarks = [];
  for (const [node, title, sub] of LANDMARK_NAMES) {
    const pose = landmarkPose(root, node);
    if (pose) landmarks.push({ ...pose, name: node.split('|')[0], title, sub });
  }

  const pad2 = (n) => String(n).padStart(2, '0');
  const defs = [
    { key: 'cars', re: /^Car_.*?(\d{2})(?:_|$)/, name: (i) => `Car_${pad2(i)}` },
    { key: 'boats', re: /^Boat_.*?(\d{2})(?:_|$)/, name: (i) => `Boat_${pad2(i)}` },
    { key: 'palms', re: /^Palm_.*?(\d{2})(?:_|$)/, name: (i) => `Palm_${pad2(i)}` },
    { key: 'clouds', re: /^Cloud_(\d+)/, name: (i) => `Cloud_${i}` },
    { key: 'sailboats', re: /^Sail_(\d{2})/, name: (i) => `Sail_${pad2(i)}` },
  ];
  const buckets = new Map();
  root.traverse((o) => {
    const n = nameOf(o);
    if (!n) return;
    for (const d of defs) {
      const m = n.match(d.re);
      if (!m) continue;
      const key = `${d.key}:${Number(m[1])}`;
      if (!buckets.has(key)) buckets.set(key, { def: d, idx: Number(m[1]), parts: [] });
      buckets.get(key).parts.push(o);
      break;
    }
  });

  const groups = { cars: [], boats: [], palms: [], clouds: [], sailboats: [] };
  root.updateMatrixWorld(true);
  for (const { def, idx, parts } of buckets.values()) {
    const rootName = def.name(idx);
    const body = parts.find((p) => p.name === rootName) || parts[0];
    const wp = new THREE.Vector3();
    body.getWorldPosition(wp);
    const group = new THREE.Group();
    group.name = rootName;
    group.position.copy(wp);
    scene.add(group);
    group.updateMatrixWorld(true);
    for (const part of parts) group.attach(part);
    group.userData.base = wp.clone();
    group.userData.phase = Math.random() * Math.PI * 2;
    group.userData.dir = Math.random() < 0.5 ? -1 : 1;
    group.userData.speed = 0.8 + Math.random() * 0.6;
    group.userData.radius = 1.0 + Math.random() * 1.8;
    group.userData.boatSpeed = 0.10 + Math.random() * 0.10;
    group.userData.baseRot = group.rotation.clone();
    groups[def.key].push(group);
    try { mergeChildren(group); } catch (e) { console.warn('[city] merge group failed', group.name, e); }
  }

  const cars = groups.cars;
  const boats = groups.boats;
  const palms = groups.palms;
  const clouds = groups.clouds;
  const sailboats = groups.sailboats;

  onStatus('整理城市几何…');
  const merged = mergeStatic(root, sea);
  scene.add(merged);
  scene.add(root);

  // bridge travel axis (glTF Y-up): from the asset QA note
  const bridgeAxis = new THREE.Vector3(0.9205, 0, 0.3907).normalize();
  const perp = new THREE.Vector3(-bridgeAxis.z, 0, bridgeAxis.x);
  let bridgeCenter = new THREE.Vector3(-35.5, 13.9, -45.5);
  let bridgeDir = bridgeAxis.clone();
  const tl = root.getObjectByName('Bridge_Tower_L');
  const tr = root.getObjectByName('Bridge_Tower_R');
  if (tl && tr) {
    const a = new THREE.Vector3(); const b = new THREE.Vector3();
    tl.getWorldPosition(a); tr.getWorldPosition(b);
    const d = b.clone().sub(a); d.y = 0;
    if (d.lengthSq() > 1e-4) bridgeDir = d.normalize();
  }
  const deck = root.getObjectByName('Bridge_Deck');
  if (deck) {
    bridgeCenter = new THREE.Box3().setFromObject(deck).getCenter(new THREE.Vector3());
  }
  for (const c of cars) {
    const lights = [];
    for (const lane of [-0.7, 0.7]) {
      const sp = makeGlow(2.6);
      sp.position.set(1.4, 0.5, lane);
      sp.visible = false;
      c.add(sp);
      lights.push(sp);
    }
    c.userData.lights = lights;
  }
  for (const b of boats) {
    const sp = makeGlow(1.8);
    sp.position.set(0, 1.6, 0);
    sp.visible = false;
    b.add(sp);
    b.userData.light = sp;
  }
  cars.forEach((c, i) => {
    c.userData.axis = bridgeDir.clone();
    c.userData.perp = new THREE.Vector3(-bridgeDir.z, 0, bridgeDir.x);
    c.userData.center = bridgeCenter.clone();
    c.userData.phaseOffset = (i / Math.max(1, cars.length)) * 36 + Math.random() * 1.5;
    c.userData.lane = i % 2 === 0 ? 1.3 : -1.3;
    c.userData.dir = i % 2 === 0 ? 1 : -1;
    c.userData.speed = 5.0 + Math.random() * 2.5;
  });
  for (const b of boats) b.userData.radius = 1.6 + Math.random() * 2.2;
  const bridge = { center: bridgeCenter.clone(), axis: bridgeDir.clone(), halfLength: 20, halfWidth: 4.3 };
  const rig = { root, sea, merged, landmarks, cars, boats, palms, clouds, sailboats, bridge, placeholder: false };

  for (const c of cars) {
    c.userData.baseX = c.position.x;
    c.userData.dir = Math.random() < 0.5 ? -1 : 1;
    c.userData.speed = 2.2 + Math.random() * 1.4;
  }
  for (const b of boats) {
    b.userData.base = b.position.clone();
    b.userData.phase = Math.random() * Math.PI * 2;
    b.userData.radius = 1.2 + Math.random() * 2.2;
    b.userData.speed = 0.05 + Math.random() * 0.08;
  }
  for (const p of palms) {
    p.userData.phase = Math.random() * Math.PI * 2;
    p.userData.baseRot = p.rotation.clone();
  }
  for (const c of clouds) {
    c.userData.base = c.position.clone();
    c.userData.phase = Math.random() * Math.PI * 2;
  }
  for (const s of sailboats) {
    s.userData.base = s.position.clone();
    s.userData.phase = Math.random() * Math.PI * 2;
  }
  return rig;
}

export function updateCity(city, t, dt, state) {
  if (!city) return;
  const wind = state?.windSpeed ?? 5;
  const windAmp = THREE.MathUtils.clamp(wind / 10, 0.3, 1.6);

  for (const c of city.cars) {
    const span = 28;
    const { axis, perp, center, lane, dir, speed, phaseOffset, base } = c.userData;
    const off = (((phaseOffset + t * speed * dir) % span) + span) % span - span / 2;
    c.position.set(
      center.x + axis.x * off + perp.x * lane,
      base.y,
      center.z + axis.z * off + perp.z * lane,
    );
  }

  for (const b of city.boats) {
    const { base, phase, radius } = b.userData;
    const a = t * (b.userData.boatSpeed || 0.08) + phase;
    b.position.x = base.x + Math.cos(a) * radius;
    b.position.z = base.z + Math.sin(a) * radius;
    b.position.y = base.y + Math.sin(t * 1.8 + phase) * 0.34 + 0.12;
    b.rotation.z = Math.sin(t * 1.3 + phase) * 0.09;
    b.rotation.x = Math.sin(t * 0.9 + phase) * 0.07;
  }

  for (const s of city.sailboats) {
    const { base, phase } = s.userData;
    s.position.y = base.y + Math.sin(t * 1.1 + phase) * 0.12;
    s.rotation.z = Math.sin(t * 0.9 + phase) * 0.05;
  }

  for (const p of city.palms) {
    const { phase, baseRot } = p.userData;
    p.rotation.z = baseRot.z + Math.sin(t * 1.3 + phase) * 0.065 * windAmp;
    p.rotation.x = baseRot.x + Math.sin(t * 1.05 + phase * 1.7) * 0.045 * windAmp;
  }

  for (const c of city.clouds) {
    const { base, phase } = c.userData;
    c.position.x = base.x + Math.sin(t * 0.02 + phase) * 10;
    c.position.z = base.z + Math.cos(t * 0.015 + phase) * 6;
    c.position.y = base.y + Math.sin(t * 0.12 + phase) * 0.4;
  }
}
