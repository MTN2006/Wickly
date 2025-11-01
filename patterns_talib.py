# patterns_talib.py
import time as _time
import numpy as np
import pandas as pd

try:
    import talib
except Exception as e:
    raise RuntimeError("TA-Lib not installed or not importable") from e

# Map TA-Lib function names you want (about ~60 common ones):
_PATTERN_FUNCS = [
    "CDL2CROWS","CDL3BLACKCROWS","CDL3INSIDE","CDL3LINESTRIKE","CDL3OUTSIDE","CDL3STARSINSOUTH",
    "CDL3WHITESOLDIERS","CDLABANDONEDBABY","CDLADVANCEBLOCK","CDLBELTHOLD","CDLBREAKAWAY",
    "CDLCLOSINGMARUBOZU","CDLCONCEALBABYSWALL","CDLCOUNTERATTACK","CDLDARKCLOUDCOVER",
    "CDLDOJI","CDLDOJISTAR","CDLDRAGONFLYDOJI","CDLENGULFING","CDLEVENINGDOJISTAR",
    "CDLEVENINGSTAR","CDLGAPSIDESIDEWHITE","CDLGRAVESTONEDOJI","CDLHAMMER","CDLHANGINGMAN",
    "CDLHARAMI","CDLHARAMICROSS","CDLHIGHWAVE","CDLHIKKAKE","CDLHOMINGPIGEON","CDLIDENTICAL3CROWS",
    "CDLINNECK","CDLINVERTEDHAMMER","CDLKICKING","CDLKICKINGBYLENGTH","CDLLADDERBOTTOM",
    "CDLLONGLEGGEDDOJI","CDLLONGLINE","CDLMARUBOZU","CDLMATCHINGLOW","CDLMATHOLD","CDLMORNINGDOJISTAR",
    "CDLMORNINGSTAR","CDLONNECK","CDLPIERCING","CDLRICKSHAWMAN","CDLRISEFALL3METHODS","CDLSEPARATINGLINES",
    "CDLSHOOTINGSTAR","CDLSHORTLINE","CDLSPINNINGTOP","CDLSTALLEDPATTERN","CDLSTICKSANDWICH",
    "CDLTAKURI","CDLTASUKIGAP","CDLTHRUSTING","CDLTRISTAR","CDLUNIQUE3RIVER","CDLUPSIDEGAP2CROWS",
    "CDLXSIDEGAP3METHODS"
]

# Nicenames and direction mapping
def _dir_from_val(v):
    if v > 0:  return "bullish"
    if v < 0:  return "bearish"
    return "neutral"

def _pretty_name(fn):
    # turn CDLENGULFING -> Engulfing
    s = fn[3:] if fn.startswith("CDL") else fn
    return s.title().replace("3", " Three ").replace("2", " Two ")

# Per-pattern cooldown in seconds (e.g., 10 minutes for 1m charts)
_DEFAULT_COOLDOWN_SEC = 600

# Runtime cache (pattern -> last_emit_unix)
_last_emit_at = {}

def scan_patterns(df: pd.DataFrame, min_abs: int = 20, cooldown_sec: int | None = None):
    """
    Scan TA-Lib candle patterns and return recent edge-triggered detections.

    - min_abs: absolute value threshold; TA-Lib returns larger magnitude for “stronger” matches
    - cooldown_sec: minimum seconds between emissions for the same pattern (suppresses spam)
    """
    if df is None or df.empty:
        return []

    cooldown = _DEFAULT_COOLDOWN_SEC if cooldown_sec is None else cooldown_sec

    # Require columns with exact names used here
    for c in ("Open","High","Low","Close"):
        if c not in df.columns:
            raise ValueError("scan_patterns expects columns: Open, High, Low, Close")

    o = df["Open"].astype(float).values
    h = df["High"].astype(float).values
    l = df["Low"].astype(float).values
    c_ = df["Close"].astype(float).values

    n = len(df)
    if n < 5:
        return []

    out = []
    now_unix = int(_time.time())

    # We only consider the last CLOSED bar -> index n-2
    i = n - 2
    for fn in _PATTERN_FUNCS:
        func = getattr(talib, fn)
        vals = func(o, h, l, c_)  # vector of ints
        if vals is None or len(vals) != n:
            continue

        curr = int(vals[i])
        prev = int(vals[i-1]) if i-1 >= 0 else 0

        # Edge trigger: previously 0, now non-zero and strong enough
        if prev == 0 and curr != 0 and abs(curr) >= min_abs:
            pattern = fn
            pdir = _dir_from_val(curr)

            # Cooldown
            last_ts = _last_emit_at.get(pattern)
            if last_ts is not None and (now_unix - last_ts) < cooldown:
                continue

            # Emit
            out.append({
                "pattern": pattern,
                "name": _pretty_name(pattern),
                "dir": pdir,
                "value": int(curr),
                "time": int(df.iloc[i]["time"]) if "time" in df.columns else None,
                "index": int(i),
            })
            _last_emit_at[pattern] = now_unix

    # Sort by absolute strength desc, then most recent first (same time)
    out.sort(key=lambda d: (abs(d["value"]), d.get("time", 0)), reverse=True)
    # Cap results (sidebar)
    return out[:50]