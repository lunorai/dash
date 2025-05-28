import os
import pandas as pd
import requests
from datetime import datetime

def create_standard_time_grid():
    """Create standard 1H time grid with exactly 3073 rows"""
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 5, 9)
    
    # Create 1H intervals
    time_grid = pd.date_range(start=start_date, end=end_date, freq='1H')
    return pd.DataFrame({'timestamp': time_grid})

def fetch_target_data(symbol: str, timeframe: str = "1h") -> pd.DataFrame:
    """
    Fetch target data with pagination and ensure exactly 3073 rows
    
    Args:
        symbol: coin symbol like 'BTC', 'ETH' 
        timeframe: '1h', '4h', or '1d'
    
    Returns:
        DataFrame with exactly 3073 rows (timestamp + OHLCV)
    """
    
    cache_file = f"candle_data/{symbol.lower()}_{timeframe}.parquet"
    
    # Check if cached file exists
    if os.path.exists(cache_file):
        print(f"Loading cached data for {symbol} {timeframe}")
        df = pd.read_parquet(cache_file)
        
        # Still align to standard grid even if cached
        standard_grid = create_standard_time_grid()
        result = pd.merge(standard_grid, df, on='timestamp', how='left')
        print(f"Loaded {len(result)} rows for {symbol} (aligned to standard grid)")
        return result
    
    # If no cache, fetch from Binance with pagination
    print(f"Fetching fresh data for {symbol} {timeframe} with pagination...")
    
    start_time = int(datetime(2025, 1, 1).timestamp() * 1000)
    end_time = int((datetime(2025, 5, 9, 23, 59)).timestamp() * 1000)
    
    all_data = []
    current_start = start_time
    
    try:
        while current_start < end_time:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': f"{symbol}USDT",
                'interval': timeframe,
                'startTime': current_start,
                'endTime': end_time,
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            # Convert to DataFrame
            df_batch = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Keep only essential columns
            df_batch = df_batch[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Convert types
            df_batch['timestamp'] = pd.to_datetime(df_batch['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df_batch[col] = pd.to_numeric(df_batch[col])
            
            all_data.append(df_batch)
            
            # 🔥 FIXED PAGINATION: Use raw timestamp from API + interval
            # OLD: current_start = int((df_batch['timestamp'].max() + pd.Timedelta(hours=1)).timestamp() * 1000)
            if len(data) > 0:
                last_timestamp_ms = data[-1][0]  # Raw timestamp from API response
                if timeframe == '1h':
                    current_start = last_timestamp_ms + (60 * 60 * 1000)
                elif timeframe == '4h':
                    current_start = last_timestamp_ms + (4 * 60 * 60 * 1000)
                elif timeframe == '1d':
                    current_start = last_timestamp_ms + (24 * 60 * 60 * 1000)
            
            print(f"Fetched batch: {len(df_batch)} records, total batches: {len(all_data)}")
            
            # Break if we got less than 1000 records (last page)
            if len(data) < 1000:
                break
        
        if not all_data:
            print(f"No data fetched for {symbol}")
            return create_standard_time_grid()
        
        # Combine all batches
        df = pd.concat(all_data, ignore_index=True)
        
        # 🔥 ADDED: Remove duplicates that may occur at batch boundaries
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        print(f"Total fetched records: {len(df)}")
        
        # Create standard time grid (3073 rows)
        standard_grid = create_standard_time_grid()
        
        # Align fetched data to standard grid
        aligned_df = pd.merge(standard_grid, df, on='timestamp', how='left')
        
        # Save to cache
        aligned_df.to_parquet(cache_file, index=False)
        print(f"✅ SAVED {len(aligned_df)} rows to cache: {cache_file}")
        
        return aligned_df
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        # Return empty grid with 3073 rows
        return create_standard_time_grid()