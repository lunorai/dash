# Pairwise Strategy Dashboard

A simple dashboard to evaluate and monitor trading strategies.

## Quick Start

1. Add your strategy file in the `strategies` folder with your strategy logic

2. Add your strategy details in `strategy_config.py`:
```python
{
    "id": "unique_id",
    "target": "TARGET_TOKEN",
    "anchors": "ANCHOR_TOKENS",  # Comma-separated list
    "total_return": "return_value",
    "sharpe_ratio": "ratio_value",
    "max_drawdown": "drawdown_value"
}
```

3. Run the dashboard:
```bash
streamlit run app.py
``` 