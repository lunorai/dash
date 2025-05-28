#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np

def generate_signals(candles_target: pd.DataFrame, candles_anchor: pd.DataFrame) -> pd.DataFrame:
    """Generate trading signals using optimized parameters."""

    params = {'target': 'RSRUSDT', 'anchors': ['ETH', 'SOL'], 'lag': 1, 'stop_multiplier': 2.415132561965484, 'risk_reward_ratio': 3.8647160537540355, 'zscore_window': 24, 'zscore_threshold': 2.293588583429513, 'tail_window': 25, 'tail_quantile': 0.6590598605491346, 'SOL_threshold': 0.022688815624809604, 'ETH_threshold': 0.021392337170843177}
    
    df = candles_target.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Merge anchor data
    for symbol in params['anchors']:
        adf = candles_anchor[['timestamp', f'close_{symbol}_4H']].copy()
        adf['timestamp'] = pd.to_datetime(adf['timestamp'])
        adf = adf.set_index('timestamp')
        adf_1h = adf.resample('1H').ffill().reset_index()
        df = pd.merge(df.reset_index(), adf_1h, on='timestamp', how='left')

        df[f'{symbol}_ret'] = df[f'close_{symbol}_4H'].pct_change().shift(params['lag'])
        df[f'{symbol}_ret'] = df[f'{symbol}_ret'].ffill()
        df[f'{symbol}_ret_quantile'] = df[f'{symbol}_ret'].rolling(window=params['tail_window']).quantile(params['tail_quantile'])

    # Volatility and z-score features
    df['volatility'] = df['high'].rolling(24).std() / df['close'].rolling(24).mean()
    df['mean_price'] = df['close'].rolling(window=params['zscore_window']).mean()
    df['std_price'] = df['close'].rolling(window=params['zscore_window']).std()
    df['zscore'] = (df['close'] - df['mean_price']) / df['std_price']
    df['zscore'] = df['zscore'].ffill()

    signals = []
    in_position = False
    entry_price = None
    prev_zscore = None
    trading_fee = 0.001

    for i in range(len(df)):
        row = df.iloc[i]
        current_price = row['close']
        
        # Safely access zscore
        current_zscore = row['zscore'] if not pd.isna(row['zscore']) else 0

        if in_position:
            move_pct = (current_price - entry_price) / entry_price
            volatility = row['volatility']
            stop_level = params['stop_multiplier'] * volatility
            profit_level = stop_level * params['risk_reward_ratio']
            current_zscore = row['zscore']
            zscore_exit = (
                prev_zscore is not None and
                prev_zscore > params['zscore_threshold'] and
                current_zscore <= params['zscore_threshold']
            )
            if (move_pct < -stop_level) or (move_pct > profit_level) or zscore_exit:
                signals.append('SELL')
                in_position = False
            else:
                signals.append('HOLD')
        else:
            anchor_triggers = all(
                row[f'{a}_ret'] > params[f'{a}_threshold'] for a in params['anchors']
            )
            tail_risk = any(
                row[f'{a}_ret'] < row[f'{a}_ret_quantile'] for a in params['anchors']
            )
            if anchor_triggers and not tail_risk:
                signals.append('BUY')
                in_position = True
                entry_price = current_price
            else:
                signals.append('HOLD')
        prev_zscore = current_zscore

    df['signal'] = signals
    return df[['timestamp', 'signal']].fillna('HOLD')

def get_coin_metadata() -> dict:
    """Return metadata for the strategy."""
    return {
        "target": {"symbol": "RSR", "timeframe": "1H"},
        "anchors": [
            {"symbol": "ETH", "timeframe": "4H"},
            {"symbol": "SOL", "timeframe": "4H"}
        ]
    }
