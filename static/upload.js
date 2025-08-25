// ---------- existing refs ----------
const fileInput = document.getElementById('upload');
const preview = document.getElementById('preview');
const result = document.getElementById('result');

// ---------- create a toast root dynamically (no HTML change needed) ----------
function ensureToastRoot() {
  let root = document.getElementById('toastRoot');
  if (!root) {
    root = document.createElement('div');
    root.id = 'toastRoot';
    // Full-width, stacked popups at bottom; pointer-events so buttons are clickable
    root.className = 'fixed inset-x-0 bottom-4 px-4 space-y-3 z-50 pointer-events-none';
    document.body.appendChild(root);
  }
  return root;
}

// ---------- tiny advice map (extend as you like) ----------
const ADVICE = {
  "Hammer": "Often seen after a decline; wait for bullish confirmation.",
  "Inverted Hammer": "Appears in downtrends; confirmation improves reliability.",
  "Bullish Engulfing": "Momentum shift up; confirm with next close and volume.",
  "Piercing Line": "Potential reversal; watch the next candle.",
  "Morning Star": "3‑candle reversal; seek confirmation.",
  "Morning Doji Star": "Indecision mid‑candle; wait for follow‑through.",
  "Three White Soldiers": "Strong momentum; beware overextension.",
  "Bullish Harami": "Possible turn; confirmation helps.",
  "Bullish Harami Cross": "As above with doji; confirm.",
  "Tweezer Bottom": "Double rejection of lows; monitor follow‑through.",
  "Rising Three Methods": "Continuation; trend context matters.",
  "Bullish Tasuki Gap": "Continuation; gap support is key.",
  "Side-by-Side White Lines (Bullish)": "Continuation; confirm trend.",
  "Mat Hold (Bullish)": "Robust continuation structure.",
  "Bullish Kicking": "Strong shift; verify with volume/gap.",
  "Shooting Star": "After uptrend; look for a lower close.",
  "Bearish Engulfing": "Momentum down; confirm below support.",
  "Evening Star": "3‑candle reversal; confirm.",
  "Tweezer Top": "Repeated rejection of highs; watch breakdown."
};

// ---------- helpers ----------
function makeToast({ label, prob }) {
  const pct = (prob != null) ? `${(prob * 100).toFixed(1)}%` : null;

  const wrap = document.createElement('div');
  wrap.className = 'pointer-events-auto w-full';

  const bar = document.createElement('div');
  // Uses Tailwind (already on your page) but injected via JS (no HTML edits)
  bar.className = `
    mx-auto w-full max-w-6xl rounded-2xl
    bg-gray-900 bg-opacity-85 backdrop-blur
    ring-1 ring-white/10 shadow-2xl
    px-4 py-3
  `.replace(/\s+/g, ' ').trim();

  const row = document.createElement('div');
  row.className = 'flex items-start justify-between gap-3';

  const left = document.createElement('div');
  left.className = 'flex items-center gap-2';

  const title = document.createElement('h3');
  title.className = 'text-base font-semibold text-cyan-300';
  title.textContent = label;

  left.appendChild(title);

  if (pct) {
    const badge = document.createElement('span');
    badge.className = `
      inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold
      bg-cyan-700/30 ring-1 ring-cyan-400/40
    `.replace(/\s+/g, ' ').trim();
    badge.textContent = pct;
    left.appendChild(badge);
  }

  const closeBtn = document.createElement('button');
  closeBtn.className = 'px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 transition';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', () => wrap.remove());

  row.appendChild(left);
  row.appendChild(closeBtn);

  const tip = document.createElement('p');
  tip.className = 'text-sm text-gray-200 mt-1';
  const advice = ADVICE[label]
    || ADVICE[label.replace('(Bullish)', '').trim()]
    || ADVICE[label.replace('(Bearish)', '').trim()]
    || 'Consider trend, volume, and key levels before acting.';
  tip.textContent = advice;

  bar.appendChild(row);
  bar.appendChild(tip);
  wrap.appendChild(bar);
  return wrap;
}

function extractPatterns(data) {
  // Preferred: multi-category probabilities dict
  const probs = data?.probabilities || {};
  let list = Object.entries(probs)
    .map(([label, p]) => ({ label, prob: Number(p) }))
    .filter(x => !Number.isNaN(x.prob));

  // Fallback: single-label only
  if (list.length === 0 && data?.prediction) {
    list = [{ label: String(data.prediction), prob: null }];
  }

  // Sort + threshold
  const THRESHOLD = 0.25;
  const sorted = list.sort((a, b) => (b.prob ?? -1) - (a.prob ?? -1));
  const filtered = sorted.filter(x => x.prob == null || x.prob >= THRESHOLD);

  if (filtered.length === 0 && sorted.length > 0) return [sorted[0]];
  return filtered;
}

function showPopups(patterns) {
  const root = ensureToastRoot();
  root.innerHTML = ''; // clear old ones per upload
  patterns.forEach(p => root.appendChild(makeToast(p)));
}

// ---------- your existing flow, unchanged except for calling showPopups ----------
fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  result.textContent = "Scanning...";
  result.classList.remove("hidden");

  // Preview
  const reader = new FileReader();
  reader.onload = () => {
    preview.src = reader.result;
    preview.classList.remove('hidden');
  };
  reader.readAsDataURL(file);

  // Send to backend
  const formData = new FormData();
  formData.append('image', file);

  try {
    const response = await fetch("https://wickly.onrender.com/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error || "Server error");
    }

    // Keep your fallback text output (optional)
    const predLabel = data.prediction;
    const predProb = data.probabilities?.[predLabel] ?? null;
    result.style.display = 'block';
    result.style.whiteSpace = 'pre-wrap';
    result.innerHTML = predLabel
      ? `<strong>Prediction:</strong> ${predLabel}${predProb != null ? ` (${(predProb*100).toFixed(1)}% confident)` : ''}`
      : `<strong>Scanned.</strong>`;

    // NEW: one popup per detected pattern
    const patterns = extractPatterns(data);
    showPopups(patterns);

  } catch (err) {
    console.error(err);
    result.textContent = `Error: ${err.message || err}`;
  }
});