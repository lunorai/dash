import pandas as pd
import numpy as np

def generate_signals(ray_df: pd.DataFrame, btc_df: pd.DataFrame, window: int = 24, corr_threshold: float = 0.6) -> pd.DataFrame:
    """
    Strategy: Buy LDO if BTC or ETH pumped >2% exactly 4 hours ago.

    Inputs:
    - candles_target: OHLCV for LDO (1H)
    - candles_anchor: Merged OHLCV with columns 'close_BTC' and 'close_ETH' (1H)

    Output:
    - DataFrame with ['timestamp', 'signal']
    """
    # try:
    #     print(candles_anchor.head())
    #     df = pd.merge(
    #         candles_target[['timestamp', 'close']],
    #         candles_anchor[['timestamp', 'close_BTC_1H', 'close_ETH_1H']],
    #         on='timestamp',
    #         how='inner'
    #     )

        # df['btc_return_4h_ago'] = df['close_BTC'].pct_change().shift(4)
        # df['eth_return_4h_ago'] = df['close_ETH'].pct_change().shift(4)

        # signals = []
        # for i in range(len(df)):
        #     btc_pump = df['btc_return_4h_ago'].iloc[i] > 0.02
        #     eth_pump = df['eth_return_4h_ago'].iloc[i] > 0.02
        #     if btc_pump or eth_pump:
        #         signals.append('BUY')
        #     else:
        #         signals.append('HOLD')

        # df['signal'] = signals
        # lag = 4
        # window = 20
        # df['btc_return_lag'] = df['close_BTC_1H'].pct_change().shift(lag)
        # df['btc_mean'] = df['btc_return_lag'].rolling(window).mean()
        # df['btc_std'] = df['btc_return_lag'].rolling(window).std()
        # df['btc_z'] = (df['btc_return_lag'] - df['btc_mean']) / (df['btc_std'] + 1e-8)
        # signals = []
        # for i in range(len(df)):
        #     if df['btc_z'].iloc[i] > 1:
        #         signals.append('BUY')
        #     elif df['btc_z'].iloc[i] < -1:
        #         signals.append('SELL')
        #     else:
        #         signals.append('HOLD')
        # df['signal'] = signals
        
    # window = 14  # RSI window
    # merged = pd.merge(
    #     ray_df[["timestamp", "close"]].rename(columns={"close": "ray_close"}),
    #     btc_df[["timestamp", "close_BTC_1H"]].rename(columns={"close_BTC_1H": "btc_close"}),
    #     on="timestamp", how="inner"
    # )

    # def compute_rsi(prices, window=14):
    #     delta = prices.diff()
    #     gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    #     loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    #     rs = gain / (loss + 1e-8)
    #     rsi = 100 - (100 / (1 + rs))
    #     return rsi

    # merged["btc_rsi"] = compute_rsi(merged["btc_close"], window)

    # signals = []
    # in_position = False
    # for idx in range(len(merged)):
    #     if idx < window:
    #         signals.append("HOLD")
    #         continue
    #     rsi_prev = merged["btc_rsi"].iloc[idx-1]
    #     rsi_curr = merged["btc_rsi"].iloc[idx]
    #     if rsi_prev < 30 and rsi_curr > 30:
    #         signals.append("BUY")
    #         in_position = True
    #     elif rsi_prev > 70 and rsi_curr < 70:
    #         signals.append("SELL")
    #         in_position = False
    #     else:
    #         signals.append("HOLD")

    # signal_df = merged[["timestamp"]].copy()
    # signal_df["signal"] = signals
    # return signal_df

    # # except Exception as e:
    # #     raise RuntimeError(f"Error in generate_signals: {e}")
    merged = ray_df[["timestamp", "close"]].copy()
    close_prices = merged['close'].values
    local_min = []
    local_max = []
    for i in range(1, len(close_prices)-1):
        if close_prices[i] < close_prices[i-1] and close_prices[i] < close_prices[i+1]:
            local_min.append(i)
        elif close_prices[i] > close_prices[i-1] and close_prices[i] > close_prices[i+1]:
            local_max.append(i)

    signals = []
    position = 0  # 0 = out of market, 1 = long
    trade_indices = []  # Store (buy_idx, sell_idx) pairs
    last_buy_idx = None
    # First pass: generate raw signals and record trade indices
    for i in range(len(merged)):
        if i <= 0:
            signals.append("HOLD")
            continue
        if i in local_min and position == 0:
            signals.append("BUY")
            position = 1
            last_buy_idx = i
        elif i in local_max and position == 1:
            signals.append("SELL")
            position = 0
            if last_buy_idx is not None:
                trade_indices.append((last_buy_idx, i))
                last_buy_idx = None
        else:
            signals.append("HOLD")

    # Second pass: filter out noisy trades (profit < threshold)
    threshold = 0.05  # 0.5% minimum profit required
    signals_filtered = signals.copy()
    for buy_idx, sell_idx in trade_indices:
        buy_price = close_prices[buy_idx]
        sell_price = close_prices[sell_idx]
        profit = (sell_price - buy_price) / buy_price
        if profit < threshold:
            signals_filtered[buy_idx] = "HOLD"
            signals_filtered[sell_idx] = "HOLD"

    signal_df = merged[["timestamp"]].copy()
    signal_df["signal"] = signals_filtered
    return signal_df

    # --- Updated: Significant local min/max strategy for higher Sharpe ratio ---
    # merged = ray_df[["timestamp", "close"]].copy()
    # close_prices = merged['close'].values
    # threshold = 0.001  # Require at least 1% move from previous extrema
    # significant_min = []
    # significant_max = []
    # last_extrema = None
    # last_extrema_price = None
    # for i in range(1, len(close_prices)-1):
    #     if close_prices[i] < close_prices[i-1] and close_prices[i] < close_prices[i+1]:
    #         if last_extrema == "max" and last_extrema_price is not None:
    #             if (last_extrema_price - close_prices[i]) / last_extrema_price > threshold:
    #                 significant_min.append(i)
    #                 last_extrema = "min"
    #                 last_extrema_price = close_prices[i]
    #         else:
    #             last_extrema = "min"
    #             last_extrema_price = close_prices[i]
    #     elif close_prices[i] > close_prices[i-1] and close_prices[i] > close_prices[i+1]:
    #         if last_extrema == "min" and last_extrema_price is not None:
    #             if (close_prices[i] - last_extrema_price) / last_extrema_price > threshold:
    #                 significant_max.append(i)
    #                 last_extrema = "max"
    #                 last_extrema_price = close_prices[i]
    #         else:
    #             last_extrema = "max"
    #             last_extrema_price = close_prices[i]
    # signals = []
    # position = 0  # 0 = out of market, 1 = long
    # for i in range(len(merged)):
    #     if i <= 0:
    #         signals.append("HOLD")
    #         continue
    #     if i in significant_min and position == 0:
    #         signals.append("BUY")
    #         position = 1
    #     elif i in significant_max and position == 1:
    #         signals.append("SELL")
    #         position = 0
    #     else:
    #         signals.append("HOLD")
    # signal_df = merged[["timestamp"]].copy()
    # signal_df["signal"] = signals
    # return signal_df

    # --- New: Buy only if expected profit/preceding drop ratio is above threshold ---
    # merged = ray_df[["timestamp", "close"]].copy()
    # close_prices = merged['close'].values
    # threshold_ratio = 0.3  # Require profit to be at least 50% of the drop from last sell to current buy
    # local_min = []
    # local_max = []
    # lastmax=-1
    # for i in range(1, len(close_prices)-1):
    #     if close_prices[i] < close_prices[i-1] and close_prices[i] < close_prices[i+1]:
    #         if lastmax!=-1:
    #             if close_prices[lastmax]-close_prices[i]<0.001*close_prices[lastmax]:
    #                 local_min.append(i)
    #                 continue
    #             else:
    #                 continue
    #                 #local_min.append((i+lastmax*(close_prices[lastmax]-close_prices[i]))//2)
    #         else:
    #             local_min.append(i)
                
            
    #     elif close_prices[i] > close_prices[i-1] and close_prices[i] > close_prices[i+1]:
    #         local_max.append(i)
    #         lastmax=i

    # signals = []
    # position = 0  # 0 = out of market, 1 = long
    # last_sell = None
    # for i in range(len(merged)):
    #     if i <= 0:
    #         signals.append("HOLD")
    #         continue
    #     # Only buy at local min if expected profit/preceding drop ratio is above threshold
    #     if i in local_min and position == 0:
    #         # Look ahead for the next local max after this min
    #         next_max = next((j for j in local_max if j > i), None)
    #         if last_sell is not None and next_max is not None:
    #             drop = last_sell - close_prices[i]
    #             profit = close_prices[next_max] - close_prices[i]
    #             ratio = profit / drop if drop > 0 else 0
    #             if  ratio >= 0*threshold_ratio*close_prices[i]:
    #                 signals.append("BUY")
    #                 position = 1
    #             else:
    #                 signals.append("HOLD")
    #         elif last_sell is None and next_max is not None:
    #             # First trade, just buy if profit is positive
    #             if close_prices[next_max] > close_prices[i]:
    #                 signals.append("BUY")
    #                 position = 1
    #             else:
    #                 signals.append("HOLD")
    #         else:
    #             signals.append("HOLD")
    #     elif i in local_max and position == 1:
    #         signals.append("SELL")
    #         position = 0
    #         last_sell = close_prices[i]
    #     else:
    #         signals.append("HOLD")
    # signal_df = merged[["timestamp"]].copy()
    # signal_df["signal"] = signals
    # return signal_df

def get_coin_metadata() -> dict:
    """
    Specifies the target and anchor coins used in this strategy.

    Returns:
    {
        "target": {"symbol": "LDO", "timeframe": "1H"},
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"},
            {"symbol": "ETH", "timeframe": "1H"}
        ]
    }
    """
    return {
        "target": {
            "symbol": "LDO",
            "timeframe": "1H"
        },
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"}
        ]
    }
