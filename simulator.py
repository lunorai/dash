import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TradeSimulator:
    def __init__(self, 
                 initial_capital: float = 1000.0,
                 fee_pct: float = 0.001,  # 0.1% per trade (entry + exit = 0.2% total)
                 compound: bool = True):
        self.initial_capital = initial_capital
        self.fee_pct = fee_pct
        self.compound = compound

    def run(self, candles: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """
        Simulates trade execution based on signals.

        Inputs:
        - candles: DataFrame with 'timestamp' and 'close'
        - signals: DataFrame with 'timestamp' and 'signal' ('BUY', 'SELL', 'HOLD')

        Returns:
        - tradelog: DataFrame with each trade's entry, exit, PnL, and resulting capital
        """
        logger.info(f"Starting trade simulation with {len(candles)} candles and {len(signals)} signals")
        
        # Critical validations using assert
        assert 'close' in candles.columns, f"Missing 'close' column in candles. Available columns: {candles.columns.tolist()}"
        assert 'signal' in signals.columns, f"Missing 'signal' column in signals. Available columns: {signals.columns.tolist()}"
        assert len(candles) == len(signals), f"Mismatch in data length: candles={len(candles)}, signals={len(signals)}"
        
        # Additional validations with detailed error messages
        valid_signals = {'BUY', 'SELL', 'HOLD'}
        invalid_signals = set(signals['signal'].unique()) - valid_signals
        if invalid_signals:
            raise ValueError(f"Invalid signal values found: {invalid_signals}. Valid values are: {valid_signals}")

        capital = self.initial_capital
        entry_price = None
        position = None
        tradelog = []

        logger.info(f"Initial capital: {capital}")

        for i in range(len(candles)):
            timestamp = candles.iloc[i]['timestamp']
            close_price = candles.iloc[i]['close']
            signal = signals.iloc[i]['signal'].upper()

            if signal == 'BUY' and position is None:
                # Enter long
                entry_price = close_price
                position = 'long'
                capital *= (1 - self.fee_pct)  # entry fee

            elif signal == 'SELL' and position == 'long':
                # Exit long
                exit_price = close_price
                trade_return = (exit_price - entry_price) / entry_price
                pnl = capital * trade_return

                capital += pnl
                capital *= (1 - self.fee_pct)  # exit fee

                tradelog.append({
                    'timestamp': timestamp,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'PnL': round(trade_return, 6),   # in decimal, e.g. 0.05 = +5%
                    'capital': round(capital, 2)
                })

                entry_price = None
                position = None

            # HOLD or SELL while no open position → do nothing

        logger.info(f"Simulation complete. Final capital: {capital}")
        logger.info(f"Number of trades executed: {len(tradelog)}")
        
        if not tradelog:
            logger.warning("No trades were executed during the simulation")
        
        return pd.DataFrame(tradelog)
