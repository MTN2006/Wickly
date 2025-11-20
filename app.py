import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

# -------------------- Flask imports --------------------
from flask import Flask, request, jsonify, make_response, render_template
from PIL import Image, ImageOps

# -------------------- FastAPI imports --------------------
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

# -------------------- Env --------------------
from dotenv import load_dotenv
load_dotenv()

# -------------------- Extra imports for OHLC --------------------
import pandas as pd
import yfinance as yf
import requests
import io
import httpx  # for Alpaca REST

# -------- TA-Lib pattern scanner --------
try:
    from patterns_talib import scan_patterns
    HAS_TALIB = True
except Exception as e:
    HAS_TALIB = False
    scan_patterns = lambda df, **kw: []  # graceful no-op
    logging.warning(f"TA-Lib not available: {e}")

# ---- Safe TA-Lib wrapper and cache for stability --------------------------------
from functools import lru_cache
import time

_DETS_CACHE: dict[tuple[str, str, str], dict] = {}  # (ticker,tf,look) -> {last_time:int, dets:list, ts:float}


def _bars_last_time(bars: list[dict]) -> int:
    return int(bars[-1]["time"]) if bars else 0


def safe_scan(df: pd.DataFrame, *, min_abs: int = 20, max_bars: int = 400, top_k: int = 50) -> list[dict]:
    try:
        if df is None or df.empty:
            return []
        df2 = df.tail(max_bars).copy()

        # Call TA-Lib
        dets = scan_patterns(df2, min_abs=min_abs) if HAS_TALIB else []
        if not isinstance(dets, list):
            return []

        # Normalize: sort by time and strength, pick strongest per timestamp
        dets.sort(key=lambda d: (d.get("time", 0), abs(d.get("value", 0))), reverse=True)
        seen = set()
        coalesced = []
        for d in dets:
            if d.get("time") in seen:
                continue
            seen.add(d.get("time"))
            coalesced.append(d)
        dets = coalesced

        # Normalize & sort newest first
        for d in dets:
            d.setdefault("pattern", d.get("name", "Unknown"))
            d.setdefault("time", 0)
        dets.sort(key=lambda x: x["time"], reverse=True)
        return dets[:top_k]
    except Exception as e:
        logging.warning(f"safe_scan failed: {e}")
        return []


# -------------------- FastAPI app (ASGI) --------------------
app = FastAPI(title="Wickly API", version="0.2.0")

# serve static + templates (FastAPI side)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# include routers (keep your existing routers)
from wicklyu.routers import detections  # noqa: E402

app.include_router(detections.router)


# 🚨 NEW: make the ASGI root redirect to the Flask UI
@app.get("/", include_in_schema=False)
async def root():
    # When someone hits the bare domain, send them to the Flask home page
    return RedirectResponse(url="/flask/")


# optional: /home → same place (nice for SEO / bookmarks)
@app.get("/home", include_in_schema=False)
async def home_redirect():
    return RedirectResponse(url="/flask/")


# -------------------- fastai (only import what you use) --------------------
from fastai.vision.all import load_learner  # noqa: E402

# ---- Optional HEIC support (won't crash if missing) ----
HEIC_ENABLED = False
try:
    import pillow_heif  # enables HEIC/HEIF via PIL, if installed

    pillow_heif.register_heif_opener()
    HEIC_ENABLED = True
except Exception as e:
    logging.warning(f"pillow-heif not available ({e}). HEIC uploads will not be accepted.")

# -------------------- Flask app (WSGI) --------------------
flask_app = Flask(__name__)

# ---- logging (shows up in Render/local logs) ----
logging.basicConfig(level=logging.INFO)
flask_app.logger.setLevel(logging.INFO)

# ---- model + uploads ----
model_path = Path("candlestick_model_V04.pkl")
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# Force CPU on Render
learn = load_learner(model_path, cpu=True)  # <— keeps CPU
VOCAB = list(learn.dls.vocab)  # e.g. ['hammer','none']


def predict_argmax(img_path: Path):
    _, _, probs = learn.predict(img_path)
    top_idx = int(probs.argmax())
    label = VOCAB[top_idx]
    probs_dict = {VOCAB[i]: float(probs[i]) for i in range(len(VOCAB))}
    return label, probs_dict


# ===================== OHLC via Alpaca (primary) + yfinance + Stooq (fallbacks) =====================

ALPACA_KEY = os.environ.get("ALPACA_API_KEY_ID")
ALPACA_SEC = os.environ.get("ALPACA_API_SECRET_KEY")

