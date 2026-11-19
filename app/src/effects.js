// Visual effects: sky dome, sea shader, rain lines, birds, lightning flash.
import * as THREE from 'three';

export function createSky(scene) {
  const geo = new THREE.SphereGeometry(1600, 32, 20);
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      uTop: { value: new THREE.Color('#5aa9dd') },
      uHorizon: { value: new THREE.Color('#d9ecf4') },
      uSunDir: { value: new THREE.Vector3(0.4, 0.5, 0.6).normalize() },
      uSunColor: { value: new THREE.Color('#fff2cf') },
      uNight: { value: 0 },
      uCloud: { value: 0.3 },
    },
    vertexShader: `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uTop; uniform vec3 uHorizon; uniform vec3 uSunDir;
      uniform vec3 uSunColor; uniform float uNight; uniform float uCloud;
      varying vec3 vDir;
      void main() {
        float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
        vec3 col = mix(uHorizon, uTop, pow(h, 1.2));
        float sun = pow(max(dot(normalize(vDir), normalize(uSunDir)), 0.0), 900.0);
        float glow = pow(max(dot(normalize(vDir), normalize(uSunDir)), 0.0), 12.0);
        col += uSunColor * (sun * 1.6 + glow * 0.18) * (1.0 - uNight * 0.7);
        float band = smoothstep(0.0, 0.35, uCloud) * 0.08;
        col = mix(col, vec3(0.72, 0.78, 0.84), band);
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  });
  const sky = new THREE.Mesh(geo, mat);
  sky.name = 'SkyDome';
  scene.add(sky);
  return sky;
}

export function createSea(seaMesh, scene) {
  if (!seaMesh) return null;
  const uniforms = {
    uTime: { value: 0 },
    uDeep: { value: new THREE.Color('#105a72') },
    uShallow: { value: new THREE.Color('#3fa8bd') },
    uSunDir: { value: new THREE.Vector3(0.4, 0.7, 0.3).normalize() },
    uSunColor: { value: new THREE.Color('#ffe9bd') },
    uNight: { value: 0 },
    uWind: { value: 0.4 },
  };
  const mat = new THREE.ShaderMaterial({
    uniforms,
    transparent: false,
    side: THREE.DoubleSide,
    vertexShader: `
      uniform float uTime; uniform float uWind;
      varying vec3 vWorld; varying vec3 vN;
      void main() {
        vec3 p = position;
        float top = step(0.6, normal.y);
        float w1 = sin(p.x * 0.060 + uTime * 1.10);
        float w2 = sin(p.z * 0.045 - uTime * 0.80);
        float w3 = sin((p.x + p.z) * 0.030 + uTime * 0.60);
        float w4 = sin(p.x * 0.130 - uTime * 1.70) * 0.36;
        float w5 = sin(p.z * 0.110 + uTime * 1.30) * 0.30;
        float w = w1 * 0.28 + w2 * 0.36 + w3 * 0.20 + w4 * 0.10 + w5 * 0.09;
        p.y += w * top * (0.55 + uWind * 0.75);
        vWorld = (modelMatrix * vec4(p, 1.0)).xyz;
        float dx = cos(p.x * 0.060 + uTime * 1.10) * 0.060 * 0.28
                 + cos((p.x + p.z) * 0.030 + uTime * 0.60) * 0.030 * 0.20
                 + cos(p.x * 0.130 - uTime * 1.70) * 0.130 * 0.036;
        float dz = -cos(p.z * 0.045 - uTime * 0.80) * 0.045 * 0.36
                 + cos((p.x + p.z) * 0.030 + uTime * 0.60) * 0.030 * 0.20
                 + cos(p.z * 0.110 + uTime * 1.30) * 0.110 * 0.027;
        vN = normalize(vec3(-dx * 14.0, 1.0, -dz * 14.0));
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uDeep; uniform vec3 uShallow; uniform vec3 uSunDir;
      uniform vec3 uSunColor; uniform float uNight; uniform float uTime;
      varying vec3 vWorld; varying vec3 vN;
      void main() {
        vec3 viewDir = normalize(cameraPosition - vWorld);
        float fres = pow(1.0 - max(dot(viewDir, normalize(vN)), 0.0), 3.0);
        float dist = length(vWorld.xz - vec2(8.0, -1.0));
        float shore = 1.0 - smoothstep(72.0, 103.0, dist);
        vec3 col = mix(uDeep, uShallow, 0.55 + 0.45 * dot(normalize(vN), vec3(0.0, 1.0, 0.0)));
        col = mix(col, uShallow * 1.18 + vec3(0.02, 0.05, 0.04), shore * 0.45);
        col = mix(col, vec3(0.62, 0.82, 0.92), fres * (0.35 + shore * 0.25));
        vec3 h = normalize(viewDir + normalize(uSunDir));
        float spec = pow(max(dot(normalize(vN), h), 0.0), 120.0);
        col += uSunColor * spec * 0.9 * (1.0 - uNight * 0.8);
        float sparkle = pow(max(sin(vWorld.x * 1.7 + uTime * 1.5) * sin(vWorld.z * 1.3 - uTime), 0.0), 22.0);
        col += vec3(0.75, 0.92, 1.0) * sparkle * 0.03;
        float cap = smoothstep(0.72, 0.96, sin(vWorld.x * 0.70 + uTime * 1.35) * sin(vWorld.z * 0.55 - uTime * 0.95));
        col = mix(col, vec3(0.86, 0.95, 0.96), cap * 0.07 * (1.0 - uNight));
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  });
  seaMesh.material = mat;
  seaMesh.receiveShadow = false;
  return mat;
}

