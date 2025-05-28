import streamlit as st
import pandas as pd

from evaluation_runner import run_strategy_evaluation
from strategy_config import STRATEGIES

# Initialize session state
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = []

# Page title
st.title("Strategy Evaluation Dashboard")
st.markdown("---")  # Adds a horizontal line

st.subheader("Strategy Leaderboard")

# Add table headers with wider columns
col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5, 1])
with col1:
    st.markdown("**Strategy ID**")
with col2:
    st.markdown("**Target Coin**")
with col3:
    st.markdown("**Anchor Coins**")
with col4:
    st.markdown("**Total Return**")
with col5:
    st.markdown("**Sharpe Ratio**")
with col6:
    st.markdown("**Max Drawdown**")
with col7:
    st.markdown("**Action**")

# Create table with buttons
for i, strategy in enumerate(STRATEGIES):
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1.5, 1.5, 1.5, 1.5, 1])
    
    with col1:
        st.write(f"**Strategy {strategy['id']}**")
    with col2:
        st.write(strategy['target'])
    with col3:
        st.write(strategy['anchors'])
    with col4:
        st.write(strategy['total_return'])
    with col5:
        st.write(strategy['sharpe_ratio'])
    with col6:
        st.write(strategy['max_drawdown'])
    with col7:
        if st.button("Run", key=f"btn_{i}"):
            # Clear previous results and add new result
            st.session_state.evaluation_results = []
            # Call your evaluation function with strategy ID
            result = run_strategy_evaluation(strategy['id'])
            
            # Store result
            st.session_state.evaluation_results.append({
                'strategy_name': f"Strategy {strategy['id']}",
                'result': result
            })
            st.rerun()

# Results section (appears below)
st.markdown("---")
st.subheader("Evaluation Results")

if st.session_state.evaluation_results:
    for result in st.session_state.evaluation_results:
        strategy_result = result['result']
        
        if strategy_result.get('status') == 'failed':
            st.error(f"❌ {result['strategy_name']} - Error: {strategy_result.get('error', 'Unknown error')}")
            continue
            
        # Create a container for each strategy result
        with st.container():
            st.markdown(f"### 📊 {result['strategy_name']} Results")
            
            # Key metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Total Return",
                    f"{strategy_result['return_percentage']:.2f}%",
                    delta=f"{strategy_result['return_percentage']:.2f}%"
                )
            with col2:
                st.metric(
                    "Max Drawdown",
                    f"{strategy_result['max_drawdown_percentage']:.2f}%",
                    delta=f"-{strategy_result['max_drawdown_percentage']:.2f}%",
                    delta_color="inverse"
                )
            with col3:
                st.metric(
                    "Sharpe Ratio",
                    f"{strategy_result['sharpe_ratio']:.2f}"
                )
            with col4:
                st.metric(
                    "Final Capital",
                    f"${strategy_result['final_capital']:.2f}",
                    delta=f"${strategy_result['final_capital'] - strategy_result['initial_capital']:.2f}"
                )
            
            # Additional metrics in expandable section
            with st.expander("📊 Detailed Performance Metrics", expanded=True):
                # Trading Statistics
                st.markdown("#### Trading Statistics")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Win Rate", f"{strategy_result['win_rate']:.2f}%")
                    st.metric("Total Trades", strategy_result['total_trades'])
                with col2:
                    st.metric("Avg Win", f"${strategy_result['avg_win']:.2f}")
                    st.metric("Avg Loss", f"${strategy_result['avg_loss']:.2f}")
                with col3:
                    st.metric("Profit Factor", "∞" if strategy_result['profit_factor'] == float('inf') else f"{strategy_result['profit_factor']:.2f}")
                    st.metric("Max Consecutive Wins", strategy_result['max_consecutive_wins'])
                with col4:
                    st.metric("Max Consecutive Losses", strategy_result['max_consecutive_losses'])
                    st.metric("Drawdown Count", strategy_result['drawdown_count'])

                # Drawdown Analysis
                st.markdown("#### Drawdown Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Max Drawdown", f"{strategy_result['max_drawdown_percentage']:.2f}%")
                    st.metric("Avg Drawdown Duration", f"{strategy_result['avg_drawdown_duration_hours']:.1f}h")
                with col2:
                    st.metric("Max Drawdown Duration", f"{strategy_result['max_drawdown_duration_hours']:.1f}h")
                    st.metric("Sharpe Ratio", f"{strategy_result['sharpe_ratio']:.2f}")
            
            # Trade log visualization
            if 'tradelog' in strategy_result:
                st.markdown("#### 📈 Trade History")
                tradelog_df = pd.DataFrame(strategy_result['tradelog'])
                print(f"Dashboard - Trade log columns: {tradelog_df.columns.tolist()}")
                print(f"Dashboard - First few trades:\n{tradelog_df.head()}")
                
                # Plot capital over time
                st.line_chart(
                    tradelog_df.set_index('timestamp')['capital'],
                    use_container_width=True
                )
                
                # Show recent trades in a table
                st.markdown("#### Trade Logs")
                if not tradelog_df.empty:
                    print(f"Dashboard - Available columns for display: {tradelog_df.columns.tolist()}")
                    display_columns = ['timestamp', 'entry_price', 'exit_price', 'PnL', 'capital']
                    missing_columns = [col for col in display_columns if col not in tradelog_df.columns]
                    if missing_columns:
                        print(f"Warning: Missing columns in tradelog: {missing_columns}")
                        # Use only available columns
                        display_columns = [col for col in display_columns if col in tradelog_df.columns]
                    
                    st.dataframe(
                        tradelog_df[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
            
            st.markdown("---")
else:
    st.info("No evaluations run yet. Click 'Run' button above to start.")
    
st.markdown("Powered by [Lunor](https://lunor.quest/)")
   