# UI TFs -> Alpaca API timeframe strings
_TF_TO_ALPACA = {
    "5M": "5Min",
    "15M": "15Min",
    "1H": "1Hour",
    "1D": "1Day",
    "1W": "1Week",
    "1MO": "1Month",
    "1M": "1Min",
}

# UI TFs -> yfinance intervals (fallbacks keep your existing behavior)
TF_TO_INTERVAL = {
    "1D": "1d",
    "1W": "1wk",
    "1MO": "1mo",
    "1H": "1h",
    "15M": "15m",
    "5M": "5m",
    "1M": "1m",
}


def _period_to_delta(p: str) -> timedelta:
    p = (p or "").lower()
    if p in ("1h",):
        return timedelta(hours=1)
    if p in ("1d", "1day"):
        return timedelta(days=1)
    if p in ("7d", "1w"):
        return timedelta(days=7)
    if p in ("1m", "1mo"):
        return timedelta(days=30)
    if p in ("1y",):
        return timedelta(days=365)
    return timedelta(days=30)


def _is_crypto_symbol(sym: str) -> bool:
    s = (sym or "").upper()
    return s.endswith("-USD") or s.endswith("-USDT") or "/" in s


def _to_alpaca_crypto_symbol(sym: str) -> str:
    return sym.upper().replace("-", "/")


