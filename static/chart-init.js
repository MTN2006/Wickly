// static/chart-init.js
(function () {
  const container = document.getElementById('chart');
  if (!container || !window.LightweightCharts) return;

  const BASE = '/flask/api';

  const symbolEl = document.getElementById('symbol');
  const tfEl = document.getElementById('tf');
  const periodEl = document.getElementById('period');
  const applyBtn = document.getElementById('apply');
  const detBox = document.getElementById('detections');
  const detRefresh = document.querySelector('button#detections-refresh') || document.querySelector('button[aria-label="refresh-detections"]') || document.querySelector('button:has(#detections-refresh)');

  // UI Period -> backend lookback hint (yfinance fallback still uses these)
  const PERIOD_TO_YF = { '1H':'1h', '1D':'1d', '1W':'7d', '1M':'1mo', '1Y':'1y' };

  function normalizePeriodForTF(tf, uiPeriod) {
    const t = (tf || '').toUpperCase();
    const p = (uiPeriod || '').toUpperCase();
    if (t === '1M' || t === '5M' || t === '15M') return p;
    if (t === '1H') return p;
    if (t === '1W') { if (['1H','1D','1W'].includes(p)) return '1M'; return p; }
    if (t === '1MO') { if (['1H','1D','1W'].includes(p)) return '1M'; return p; }
    return p;
  }

  // read URL params (deep-link support)
  const params = new URLSearchParams(window.location.search);
  const urlTicker = params.get('ticker');
  const urlTF = params.get('tf');
  const urlLookback = params.get('lookback');
  if (symbolEl && urlTicker) symbolEl.value = urlTicker;
  if (tfEl && urlTF) tfEl.value = urlTF.toUpperCase();
  if (periodEl && urlLookback) {
    const inv = Object.fromEntries(Object.entries(PERIOD_TO_YF).map(([k, v]) => [v, k]));
    periodEl.value = inv[urlLookback] || periodEl.value;
  }

  // — chart creation —
  const chart = LightweightCharts.createChart(container, {
    layout: { background: { type: 'solid', color: '#0f172a' }, textColor: '#e2e8f0' },
    grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
    rightPriceScale: { borderColor: '#334155' },
    // we’ll override timeScale dynamically via setTimeScaleFormat()
    timeScale: { borderColor: '#334155' },
    crosshair: { mode: 1 },
    autoSize: true,
  });

  setTimeScaleFormat((tfEl?.value || '1D').toUpperCase());

  // Format x-axis depending on timeframe
  function setTimeScaleFormat(tf) {
    const T = (tf || '1D').toUpperCase();
    const intraday = ['1M', '5M', '15M', '1H'].includes(T);

    chart.applyOptions({
      timeScale: {
        borderColor: '#334155',
        timeVisible: intraday,                // show hh:mm for intraday
        secondsVisible: T === '1M',           // only for 1-minute
        tickMarkFormatter: (t, markType, locale) => {
          // t can be UTCTimestamp (number) or BusinessDay ("YYYY-MM-DD")
          const toDate = (val) =>
            (typeof val === 'number')
              ? new Date(val * 1000)
              : new Date(val);  // BusinessDay becomes local midnight

          const d = toDate(t);
          const mm = String(d.getMonth() + 1).padStart(2, '0');
          const dd = String(d.getDate()).padStart(2, '0');
          const hh = String(d.getHours()).padStart(2, '0');
          const mi = String(d.getMinutes()).padStart(2, '0');

          if (intraday) {
            // Minute/Hour ticks: show time; Day ticks: show M/D to reduce clutter
            if (markType === LightweightCharts.TickMarkType.Minute ||
                markType === LightweightCharts.TickMarkType.Time ||
                markType === LightweightCharts.TickMarkType.Hour) {
              return `${hh}:${mi}`;
            }
            return `${mm}/${dd}`;
          }

          // Higher TFs
          if (T === '1D') return `${mm}/${dd}`;
          if (T === '1W' || T === '1MO') {
            return `${d.getFullYear()}-${mm}`; // YYYY-MM
          }
          return d.toLocaleDateString(locale || undefined);
        },
      },
    });
  }

  const candle = chart.addCandlestickSeries({
    upColor: '#22c55e', downColor: '#ef4444', borderVisible: false,
    wickUpColor: '#22c55e', wickDownColor: '#ef4444'
  });

  let pollTimer = null;

  function currentParams() {
    const symbol = (symbolEl?.value || 'AAPL').toUpperCase();
    const tf = (tfEl?.value || '1D').toUpperCase();          // 1M/5M/15M/1H/1D/1W/1MO
    let periodUi = (periodEl?.value || '1M').toUpperCase();   // 1H/1D/1W/1M/1Y
    periodUi = normalizePeriodForTF(tf, periodUi);
    const yfPeriod = PERIOD_TO_YF[periodUi] || '1mo';
    return { symbol, tf, periodUi, yfPeriod };
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`${url} -> ${res.status}`);
    return res.json();
  }

  // (removed duplicate simple helper setTimeScaleFormat)

  async function loadChart() {
    try {
      const { symbol, tf, periodUi, yfPeriod } = currentParams();

      setTimeScaleFormat(tf);

      // Debug visibility
      console.log('[Wickly] params ->', { symbol, tf, periodUi, yfPeriod });

      const qs = `?ticker=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(tf)}&lookback=${encodeURIComponent(yfPeriod)}&t=${Date.now()}`;
      const bars = await fetchJson(`${BASE}/bars${qs}`);

      candle.setData(bars || []);
      chart.timeScale().fitContent();

      // also refresh detections whenever the chart reloads
      await loadDetections();
    } catch (e) {
      console.error('loadChart failed', e);
    }
  }

  function renderDetections(items) {
    if (!detBox) return;
    if (!items || !items.length) {
      detBox.innerHTML = `<div class="text-sm opacity-70">No recent patterns.</div>`;
      return;
    }
    const lines = items.map(d => {
      // ---- PATCH: guard missing/invalid time ----
      const ts = (d && typeof d.time === 'number') ? d.time : null;
      const when = ts ? new Date(ts * 1000).toLocaleString() : '—';
      const arrow = d.dir === 'bullish' ? '🟩' : '🟥';
      const nice = d.name || d.pattern || 'Pattern';
      return `<div class="p-2 rounded border border-slate-700 bg-slate-800/60 mb-2">
                <div class="text-sm font-semibold">${arrow} ${nice}</div>
                <div class="text-[11px] opacity-70">${when}</div>
              </div>`;
    });
    detBox.innerHTML = lines.join('');
  }

  async function loadDetections() {
    try {
      const { symbol, tf, periodUi, yfPeriod } = currentParams();
      const qs = `?ticker=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(tf)}&lookback=${encodeURIComponent(yfPeriod)}&t=${Date.now()}`;
      const dets = await fetchJson(`${BASE}/detections${qs}`);
      renderDetections(dets);
    } catch (e) {
      console.error('loadDetections failed', e);
      renderDetections([]);
    }
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    const tf = (tfEl?.value || '1D').toUpperCase();
    const intervalMs =
      tf === '1M' ? 5_000 :
      (tf === '5M' || tf === '15M') ? 20_000 :
      tf === '1H' ? 60_000 :
      120_000;
    pollTimer = setInterval(loadChart, intervalMs);
  }

  if (tfEl) {
    tfEl.addEventListener('change', async () => {
      const tf = (tfEl.value || '1D').toUpperCase();
      setTimeScaleFormat(tf);   // update the time axis labels
      await loadChart();        // reload data too
      startPolling();           // restart cadence based on TF
    });
  }
  if (applyBtn) applyBtn.addEventListener('click', async () => { await loadChart(); startPolling(); });
  if (detRefresh) detRefresh.addEventListener('click', loadDetections);

  (async () => {
    await loadChart();
    startPolling();
    new ResizeObserver(() => chart.applyOptions({})).observe(container);
  })();
})();