(() => {
  const cfg = JSON.parse(document.getElementById('cfg').textContent);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const meta = Object.fromEntries(cfg.features.map(f => [f.name, f]));
  const classes = Object.fromEntries(cfg.classes.map(c => [c.name, c]));
  const state = Object.fromEntries(cfg.features.map(f => [f.name, f.median]));
  const ranges = Object.fromEntries($$('.range').map(el => [el.dataset.f, el]));
  const nums = Object.fromEntries($$('.num').map(el => [el.dataset.f, el]));

  const clamp = (f, v) => Math.min(Math.max(v, meta[f].min), meta[f].max);
  const fmt = (f, v) => Number(v).toFixed(meta[f].decimals);
  const pct = (f, v) => ((v - meta[f].min) / ((meta[f].max - meta[f].min) || 1)) * 100;

  function paint(f) {
    const v = state[f];
    ranges[f].value = v;
    ranges[f].style.setProperty('--pct', pct(f, v) + '%');
    if (document.activeElement !== nums[f]) nums[f].value = fmt(f, v);
  }
  function setValue(f, v, { quiet = false } = {}) {
    state[f] = clamp(f, v);
    paint(f);
    if (!quiet) { clearActive(); schedule(); }
  }

  /* ---------- presets ---------- */
  function clearActive() { $$('.preset').forEach(b => b.classList.remove('active')); }
  function applyValues(src) {
    cfg.features.forEach(f => setValue(f.name, src[f.name], { quiet: true }));
    schedule();
  }
  $$('.preset[data-class]').forEach(btn => btn.addEventListener('click', () => {
    applyValues(classes[btn.dataset.class].median);
    clearActive(); btn.classList.add('active');
  }));
  $('#reset').addEventListener('click', () => {
    applyValues(Object.fromEntries(cfg.features.map(f => [f.name, f.median]))); clearActive();
  });

  /* ---------- input sliders & angka ---------- */
  Object.entries(ranges).forEach(([f, el]) => el.addEventListener('input', () => setValue(f, parseFloat(el.value))));
  Object.entries(nums).forEach(([f, el]) => {
    el.addEventListener('input', () => { const v = parseFloat(el.value); if (Number.isFinite(v)) { state[f] = clamp(f, v); ranges[f].value = state[f]; ranges[f].style.setProperty('--pct', pct(f, state[f]) + '%'); clearActive(); schedule(); } });
    el.addEventListener('change', () => { const v = parseFloat(el.value); setValue(f, Number.isFinite(v) ? v : meta[f].median); el.value = fmt(f, state[f]); });
    el.addEventListener('blur', () => { el.value = fmt(f, state[f]); });
  });

  /* ---------- prediksi ---------- */
  let timer = null, ctrl = null;
  function schedule() { clearTimeout(timer); timer = setTimeout(predict, 120); }

  async function predict() {
    if (ctrl) ctrl.abort();
    ctrl = new AbortController();
    try {
      const res = await fetch('/api/predict', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: state }), signal: ctrl.signal
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Gagal memprediksi');
      render(data);
    } catch (e) {
      if (e.name === 'AbortError') return;
      showWarn('Prediksi gagal: ' + e.message + '. Coba muat ulang halaman.');
    }
  }

  const card = $('#res-card'), mini = $('#minibar'), warn = $('#res-warn');
  function showWarn(html) { warn.innerHTML = html; warn.hidden = !html; }

  function render(d) {
    const c = classes[d.top] || { label: d.top, color: '#0E7C66' };
    card.style.setProperty('--c', c.color);
    mini.style.setProperty('--c', c.color);
    $('#res-name').textContent = c.label;
    $('#res-conf').textContent = Math.round(d.confidence * 100) + '%';
    $('#res-meter').style.width = (d.confidence * 100) + '%';
    $('#mini-name').textContent = c.label;
    $('#mini-conf').textContent = Math.round(d.confidence * 100) + '% yakin';

    const bars = $('#bars');
    d.probabilities.forEach((p, i) => {
      const row = $(`.row[data-class="${CSS.escape(p.class)}"]`, bars);
      if (!row) return;
      row.style.order = i;
      $('.fill', row).style.width = (p.p * 100).toFixed(1) + '%';
      $('.val', row).textContent = (p.p * 100).toFixed(1) + '%';
    });
    bars.style.display = 'flex'; bars.style.flexDirection = 'column';

    if (d.confidence < 0.6 && d.probabilities[1]) {
      const r = classes[d.probabilities[1].class]?.label || d.probabilities[1].class;
      showWarn(`Keyakinan masih rendah. Ciri biji ini mirip dengan <b>${r}</b>, jadi pertimbangkan pemeriksaan manual.`);
    } else showWarn('');
  }

  /* ---------- tab ---------- */
  const tabs = { prediksi: $('#tab-prediksi'), tentang: $('#tab-tentang') };
  function show(name) {
    if (!tabs[name]) name = 'prediksi';
    Object.entries(tabs).forEach(([k, el]) => {
      el.setAttribute('aria-selected', String(k === name));
      $('#view-' + k).hidden = k !== name;
    });
    mini.style.visibility = name === 'prediksi' ? 'visible' : 'hidden';
  }
  Object.entries(tabs).forEach(([k, el]) => el.addEventListener('click', () => { history.replaceState(null, '', '#' + k); show(k); }));
  window.addEventListener('hashchange', () => show(location.hash.slice(1)));

  cfg.features.forEach(f => paint(f.name));
  show(location.hash.slice(1));
  predict();
})();