async def _alpaca_fetch(symbol: str, tf: str, lookback: str, limit: int = 1000) -> list[dict]:
    tf_api = _TF_TO_ALPACA.get(tf.upper())
    if not tf_api:
        return []

    now = datetime.now(timezone.utc)
    start = now - _period_to_delta(lookback)

    headers = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SEC}
    out = []

    try:
        async with httpx.AsyncClient(timeout=20) as client:

            if _is_crypto_symbol(symbol):
                alp_sym = _to_alpaca_crypto_symbol(symbol)
                url = "https://data.alpaca.markets/v1beta3/crypto/us/bars"
                params = {
                    "symbols": alp_sym,
                    "timeframe": tf_api,
                    "start": start.isoformat(),
                    "end": now.isoformat(),
                    "limit": str(limit),
                }
                r = await client.get(url, params=params, headers=headers)
                if r.status_code != 200:
                    flask_app.logger.warning(
                        f"[alpaca-crypto] {symbol} {tf_api} -> {r.status_code} {r.text[:200]}"
                    )
                    return []
                js = r.json() or {}
                series = (js.get("bars", {}) or {}).get(alp_sym, []) or []
                for b in series:
                    ts = pd.to_datetime(b.get("t"), utc=True)
                    out.append(
                        {
                            "time": int(ts.value // 10**9),
                            "open": float(b.get("o")),
                            "high": float(b.get("h")),
                            "low": float(b.get("l")),
                            "close": float(b.get("c")),
                        }
                    )

            else:
                url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
                params = {
                    "timeframe": tf_api,
                    "start": start.isoformat(),
                    "end": now.isoformat(),
                    "limit": str(limit),
                    "feed": "iex",
                }
                r = await client.get(url, params=params, headers=headers)
                if r.status_code != 200:
                    flask_app.logger.warning(
                        f"[alpaca-stock] {symbol} {tf_api} -> {r.status_code} {r.text[:200]}"
                    )
                    return []
                js = r.json() or {}
                series = js.get("bars", []) or []
                for b in series:
                    ts = pd.to_datetime(b.get("t"), utc=True)
                    out.append(
                        {
                            "time": int(ts.value // 10**9),
                            "open": float(b.get("o")),
                            "high": float(b.get("h")),
                            "low": float(b.get("l")),
                            "close": float(b.get("c")),
                        }
                    )
    except Exception as e:
        flask_app.logger.exception(f"[alpaca] fetch error for {symbol} {tf_api}: {e}")
        return []

    out.sort(key=lambda x: x["time"])
    return out


def _normalize_lookback_for_interval(interval: str, lookback: str) -> str:
    interval = (interval or "").lower()
    lb = (lookback or "").lower()

    if interval == "1m":
        return {"1h": "1d", "1d": "1d", "7d": "7d", "1w": "7d", "1m": "7d", "1mo": "7d"}.get(lb, "7d")
    if interval in ("5m", "15m"):
        return {"1d": "1d", "7d": "7d", "1w": "7d", "1m": "30d", "1mo": "30d", "1y": "60d"}.get(lb, "60d")
    if interval == "1h":
        return {
            "1d": "1d",
            "7d": "7d",
            "1w": "7d",
            "1m": "30d",
            "1mo": "30d",
            "1y": "1y",
            "2y": "2y",
        }.get(lb, "1y")
    if interval == "1wk":
        return "3mo" if lb in ("1d", "7d", "1w", "1mo") else (lb or "3mo")
    if interval == "1mo":
        return "6mo" if lb in ("1d", "7d", "1w", "1mo") else (lb or "6mo")
    return lb or "1mo"


def _bars_from_df(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    df = df.reset_index()
    time_col = "Datetime" if "Datetime" in df.columns else ("Date" if "Date" in df.columns else None)
    if time_col:
        ts = pd.to_datetime(df[time_col], utc=True)
    else:
        ts = pd.to_datetime(df.index, utc=True)
    df["time"] = (ts.view("int64") // 10**9).astype(int)
    for c in ("Open", "High", "Low", "Close"):
        if c not in df.columns and c.lower() in df.columns:
            df[c] = df[c.lower()]
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return [
        {
            "time": int(r["time"]),
            "open": float(r["Open"]),
            "high": float(r["High"]),
            "low": float(r["Low"]),
            "close": float(r["Close"]),
        }
        for _, r in df.iterrows()
    ]


def _stooq_daily(ticker: str, lookback: str = "1mo") -> list[dict]:
    def try_one(sym: str) -> pd.DataFrame | None:
        url = f"https://stooq.com/q/d/l/?s={sym.lower()}&i=d"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        text = r.text or ""
        if "Date,Open,High,Low,Close,Volume" not in text:
            return None
        return pd.read_csv(io.StringIO(text))

    df = try_one(ticker) or try_one(f"{ticker}.us")
    if df is None or df.empty:
        return []
    days_map = {"1D": 2, "1W": 8, "1M": 32, "1Y": 380}
    ndays = days_map.get(lookback.upper(), 32)
    df["Date"] = pd.to_datetime(df["Date"], utc=True)
    df = df.sort_values("Date").tail(ndays)
    return _bars_from_df(df)


def fetch_bars_yf(ticker: str, tf: str = "1D", lookback: str = "1mo") -> list[dict]:
    if ALPACA_KEY and ALPACA_SEC:
        try:
            try:
                bars = asyncio.run(_alpaca_fetch(ticker, tf, lookback))
            except RuntimeError:
                loop = asyncio.get_event_loop()
                bars = loop.run_until_complete(_alpaca_fetch(ticker, tf, lookback))
            if bars:
                return bars
        except Exception as e:
            flask_app.logger.warning(f"[alpaca-first] failed -> fallback to yfinance: {e}")

    interval = TF_TO_INTERVAL.get(tf.upper(), "1d")
    lookback_norm = _normalize_lookback_for_interval(interval, lookback)
    try:
        df = yf.download(
            tickers=ticker,
            period=lookback_norm,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        bars = _bars_from_df(df)
        if bars:
            return bars
        flask_app.logger.warning(
            f"[yf.download] EMPTY for {ticker} interval={interval} period={lookback_norm} shape={getattr(df,'shape',None)}"
        )
    except Exception as e:
        flask_app.logger.exception(
            f"[yf.download] failed for {ticker} interval={interval} period={lookback_norm}: {e}"
        )

    try:
        t = yf.Ticker(ticker)
        df = t.history(period=lookback_norm, interval=interval, auto_adjust=False)
        bars = _bars_from_df(df)
        if bars:
            return bars
        flask_app.logger.warning(
            f"[ticker.history] EMPTY for {ticker} interval={interval} period={lookback_norm} shape={getattr(df,'shape',None)}"
        )
    except Exception as e:
        flask_app.logger.exception(
            f"[ticker.history] failed for {ticker} interval={interval} period={lookback_norm}: {e}"
        )

    if tf.upper() == "1D":
        stooq = _stooq_daily(ticker, lookback=lookback)
        if stooq:
            flask_app.logger.info(
                f"[stooq] used fallback for {ticker} {lookback} -> {len(stooq)} bars"
            )
            return stooq

    flask_app.logger.error(f"NO DATA for {ticker} tf={tf} lookback={lookback}. Returning [].")
    return []


# -------------------- Flask pages --------------------
@flask_app.get("/detections")
def detections_page():
    return render_template("detections.html")


@flask_app.route("/")
def home():
    return render_template("index.html")


@flask_app.route("/upload-page")
def upload_page():
    return render_template("upload.html")


@flask_app.route("/library")
def library():
    return render_template("library.html")


@flask_app.route("/health")
def health():
    return jsonify({"ok": True, "vocab": VOCAB})


# -------------------- Flask API --------------------
@flask_app.get("/api/bars")
def api_bars_flask():
    ticker = request.args.get("ticker", "AAPL").upper()
    tf = request.args.get("tf", "1D").upper()
    look = request.args.get("lookback", "1mo")

    bars = fetch_bars_yf(ticker, tf, look)

    flask_app.logger.info(f"/api/bars -> {ticker} {tf} {look} count={len(bars)}")
    if bars:
        flask_app.logger.info(f"first bar: {bars[0]}")
        last = bars[-1]
        flask_app.logger.info(
            f"last bar: time={last['time']} "
            f"ohlc=({last['open']}, {last['high']}, {last['low']}, {last['close']})"
        )

    resp = jsonify(bars)
    resp.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@flask_app.get("/api/markers")
def api_markers_flask():
    resp = jsonify([])
    resp.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@flask_app.get("/api/detections")
def api_detections_flask():
    ticker = request.args.get("ticker", "AAPL").upper()
    tf = request.args.get("tf", "1D").upper()
    look = request.args.get("lookback", "1mo")

    bars = fetch_bars_yf(ticker, tf, look)
    if not bars:
        resp = jsonify([])
        resp.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
        return resp

    key = (ticker, tf, look)
    last_time = _bars_last_time(bars)
    cached = _DETS_CACHE.get(key)
    if cached and cached.get("last_time") == last_time:
        dets = cached.get("dets", [])
    else:
        df = pd.DataFrame(bars).rename(
            columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}
        )
        dets = safe_scan(df, min_abs=80, max_bars=400, top_k=50)
        _DETS_CACHE[key] = {"last_time": last_time, "dets": dets, "ts": time.time()}

    resp = jsonify(dets)
    resp.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@flask_app.get("/partials/detections")
def partials_detections_flask():
    return ""


# -------------------- Upload endpoint --------------------
@flask_app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        r = make_response()
        r.headers.add("Access-Control-Allow-Origin", "*")
        r.headers.add("Access-Control-Allow-Headers", "Content-Type")
        r.headers.add("Access-Control-Allow-Methods", "POST")
        return r

    f = request.files.get("image")
    if not f:
        r = jsonify({"message": "❌ No image received"})
        r.headers.add("Access-Control-Allow-Origin", "*")
        return r, 400

    try:
        pil = Image.open(f.stream)
        pil = ImageOps.exif_transpose(pil)
        pil = pil.convert("RGB")

        pred_class, pred_idx, probs = learn.predict(pil)
        top5 = sorted(
            [{"label": l, "p": float(p)} for l, p in zip(learn.dls.vocab, probs.tolist())],
            key=lambda x: x["p"],
            reverse=True,
        )[:5]
        topi = int(probs.argmax().item())

        r = jsonify(
            {
                "prediction": str(pred_class),
                "index": topi,
                "confidence": float(probs[topi]),
                "top5": top5,
            }
        )
        r.headers.add("Access-Control-Allow-Origin", "*")
        return r, 200

    except Exception as e:
        flask_app.logger.exception("Prediction failed")
        r = jsonify({"message": f"❌ Prediction error: {e}"})
        r.headers.add("Access-Control-Allow-Origin", "*")
        return r, 500


# ---- Mount Flask under /flask so Uvicorn (ASGI) can serve it ----
app.mount("/flask", WSGIMiddleware(flask_app))


# -------------------- FastAPI mirrors --------------------
@app.get("/api/bars")
def api_bars_fastapi():
    ticker = "AAPL"
    tf = "1D"
    look = "1mo"
    bars = fetch_bars_yf(ticker, tf, look)
    return JSONResponse(bars)


@app.get("/api/markers")
def api_markers_fastapi():
    return JSONResponse([])


@app.get("/api/detections")
def api_detections_fastapi():
    ticker = "AAPL"
    tf = "1D"
    look = "1mo"
    bars = fetch_bars_yf(ticker, tf, look)
    if not bars:
        return JSONResponse([])
    df = pd.DataFrame(bars).rename(
        columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}
    )
    dets = scan_patterns(df, min_abs=20, last_n=400) if HAS_TALIB else []
    dets = dets[:50]
    return JSONResponse(dets)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=True)