export function createRain(scene, maxCount = 6000) {
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(maxCount * 2 * 3);
  const phase = new Float32Array(maxCount * 2);
  const top = new Float32Array(maxCount * 2);
  for (let i = 0; i < maxCount; i++) {
    const x = (Math.random() - 0.5) * 260;
    const z = (Math.random() - 0.5) * 260;
    const p = Math.random();
    for (let k = 0; k < 2; k++) {
      const j = i * 2 + k;
      pos[j * 3] = x;
      pos[j * 3 + 1] = 0;
      pos[j * 3 + 2] = z;
      phase[j] = p;
      top[j] = k;
    }
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1));
  geo.setAttribute('aTop', new THREE.BufferAttribute(top, 1));
  const mat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      uTime: { value: 0 },
      uWind: { value: new THREE.Vector2(0.2, 0.1) },
      uColor: { value: new THREE.Color('#e6f2fc') },
      uOpacity: { value: 0.0 },
    },
    vertexShader: `
      uniform float uTime; uniform vec2 uWind;
      attribute float aPhase; attribute float aTop;
      varying float vA;
      void main() {
        float H = 80.0;
        float y = mod(aPhase * H - uTime * (55.0 + aPhase * 35.0), H);
        vec3 p = position;
        p.y = 4.0 + y;
        float t = 1.0 - y / H;
        p.x += uWind.x * t * 18.0;
        p.z += uWind.y * t * 18.0;
        if (aTop > 0.5) {
          p.y += 3.6 + aPhase * 5.0;
          p.x += uWind.x * 0.9;
          p.z += uWind.y * 0.9;
        }
        vA = 0.5 + aPhase * 0.5;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor; uniform float uOpacity; varying float vA;
      void main() {
        gl_FragColor = vec4(uColor, uOpacity * vA);
      }
    `,
  });
  const lines = new THREE.LineSegments(geo, mat);
  lines.frustumCulled = false;
  lines.name = 'Rain';
  scene.add(lines);
  return { mesh: lines, material: mat, maxCount, geo };
}

export function createBirds(scene) {
  const birds = [];
  const group = new THREE.Group();
  group.name = 'Birds';
  scene.add(group);
  const mat = new THREE.MeshBasicMaterial({ color: 0x2c3a44, side: THREE.DoubleSide });
  for (let i = 0; i < 5; i++) {
    const bird = new THREE.Group();
    const body = new THREE.Mesh(new THREE.ConeGeometry(0.45, 2.0, 6), mat);
    body.rotation.x = Math.PI / 2;
    const wingGeo = new THREE.PlaneGeometry(2.4, 0.8);
    const wingL = new THREE.Mesh(wingGeo, mat);
    wingL.position.x = -1.35;
    wingL.rotation.z = 0.2;
    const wingR = new THREE.Mesh(wingGeo, mat);
    wingR.position.x = 1.35;
    wingR.rotation.z = -0.2;
    bird.add(body, wingL, wingR);
    bird.userData = {
      radius: 58 + i * 8,
      height: 48 + (i % 3) * 7,
      speed: 0.14 + Math.random() * 0.05,
      phase: Math.random() * Math.PI * 2,
      wingL, wingR,
      flap: 0.8 + Math.random() * 0.5,
    };
    bird.scale.setScalar(0.8);
    group.add(bird);
    birds.push(bird);
  }
  return birds;
}

export function updateBirds(birds, t) {
  for (const b of birds) {
    const d = b.userData;
    const a = t * d.speed + d.phase;
    b.position.set(Math.cos(a) * d.radius, d.height + Math.sin(t * 0.6 + d.phase) * 2.4, Math.sin(a) * d.radius);
    b.rotation.y = -a + Math.PI / 2;
    const flap = Math.sin(t * 8 * d.flap + d.phase) * 0.55;
    d.wingL.rotation.z = 0.15 + flap;
    d.wingR.rotation.z = -0.15 - flap;
  }
}

export function flashLightning(intensity = 1) {
  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;inset:0;background:#eaf6ff;z-index:5;pointer-events:none;opacity:0;transition:opacity .08s ease';
  document.body.appendChild(el);
  requestAnimationFrame(() => { el.style.opacity = String(0.35 * intensity); });
  setTimeout(() => { el.style.opacity = '0'; }, 90);
  setTimeout(() => el.remove(), 500);
}

export function createLights(scene) {
  const hemi = new THREE.HemisphereLight(0xd9ecf7, 0x3c4a3a, 0.9);
  const ambient = new THREE.AmbientLight(0xfff2dd, 0.22);
  const sun = new THREE.DirectionalLight(0xfff0d6, 2.2);
  sun.position.set(-120, 160, 90);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  const c = sun.shadow.camera;
  c.left = -140; c.right = 140; c.top = 140; c.bottom = -140; c.near = 1; c.far = 600;
  sun.shadow.bias = -0.0005;
  const rim = new THREE.DirectionalLight(0x9cc7e8, 0.5);
  rim.position.set(120, 80, -120);
  scene.add(ambient, hemi, sun, rim);
  return { hemi, sun, rim, ambient };
}

export function updateSky(sky, sunDir, night, cloud) {
  if (!sky) return;
  sky.material.uniforms.uSunDir.value.copy(sunDir);
  sky.material.uniforms.uNight.value = night;
  sky.material.uniforms.uCloud.value = cloud;
  const top = sky.material.uniforms.uTop.value;
  const hor = sky.material.uniforms.uHorizon.value;
  if (night > 0.6) {
    top.set('#0a1c30'); hor.set('#173a52');
  } else if (night > 0.25) {
    top.set('#2a5679'); hor.set('#e2a56f');
  } else {
    top.set('#5aa9dd'); hor.set('#d9ecf4');
  }
}
