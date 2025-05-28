import pandas as pd

def get_coin_metadata() -> dict:
    """
    Strategy metadata: target=LDO 1H; anchors=BTC and ETH 1H.
    """
    return {
        "target":   {"symbol": "LDO", "timeframe": "1H"},
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"},
            {"symbol": "ETH", "timeframe": "1H"}
        ]
    }


def generate_signals(
        candles_target: pd.DataFrame,
        candles_anchor: pd.DataFrame,
        ema_short_period_anchor: int = 9,
        ema_long_period_anchor: int = 21,
        signal_lag: int = 1,
        profit_threshold: float = 0.02,  # Minimum 1% profit target
        anchor_rule: str = "any"  # 'any' or 'all' anchors must be bullish
) -> pd.DataFrame:
    """
    Generates trading signals based on anchor asset momentum and target asset local min/max.

    Args:
        candles_target (pd.DataFrame): DataFrame with 'timestamp' and 'close' for the target asset.
        candles_anchor (pd.DataFrame): DataFrame with 'timestamp' and 'close_SYMBOL_TIMEFRAME' columns for anchor assets.
        ema_short_period_anchor (int): Short EMA period for anchor asset momentum.
        ema_long_period_anchor (int): Long EMA period for anchor asset momentum.
        signal_lag (int): Lag applied to anchor momentum signal before making a trading decision on the target.
        profit_threshold (float): Minimum profit required for a trade to be considered valid (e.g., 0.01 for 1%).
        anchor_rule (str): 'any' or 'all'. Determines if any or all anchors must show bullish momentum.

    Returns:
        pd.DataFrame: DataFrame with 'timestamp' and 'signal' ('BUY', 'SELL', 'HOLD').
    """
    meta = get_coin_metadata()

    # 1. Data Preparation and Validation
    # Ensure candles_target has 'timestamp' and 'close'
    if not all(col in candles_target.columns for col in ["timestamp", "close"]):
        raise ValueError("candles_target must contain 'timestamp' and 'close' columns.")

    anchor_cols_meta = [
        f"close_{a['symbol']}_{a['timeframe']}" for a in meta["anchors"]
    ]
    missing_anchors = set(anchor_cols_meta) - set(candles_anchor.columns)
    if missing_anchors:
        raise KeyError(f"candles_anchor missing columns: {missing_anchors}")

    # Merge target and anchor data
    df = pd.merge(
        candles_target[["timestamp", "close"]].rename(columns={"close": "target_close"}),
        candles_anchor[["timestamp"] + anchor_cols_meta],
        on="timestamp",
        how="inner"
    ).sort_values("timestamp").reset_index(drop=True)

    if df.empty or len(df) < max(ema_long_period_anchor, 3):  # Need enough data for EMAs and min/max
        return pd.DataFrame(columns=["timestamp", "signal"])

    # 2. Anchor Momentum Calculation
    anchor_bullish_signals = pd.DataFrame(index=df.index)
    for anchor_col_name in anchor_cols_meta:
        df[f'{anchor_col_name}_ema_short'] = df[anchor_col_name].ewm(span=ema_short_period_anchor, adjust=False,
                                                                     min_periods=ema_short_period_anchor).mean()
        df[f'{anchor_col_name}_ema_long'] = df[anchor_col_name].ewm(span=ema_long_period_anchor, adjust=False,
                                                                    min_periods=ema_long_period_anchor).mean()
        anchor_bullish_signals[f'{anchor_col_name}_bullish'] = df[f'{anchor_col_name}_ema_short'] > df[
            f'{anchor_col_name}_ema_long']

    if anchor_rule == "any":
        df["anchor_momentum_bullish"] = anchor_bullish_signals.any(axis=1)
    elif anchor_rule == "all":
        df["anchor_momentum_bullish"] = anchor_bullish_signals.all(axis=1)
    else:
        raise ValueError("anchor_rule must be 'any' or 'all'")

    # Apply signal lag to anchor momentum
    df["anchor_momentum_bullish_lagged"] = df["anchor_momentum_bullish"].shift(signal_lag).fillna(False)

    # 3. Target Local Min/Max Detection
    target_close_prices = df['target_close'].values
    local_min_indices = []
    local_max_indices = []

    # Adjusted range to ensure indices are valid for price array
    for i in range(1, len(target_close_prices) - 1):
        if target_close_prices[i] < target_close_prices[i - 1] and target_close_prices[i] < target_close_prices[i + 1]:
            local_min_indices.append(i)
        elif target_close_prices[i] > target_close_prices[i - 1] and target_close_prices[i] > target_close_prices[
            i + 1]:
            local_max_indices.append(i)

    df["is_local_min"] = False
    if local_min_indices:  # Check if list is not empty
        df.loc[df.index[local_min_indices], "is_local_min"] = True

    df["is_local_max"] = False
    if local_max_indices:  # Check if list is not empty
        df.loc[df.index[local_max_indices], "is_local_max"] = True

    # 4. Signal Generation (Initial Pass)
    signals = ["HOLD"] * len(df)
    position = 0  # 0 = out of market, 1 = long
    trade_indices_for_filtering = []  # Store (buy_idx, sell_idx) pairs for profit filtering
    last_buy_idx = None

    for i in range(len(df)):
        # Skip if not enough data for lagged signals or min/max (first few rows)
        if i < signal_lag or i == 0 or i == len(df) - 1:  # also ensure i+1 is valid for local_max check
            continue

        # BUY Condition
        if position == 0 and df.loc[i, "anchor_momentum_bullish_lagged"] and df.loc[i, "is_local_min"]:
            signals[i] = "BUY"
            position = 1
            last_buy_idx = i
        # SELL Condition
        elif position == 1 and df.loc[i, "is_local_max"]:
            signals[i] = "SELL"
            position = 0
            if last_buy_idx is not None:
                trade_indices_for_filtering.append((last_buy_idx, i))
                last_buy_idx = None
        # else: signals[i] remains "HOLD"

    # 5. Trade Filtering (Profit Threshold)
    signals_filtered = signals.copy()
    if profit_threshold > -1.0:  # Allow disabling filter with negative threshold if desired, but generally >0
        for buy_idx, sell_idx in trade_indices_for_filtering:
            buy_price = df.loc[buy_idx, 'target_close']
            sell_price = df.loc[sell_idx, 'target_close']

            if pd.isna(buy_price) or pd.isna(sell_price) or buy_price == 0:  # Avoid division by zero or NaN issues
                profit = -1  # Consider it a failed trade
            else:
                profit = (sell_price - buy_price) / buy_price

            if profit < profit_threshold:
                signals_filtered[buy_idx] = "HOLD"
                signals_filtered[sell_idx] = "HOLD"
                # If a trade is invalidated, we don't try to re-enter immediately or change state,
                # the original position logic already handled that for the next iteration.

    final_signal_df = df[["timestamp"]].copy()
    final_signal_df["signal"] = signals_filtered
    return final_signal_df