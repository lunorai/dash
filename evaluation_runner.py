import os
import sys
import pandas as pd
import numpy as np
import importlib.util
from data_fetcher import fetch_target_data
from simulator import TradeSimulator

def run_strategy_evaluation(strategy_name: str) -> dict:
    """
    Simple evaluation function that matches your actual setup:
    1. Loads strategy from strategies folder
    2. Gets metadata using get_coin_metadata() 
    3. Loads anchor data from candles_anchor_all.parquet
    4. Fetches target data using simple_data_fetcher
    5. Runs generate_signals() with proper parameters
    6. Simulates trades using TradeSimulator
    
    Args:
        strategy_name: name of the strategy file (without .py extension)
    
    Returns:
        dict with basic results and trading performance metrics
    """
    
    try:
        # Step 1: Load strategy from strategies folder
        print(f"Loading strategy: {strategy_name}")
        
        strategy_path = f"Strategies/{strategy_name}.py"
        if not os.path.exists(strategy_path):
            return {"error": f"Strategy file not found: {strategy_path}"}
        
        # Import the strategy module
        spec = importlib.util.spec_from_file_location("strategy", strategy_path)
        strategy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(strategy_module)
        
        # Step 2: Get metadata using get_coin_metadata (not get_metadata)
        print("Getting strategy metadata...")
        metadata = strategy_module.get_coin_metadata()
        print(f"Metadata: {metadata}")
        
        # Step 3: Load anchor data from parquet file
        print("Loading anchor data from candles_anchor_all.parquet...")
        anchor_file = "candle_data/candles_anchor_all.parquet"
        if not os.path.exists(anchor_file):
            return {"error": f"Anchor data file not found: {anchor_file}"}
        
        candles_anchor = pd.read_parquet(anchor_file)
        print(f"Loaded {len(candles_anchor)} rows of anchor data")
        
        # Step 4: Get target data using simple_data_fetcher
        print("Fetching target data...")
        target = metadata.get("target", {})
        target_symbol = target.get("symbol")
        target_timeframe = target.get("timeframe", "1h").lower()
        
        if not target_symbol:
            return {"error": "No target symbol in metadata"}
        
        candles_target = fetch_target_data(target_symbol, target_timeframe)
        print(f"Loaded {len(candles_target)} rows of target data for {target_symbol}")
        
        # Step 5: Run generate_signals with proper parameters (candles_target, candles_anchor)
        print("Generating signals...")
        signals_df = strategy_module.generate_signals(candles_target, candles_anchor)
        print(f"Generated {len(signals_df)} signal rows")

        # Step 6: Simulate trades using TradeSimulator
        print("Simulating trades...")
        simulator = TradeSimulator(initial_capital=1000.0, fee_pct=0.001)
        tradelog = simulator.run(candles_target, signals_df)
        print(f"Trade log columns: {tradelog.columns.tolist()}")
        print(f"First few trades:\n{tradelog.head()}")
        print(f"Total trades: {len(tradelog)}")

        # Step 7: Calculate Profit Results
        initial_capital = 1000.0
        final_capital = tradelog["capital"].iloc[-1] if not tradelog.empty else initial_capital
        print(f"Final capital: {final_capital}")

        total_return = (final_capital - initial_capital) / initial_capital
        return_percentage = total_return * 100
        print(f"Total return: {return_percentage:.2f}%")

        # Step 8: Calculate Maximum Drawdown
        peak_capital = tradelog["capital"].cummax()
        drawdown_series = tradelog["capital"] / peak_capital - 1
        max_drawdown = drawdown_series.min()
        max_drawdown_percentage = abs(max_drawdown * 100)
        print(f"Max drawdown: {max_drawdown_percentage:.2f}%")

        # Step 9: Calculate Sharpe Ratio
        daily_returns = tradelog["PnL"].values
        avg_return = np.mean(daily_returns)
        return_std = np.std(daily_returns)
        risk_free_rate = 0.0

        sharpe_ratio = 0.0
        if return_std > 0:
            sharpe_ratio = (avg_return - risk_free_rate) / return_std
        print(f"Sharpe ratio: {sharpe_ratio:.2f}")

        # Calculate additional metrics
        winning_trades = tradelog[tradelog['PnL'] > 0]
        losing_trades = tradelog[tradelog['PnL'] < 0]
        
        total_trades = len(tradelog)  # Each row in tradelog represents a completed trade
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_win = winning_trades['PnL'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['PnL'].mean() if not losing_trades.empty else 0
        
        # Fixed profit factor calculation
        if not losing_trades.empty and losing_trades['PnL'].sum() != 0:
            profit_factor = abs(winning_trades['PnL'].sum() / losing_trades['PnL'].sum())
        else:
            profit_factor = float('inf')  # Perfect profit factor when no losses

        # Calculate drawdown periods
        peak = tradelog['capital'].expanding().max()
        drawdown = (tradelog['capital'] - peak) / peak
        drawdown_periods = (drawdown < 0).astype(int)
        drawdown_periods = drawdown_periods.groupby((drawdown_periods != drawdown_periods.shift()).cumsum()).cumsum()
        
        # Calculate drawdown statistics
        if len(drawdown_periods[drawdown_periods > 0]) > 0:
            avg_drawdown_duration = drawdown_periods[drawdown_periods > 0].mean()
            max_drawdown_duration = drawdown_periods[drawdown_periods > 0].max()
            drawdown_count = len(drawdown_periods[drawdown_periods > 0].unique())
        else:
            avg_drawdown_duration = 0
            max_drawdown_duration = 0
            drawdown_count = 0

        # Calculate additional meaningful metrics
        if total_trades > 0:
            avg_trade_duration = (tradelog['timestamp'].iloc[-1] - tradelog['timestamp'].iloc[0]).total_seconds() / (3600 * total_trades)  # in hours
            trades_per_day = total_trades / ((tradelog['timestamp'].iloc[-1] - tradelog['timestamp'].iloc[0]).total_seconds() / (3600 * 24))
        else:
            avg_trade_duration = 0
            trades_per_day = 0

        # Calculate risk-adjusted metrics
        if return_std > 0:
            sortino_ratio = (avg_return - risk_free_rate) / return_std
            calmar_ratio = total_return / max_drawdown_percentage if max_drawdown_percentage > 0 else float('inf')
        else:
            sortino_ratio = float('inf')
            calmar_ratio = float('inf')

        # Return comprehensive results with improved metrics
        results = {
            "strategy_name": strategy_name,
            "status": "completed",
            "target_symbol": target_symbol,
            "return_percentage": return_percentage,
            "max_drawdown_percentage": max_drawdown_percentage,
            "sharpe_ratio": sharpe_ratio,
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "avg_return": avg_return,
            "return_std": return_std,
            "tradelog": tradelog.to_dict(orient='records'),
            "metadata": metadata,
            # Trading statistics
            "total_trades": total_trades,
            "win_rate": win_rate * 100,  # Convert to percentage
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            # Drawdown statistics
            "avg_drawdown_duration_hours": avg_drawdown_duration,
            "max_drawdown_duration_hours": max_drawdown_duration,
            "drawdown_count": drawdown_count,
            # Trade timing statistics
            "avg_trade_duration_hours": avg_trade_duration,
            "trades_per_day": trades_per_day,
            # Risk metrics
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            # Consecutive trades
            "max_consecutive_wins": (winning_trades['PnL'] > 0).astype(int).groupby((winning_trades['PnL'] > 0).astype(int).diff().ne(0).cumsum()).cumsum().max() if not winning_trades.empty else 0,
            "max_consecutive_losses": (losing_trades['PnL'] < 0).astype(int).groupby((losing_trades['PnL'] < 0).astype(int).diff().ne(0).cumsum()).cumsum().max() if not losing_trades.empty else 0
        }

        print("\nFinal results summary:")
        print(f"Strategy: {strategy_name}")
        print(f"Total trades: {total_trades}")
        print(f"Win rate: {win_rate*100:.2f}%")
        print(f"Return: {return_percentage:.2f}%")
        print(f"Max drawdown: {max_drawdown_percentage:.2f}%")
        print(f"Sharpe ratio: {sharpe_ratio:.2f}")
        print(f"Profit factor: {profit_factor:.2f}")
        print(f"Avg trade duration: {avg_trade_duration:.1f} hours")
        print(f"Trades per day: {trades_per_day:.2f}")
        print(f"Drawdown count: {drawdown_count}")
        print(f"Avg drawdown duration: {avg_drawdown_duration:.1f} hours")
        return results
        
    except Exception as e:
        print(f"Error in evaluation: {str(e)}")
        return {
            "strategy_name": strategy_name,
            "status": "failed",
            "error": str(e)
        }