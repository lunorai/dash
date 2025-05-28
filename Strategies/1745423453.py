import pandas as pd
import numpy as np

def _find_close_col(symbol: str, anchors: pd.DataFrame) -> str:
    for c in (f"close_{symbol}_1H", f"close_{symbol}"):
        if c in anchors.columns:
            return c
    for c in anchors.columns:
        if f"close_{symbol}" in c:
            return c
    raise ValueError(f"close column for {symbol} not found")

def generate_signals(
    candles_target: pd.DataFrame,
    candles_anchor: pd.DataFrame,
    *,
    threshold: float = 0.01,
    max_ldo_volatility: float = 0.03,
    trailing_stop_threshold: float = 0.05,
    trailing_stop_exit: float = 0.02,
    cooldown_period: int = 2,
    tp_mult: float = 0.27,
    sl_mult: float = -0.05,
) -> pd.DataFrame:

    anchors = candles_anchor.iloc[: len(candles_target)].reset_index(drop=True)
    df = candles_target[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    df["close_BTC"] = anchors[_find_close_col("BTC", anchors)].values
    df["close_ETH"] = anchors[_find_close_col("ETH", anchors)].values

    ts = pd.to_datetime(df["timestamp"], utc=True)
    df["day"] = ts.dt.date

    # ------------ Feature Engineering ----------------------
    df["return_BTC_4h"] = df["close_BTC"].pct_change().shift(4)
    df["return_BTC_3h"] = df["close_BTC"].pct_change(3).shift(3)
    df["return_ETH_4h"] = df["close_ETH"].pct_change().shift(4)
    df["return_ETH_3h"] = df["close_ETH"].pct_change(3).shift(3)

    df["return_LDO_3h"] = df["close"].pct_change(3)
    df["return_LDO_6h"] = df["close"].pct_change(6)

    df["volume_avg_6h"] = df["volume"].rolling(6).mean()
    df["volume_surge"] = df["volume"] > 1.2 * df["volume_avg_6h"]

    df["ldo_std_4h"] = df["close"].rolling(4).std()
    df["vol_BTC_2h"] = df["close_BTC"].pct_change(2)
    df["vol_ETH_2h"] = df["close_ETH"].pct_change(2)

    df["trend_BTC_4h"] = df["close_BTC"].pct_change(4)
    df["trend_ETH_4h"] = df["close_ETH"].pct_change(4)

    df["range"] = df["high"] - df["low"]
    df["range_median_6h"] = df["range"].rolling(6).median()
    df["sideways"] = df["range"] < 0.002 * df["close"]

    # ------------ RSI È™i MACD DIRECT Ã®n funcÈ›ie -----------------
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - 100 / (1 + rs)

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    df.fillna(0, inplace=True)

    # ------------ Loop principal ---------------------------
    signals = []
    position = None
    entry_price = peak_ret = 0.0
    cooldown = 0

    for _, r in df.iterrows():
        if cooldown > 0:
            cooldown -= 1
            signals.append("HOLD")
            continue

        intended = "HOLD"

        if position == "LONG":
            ret = (r["close"] - entry_price) / entry_price
            peak_ret = max(peak_ret, ret)
            if peak_ret >= trailing_stop_threshold and ret <= trailing_stop_exit:
                intended = "SELL"
            elif ret >= tp_mult or ret <= sl_mult:
                intended = "SELL"

        else:
            trigger = (
                (r["return_BTC_4h"] > threshold and r["return_BTC_3h"] > 0.002) or
                (r["return_ETH_4h"] > threshold and r["return_ETH_3h"] > 0.002)
            )
            volatility_ok = abs(r["vol_BTC_2h"]) > 0.002 or abs(r["vol_ETH_2h"]) > 0.002
            trend_ok      = r["trend_BTC_4h"] > -0.025 or r["trend_ETH_4h"] > -0.025
            ldo_vol_ok    = r["ldo_std_4h"] < max_ldo_volatility
            anti_fomo     = r["return_LDO_6h"] <= 0.03
            range_ok      = r["range"] < 2.5 * r["range_median_6h"]
            rsi_ok        = 25 < r["rsi"] < 55
            macd_ok       = r["macd"] > r["macd_signal"]

            if (
                trigger and ldo_vol_ok and anti_fomo and not r["sideways"]
                and r["return_LDO_3h"] > 0 and r["volume_surge"]
                and volatility_ok and trend_ok and range_ok
                and rsi_ok and macd_ok
            ):
                intended = "BUY"

        if intended == "BUY" and position is None:
            position = "LONG"
            entry_price = r["close"]
            peak_ret = 0.0
            signal = "BUY"

        elif intended == "SELL" and position == "LONG":
            position = None
            entry_price = peak_ret = 0.0
            cooldown = cooldown_period
            signal = "SELL"

        else:
            signal = "HOLD"

        signals.append(signal)
    if position == "LONG":
        signals[-1] = "SELL"


    return pd.DataFrame({"timestamp": df["timestamp"], "signal": signals})

def get_coin_metadata():
    return {
        "target":  {"symbol": "LDO", "timeframe": "1H"},
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"},
            {"symbol": "ETH", "timeframe": "1H"},
        ],
    }