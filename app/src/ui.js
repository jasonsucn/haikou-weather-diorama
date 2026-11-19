// DOM UI: live header, weather card, timeline, landmark popup, toasts.
const $ = (id) => document.getElementById(id);

const WIND16 = ['北', '北东北', '东北', '东东北', '东', '东东南', '东南', '南东南', '南', '南西南', '西南', '西西南', '西', '西西北', '西北', '北西北'];
const COMPASS = { n: '北', nne: '北东北', ne: '东北', ene: '东东北', e: '东', ese: '东东南', se: '东南', sse: '南东南', s: '南', ssw: '南西南', sw: '西南', wsw: '西西南', w: '西', wnw: '西西北', nw: '西北', nnw: '北西北' };

export function windName(deg, compass) {
  if (compass && COMPASS[compass]) return COMPASS[compass];
  if (!Number.isFinite(deg)) return '--';
  return WIND16[Math.round(((deg % 360) / 22.5)) % 16];
}

export function fmtTime(iso) {
  if (!iso) return '--:--';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '--:--';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function fmtDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function aqiClass(aqi) {
  if (!Number.isFinite(aqi)) return '';
  if (aqi <= 50) return 'good';
  if (aqi <= 100) return '';
  return 'bad';
}

export function initUI(handlers) {
  const refs = {
    temp: $('temp'), cond: $('cond'), feels: $('feels'), aqi: $('aqi'),
    updateTime: $('updateTime'), cardUpdate: $('cardUpdate'),
    mTemp: $('mTemp'), mFeels: $('mFeels'), mHum: $('mHum'), mWind: $('mWind'),
    mRain: $('mRain'), mVis: $('mVis'), mPressure: $('mPressure'), mUv: $('mUv'),
    alerts: $('alerts'), indices: $('indices'),
    slider: $('slider'), ticks: $('ticks'), tlTitle: $('tlTitle'),
    tlReadout: $('tlReadout'), playBtn: $('playBtn'),
    loading: $('loading'), loadingText: $('loadingText'), toast: $('toast'),
    tip: $('tip'), landmarks: $('landmarks'),
  };

  // landmark card
  const lmCard = document.createElement('div');
  lmCard.id = 'lmCard';
  lmCard.innerHTML = '<button class="close">×</button><h3></h3><div class="sub"></div><p></p>';
  document.body.appendChild(lmCard);
  lmCard.querySelector('.close').addEventListener('click', () => {
    lmCard.classList.remove('show');
    document.body.classList.remove('lm-open');
    handlers.onLandmarkClose?.();
  });

  refs.landmarks.querySelectorAll('button[data-lm]').forEach((btn) => {
    btn.addEventListener('click', () => handlers.onLandmark?.(btn.dataset.lm, btn));
  });
  $('resetView').addEventListener('click', () => handlers.onReset?.());
  $('soundBtn').addEventListener('click', () => handlers.onSound?.());
  $('nightBtn').addEventListener('click', () => handlers.onNight?.());
  $('demoBtn').addEventListener('click', () => handlers.onDemo?.());
  $('keyBtn').addEventListener('click', () => handlers.onKey?.());

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
      handlers.onMode?.(tab.dataset.mode);
    });
  });
  refs.slider.addEventListener('input', () => handlers.onScrub?.(Number(refs.slider.value)));
  refs.playBtn.addEventListener('click', () => handlers.onPlay?.());

  let toastTimer = 0;
  function toast(msg, ms = 2200) {
    refs.toast.textContent = msg;
    refs.toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => refs.toast.classList.remove('show'), ms);
  }

  function setLoading(text) {
    if (text) refs.loadingText.textContent = text;
  }
  function hideLoading() {
    refs.loading.classList.add('hidden');
  }

  function setLive(data) {
    const c = data.current;
    refs.temp.textContent = Math.round(c.temp);
    refs.cond.textContent = c.text;
    refs.feels.textContent = `体感 ${Math.round(c.feels)}°`;
    if (data.air) {
      refs.aqi.textContent = `AQI ${data.air.display || data.air.aqi}`;
      refs.aqi.className = `aqi ${aqiClass(data.air.aqi)}`;
    }
    const updated = new Date(data.fetchedAt);
    refs.updateTime.textContent = `${fmtTime(updated.toISOString())} 更新${data.degraded ? ' · 缓存' : ''}`;
    refs.cardUpdate.textContent = data.degraded ? '缓存数据' : fmtTime(updated.toISOString());

    refs.mTemp.textContent = `${c.temp.toFixed(1)}°`;
    refs.mFeels.textContent = `${c.feels.toFixed(1)}°`;
    refs.mHum.textContent = `${c.humidity}%`;
    refs.mWind.textContent = `${windName(c.windDeg, c.windDir)} ${c.windSpeed.toFixed(1)} m/s`;
    refs.mRain.textContent = `${c.precip.toFixed(1)} mm${c.precipRate ? ` · ${c.precipRate.toFixed(1)} mm/h` : ''}`;
    refs.mVis.textContent = `${(c.visibility / 1000).toFixed(1)} km`;
    refs.mPressure.textContent = `${Math.round(c.pressure)} hPa`;
    refs.mUv.textContent = String(c.uv);

    refs.alerts.innerHTML = '';
    for (const a of data.alerts || []) {
      const div = document.createElement('div');
      div.className = 'alert';
      div.innerHTML = `<b>${a.title}</b>${a.text.slice(0, 90)}${a.text.length > 90 ? '…' : ''}`;
      refs.alerts.appendChild(div);
    }
    refs.indices.innerHTML = '';
    for (const idx of (data.indices || []).slice(0, 5)) {
      const s = document.createElement('span');
      s.textContent = `${idx.name} · ${idx.category}`;
      s.title = idx.text || '';
      refs.indices.appendChild(s);
    }
    refs.cardUpdate.textContent = `${fmtTime(c.time)} · ${data.degraded ? '缓存' : '实况'}`;
  }

  function setTimeline(mode, items, index) {
    const isHour = mode === 'hour';
    refs.slider.max = String(isHour ? Math.max(0, items.length - 1) : Math.max(0, items.length - 1));
    refs.slider.value = String(index);
    refs.ticks.innerHTML = '';
    const n = isHour ? 6 : items.length;
    for (let i = 0; i < n; i++) {
      const span = document.createElement('span');
      if (isHour) {
        const item = items[Math.min(items.length - 1, i * 4)];
        span.textContent = item ? fmtTime(item.time) : '';
      } else {
        const item = items[i];
        span.textContent = item ? fmtDate(item.date + 'T00:00:00+08:00') : '';
      }
      refs.ticks.appendChild(span);
    }
    updateTimelineReadout(mode, items, index);
  }

  function updateTimelineReadout(mode, items, index) {
    const it = items[index];
    if (!it) return;
    if (mode === 'hour') {
      const day = fmtDate(it.time);
      refs.tlTitle.textContent = `逐小时 ${day} ${fmtTime(it.time)} · ${it.text} ${Math.round(it.temp)}°`;
      refs.tlReadout.textContent = `本小时降水 ${it.precip.toFixed(1)} mm · 湿度 ${it.humidity}% · 风 ${windName(it.windDeg)} ${it.windSpeed.toFixed(1)} m/s`;
    } else {
      const dayText = it.textDay || it.text || '--';
      const nightText = it.nightText || it.textNight || dayText;
      refs.tlTitle.textContent = `全天 ${fmtDate(it.date + 'T00:00:00+08:00')} · ${dayText} ${Math.round(it.min)}~${Math.round(it.max)}°`;
      refs.tlReadout.textContent = `白天 ${dayText} / 夜间 ${nightText} · 降水概率 ${it.precipProb}% · 风 ${windName(it.windDeg)} ${it.windScale} 级 · 日出 ${fmtTime(it.sunrise)} 日落 ${fmtTime(it.sunset)}`;
    }
  }

  function showLandmark(lm, text, sub) {
    lmCard.querySelector('h3').textContent = lm.title || lm.name;
    lmCard.querySelector('.sub').textContent = sub || lm.sub || '';
    lmCard.querySelector('p').textContent = text;
    lmCard.classList.add('show');
    document.body.classList.add('lm-open');
  }
  function hideLandmark() { lmCard.classList.remove('show'); document.body.classList.remove('lm-open'); }

  function setActive(name) {
    refs.landmarks.querySelectorAll('button[data-lm]').forEach((b) => {
      b.classList.toggle('active', b.dataset.lm === name);
    });
  }

  function setSound(on) {
    const b = $('soundBtn');
    b.textContent = on ? '🔊 声音' : '🔇 静音';
    b.classList.toggle('on', on);
  }
  function setNight(on) {
    const b = $('nightBtn');
    b.textContent = on ? '☀️ 白天' : '🌙 夜景';
    b.classList.toggle('on', on);
  }
  function setDemo(on) {
    const b = $('demoBtn');
    b.classList.toggle('on', on);
    b.textContent = on ? '⏹ 停止演示' : '✨ 演示';
  }
  function setPlay(on) {
    refs.playBtn.classList.toggle('on', on);
    refs.playBtn.textContent = on ? '❚❚' : '▶';
  }

  return {
    refs, toast, setLoading, hideLoading, setLive, setTimeline, updateTimelineReadout,
    showLandmark, hideLandmark, setActive, setSound, setNight, setDemo, setPlay,
  };
}
