# === strategy.py (submission finale Lunor â€” RAY vs BTC+ETH+SOL) ===
import pandas as pd
import numpy as np

def get_coin_metadata():
    return {
        "target": {"symbol": "RAY", "timeframe": "1H"},
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"},
            {"symbol": "ETH", "timeframe": "1H"},
            {"symbol": "SOL", "timeframe": "1H"}
        ]
    }

def generate_signals(
    candles_target: pd.DataFrame,
    candles_anchor: pd.DataFrame
) -> pd.DataFrame:

    # === ParamÃ¨tres optimisÃ©s ===
    threshold = 0.02
    lag = 6
    confirm_ray = True
    volatility_filter = 0.02
    volume_filter_enabled = True
    holding_period = 3
    min_volume_ratio = 0.7
    sma_window_ray = 5
    vol_window_anchor = 6
    volume_window_anchor = 12
    extend_hold_after_signal = False
    signal_smoothing = 1
    weight_btc = 0.2
    weight_eth = 0.2
    weight_sol = 0.6

    # === PrÃ©paration des donnÃ©es
    df = pd.merge(candles_target, candles_anchor, on="timestamp", how="inner")
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Retours individuels des ancres
    df["ret_BTC"] = df["close_BTC_1H"].pct_change()
    df["ret_ETH"] = df["close_ETH_1H"].pct_change()
    df["ret_SOL"] = df["close_SOL_1H"].pct_change()

    # Moyenne pondÃ©rÃ©e dynamique des retours
    df["ret_anchor"] = (
        weight_btc * df["ret_BTC"] +
        weight_eth * df["ret_ETH"] +
        weight_sol * df["ret_SOL"]
    )
    df["ret_anchor_lag"] = df["ret_anchor"].shift(lag)

    # RAY
    df["ret_RAY"] = df["close"].pct_change()
    df["sma_RAY"] = df["close"].rolling(sma_window_ray).mean()
    df["momentum_RAY"] = df["close"] > df["sma_RAY"]

    # VolatilitÃ© et volume combinÃ© des ancres
    df["vol_anchor"] = (
        df["close_BTC_1H"].rolling(vol_window_anchor).std() +
        df["close_ETH_1H"].rolling(vol_window_anchor).std() +
        df["close_SOL_1H"].rolling(vol_window_anchor).std()
    ) / 3

    df["avg_volumes"] = (
        df["volume_BTC_1H"].rolling(volume_window_anchor).mean() +
        df["volume_ETH_1H"].rolling(volume_window_anchor).mean() +
        df["volume_SOL_1H"].rolling(volume_window_anchor).mean()
    ) / 3

    df["volumes_now"] = (
        df["volume_BTC_1H"] +
        df["volume_ETH_1H"] +
        df["volume_SOL_1H"]
    ) / 3

    df["volume_ratio"] = df["volumes_now"] / (df["avg_volumes"] + 1e-9)

    # Conditions
    condition_buy = df["ret_anchor_lag"] > threshold
    condition_sell = df["ret_anchor_lag"] < -threshold

    if confirm_ray:
        condition_buy &= (df["ret_RAY"] > 0) & df["momentum_RAY"]
        condition_sell &= (df["ret_RAY"] < 0) & (~df["momentum_RAY"])

    if volatility_filter:
        condition_buy &= df["vol_anchor"] > volatility_filter
        condition_sell &= df["vol_anchor"] > volatility_filter

    if volume_filter_enabled:
        condition_buy &= df["volume_ratio"] > min_volume_ratio
        condition_sell &= df["volume_ratio"] > min_volume_ratio

    for i in range(signal_smoothing - 1):
        condition_buy &= df["ret_anchor_lag"].shift(i) > threshold
        condition_sell &= df["ret_anchor_lag"].shift(i) < -threshold

    df["signal"] = "HOLD"
    df.loc[condition_buy, "signal"] = "BUY"
    df.loc[condition_sell, "signal"] = "SELL"

    if extend_hold_after_signal:
        for i in range(1, holding_period):
            df["signal"] = df["signal"].mask((df["signal"].shift(i) == "BUY") & (df["signal"] == "HOLD"), "BUY")
            df["signal"] = df["signal"].mask((df["signal"].shift(i) == "SELL") & (df["signal"] == "HOLD"), "SELL")

    return df[["timestamp", "signal"]]