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
        logger.info(f"First few signals:\n{signals.head()}")
        logger.info(f"Last few signals:\n{signals.tail()}")
        
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

            logger.debug(f"Processing candle {i}: timestamp={timestamp}, close={close_price}, signal={signal}, position={position}")

            if signal == 'BUY' and position is None:
                # Enter long
                entry_price = close_price
                position = 'long'
                capital *= (1 - self.fee_pct)  # entry fee
                logger.info(f"Entering LONG position at price {entry_price}, capital after fee: {capital}")

            elif signal == 'SELL' and position == 'long':
                # Exit long
                exit_price = close_price
                trade_return = (exit_price - entry_price) / entry_price
                pnl = capital * trade_return

                capital += pnl
                capital *= (1 - self.fee_pct)  # exit fee

                logger.info(f"Exiting LONG position: entry={entry_price}, exit={exit_price}, return={trade_return:.4f}, PnL={pnl:.2f}, final capital={capital:.2f}")

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

        logger.info(f"After main loop - Position: {position}, Entry price: {entry_price}, Capital: {capital}")
        
        if position == 'long':
            #Do a final Sell if still Target Coin will be Held 
            last_candle = candles.iloc[-1]
            logger.info(f"Final candle data:\n{last_candle}")
            
            exit_price = last_candle['close']
            logger.info(f"Final candle close price: {exit_price}")
            
            if pd.isna(exit_price):
                logger.warning("Final candle close price is NaN, using entry price as exit price")
                exit_price = entry_price
                logger.info(f"Using entry price as exit price: {exit_price}")
            
            logger.info(f"Calculating trade return: entry={entry_price}, exit={exit_price}")
            trade_return = (exit_price - entry_price) / entry_price
            logger.info(f"Trade return: {trade_return}")
            
            pnl = capital * trade_return
            logger.info(f"PnL: {pnl}")

            capital += pnl
            capital *= (1 - self.fee_pct)  # exit fee
            logger.info(f"Final capital after fees: {capital}")

            logger.info(f"Final position close: entry={entry_price}, exit={exit_price}, return={trade_return:.4f}, PnL={pnl:.2f}, final capital={capital:.2f}")

            tradelog.append({
                'timestamp': last_candle['timestamp'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'PnL': round(trade_return, 6),   # in decimal, e.g. 0.05 = +5%
                'capital': round(capital, 2)
            })

            entry_price = None
            position = None

        logger.info(f"Simulation complete. Final capital: {capital}")
        logger.info(f"Number of trades executed: {len(tradelog)}")
        if tradelog:
            logger.info(f"Last trade in tradelog:\n{pd.DataFrame(tradelog).iloc[-1]}")
        
        if not tradelog:
            logger.warning("No trades were executed during the simulation")
        
        return pd.DataFrame(tradelog)
