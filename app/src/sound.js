// Procedural WebAudio ambience: ocean, rain, wind, gulls, thunder.
export class SoundEngine {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.enabled = true;
    this.unlocked = false;
    this.rainGain = null;
    this.windGain = null;
    this.oceanGain = null;
    this.birdTimer = 0;
    this.state = { rain: 0, wind: 4, night: false };
  }

  unlock() {
    if (this.unlocked) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.enabled ? 0.85 : 0.0;
    this.master.connect(this.ctx.destination);

    const noise = this.makeNoise(3);
    // ocean
    const ocean = this.ctx.createBufferSource();
    ocean.buffer = noise; ocean.loop = true;
    const oceanFilter = this.ctx.createBiquadFilter();
    oceanFilter.type = 'lowpass'; oceanFilter.frequency.value = 480;
    this.oceanGain = this.ctx.createGain();
    this.oceanGain.gain.value = 0.30;
    const lfo = this.ctx.createOscillator();
    const lfoGain = this.ctx.createGain();
    lfo.frequency.value = 0.11; lfoGain.gain.value = 0.13;
    lfo.connect(lfoGain).connect(this.oceanGain.gain);
    lfo.start();
    ocean.connect(oceanFilter).connect(this.oceanGain).connect(this.master);
    ocean.start();

    // rain
    const rain = this.ctx.createBufferSource();
    rain.buffer = noise; rain.loop = true;
    const rainFilter = this.ctx.createBiquadFilter();
    rainFilter.type = 'bandpass'; rainFilter.frequency.value = 2200; rainFilter.Q.value = 0.55;
    this.rainGain = this.ctx.createGain();
    this.rainGain.gain.value = 0.0;
    rain.connect(rainFilter).connect(this.rainGain).connect(this.master);
    rain.start();

    // wind
    const wind = this.ctx.createBufferSource();
    wind.buffer = noise; wind.loop = true;
    const windFilter = this.ctx.createBiquadFilter();
    windFilter.type = 'lowpass'; windFilter.frequency.value = 260;
    this.windGain = this.ctx.createGain();
    this.windGain.gain.value = 0.06;
    wind.connect(windFilter).connect(this.windGain).connect(this.master);
    wind.start();

    this.unlocked = true;
    if (this.ctx.state === 'suspended') this.ctx.resume();
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && this.ctx?.state === 'suspended') this.ctx.resume();
    });
    this.setEnabled(this.enabled);
  }

  makeNoise(seconds) {
    const len = Math.floor(this.ctx.sampleRate * seconds);
    const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const data = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 5.0;
    }
    return buf;
  }

  setEnabled(on) {
    this.enabled = on;
    if (this.master) {
      this.master.gain.setTargetAtTime(on ? 0.85 : 0.0, this.ctx.currentTime, 0.15);
    }
  }

  setWeather({ rain = 0, wind = 4, night = false }) {
    this.state = { rain, wind, night };
    if (!this.unlocked) return;
    const t = this.ctx.currentTime;
    this.rainGain?.gain.setTargetAtTime(rain * 0.5, t, 0.4);
    this.windGain?.gain.setTargetAtTime(0.05 + Math.min(wind / 18, 1) * 0.18, t, 0.5);
    this.oceanGain?.gain.setTargetAtTime(night ? 0.36 : 0.30, t, 0.8);
  }

  chirp() {
    if (!this.unlocked || !this.enabled) return;
    const t = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = 'sine';
    const base = 1500 + Math.random() * 900;
    osc.frequency.setValueAtTime(base, t);
    osc.frequency.exponentialRampToValueAtTime(base * 1.7, t + 0.08);
    osc.frequency.exponentialRampToValueAtTime(base * 1.15, t + 0.2);
    g.gain.setValueAtTime(0.0, t);
    g.gain.linearRampToValueAtTime(0.09, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
    osc.connect(g).connect(this.master);
    osc.start(t); osc.stop(t + 0.32);
  }

  thunder() {
    if (!this.unlocked || !this.enabled) return;
    const t = this.ctx.currentTime + 0.4 + Math.random() * 1.2;
    const src = this.ctx.createBufferSource();
    src.buffer = this.makeNoise(2.5);
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass'; filter.frequency.setValueAtTime(220, t);
    filter.frequency.exponentialRampToValueAtTime(60, t + 2.0);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0, t);
    g.gain.linearRampToValueAtTime(0.55, t + 0.05);
    g.gain.exponentialRampToValueAtTime(0.001, t + 2.2);
    src.connect(filter).connect(g).connect(this.master);
    src.start(t); src.stop(t + 2.4);
  }

  update(dt) {
    this.birdTimer -= dt;
    if (this.birdTimer <= 0) {
      this.birdTimer = 3.5 + Math.random() * 5;
      if (!this.state.night || Math.random() < 0.25) this.chirp();
    }
  }
}
