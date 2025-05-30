import streamlit as st
import pandas as pd
from evaluation_runner import run_strategy_evaluation
from strategy_config import STRATEGIES

# Set page configuration
st.set_page_config(
    page_title="Strategy Evaluation Dashboard",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling with dark theme and improved typography
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #000000 !important;
        color: #FFFFFF;
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .stApp {
        background-color: #000000 !important;
    }
    
    .stApp > header {
        background-color: #000000 !important;
    }
    
    .stApp > footer {
        background-color: #000000 !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    .stButton>button {
        background-color: #FFD700;
        color: #000000;
        border-radius: 6px;
        padding: 0.4rem 0.8rem;
        border: none;
        transition: all 0.3s ease;
        font-weight: 800;
        font-size: 0.85rem;
        text-transform: none;
        letter-spacing: 0.5px;
        min-width: 60px;
        box-shadow: 0 2px 4px rgba(255, 215, 0, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }
    
    .stButton>button:hover {
        background-color: #FFC800;
        box-shadow: 0 4px 8px rgba(255, 215, 0, 0.3);
        transform: translateY(-2px);
    }
    
    .metric-card {
        background-color: #111111;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        border: 1px solid #222222;
    }
    
    .strategy-header {
        background-color: #111111;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid #222222;
    }
    
    .stDataFrame {
        background-color: #111111;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
    }
    
    .stDataFrame td {
        color: #FFFFFF;
        font-size: 0.9rem;
    }
    
    .stDataFrame th {
        background-color: #1A1A1A;
        color: #FFD700;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .stMetric {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 10px;
        padding: 1rem;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .stMetric label {
        color: #FFD700;
        font-weight: 500;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .stMetric div {
        color: #FFFFFF;
        font-weight: 600;
        font-size: 1.1rem;
        line-height: 1.4;
    }
    
    .stExpander {
        background-color: #111111;
        border: 1px solid #222222;
    }
    
    .stExpander > div {
        background-color: #111111;
    }
    
    .stMarkdown {
        font-family: 'Inter', sans-serif;
    }
    
    .stMarkdown p {
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #FFD700;
        margin-bottom: 1rem;
    }

    /* Custom styling for positive/negative values */
    .positive-value {
        color: #00FF00 !important;
    }
    
    .negative-value {
        color: #FF4444 !important;
    }
    
    .neutral-value {
        color: #FFFFFF !important;
    }

    /* Coin display styling */
    .coin-tag {
        display: inline-block;
        background-color: #1A1A1A;
        color: #FFD700;
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        margin: 0.1rem;
        font-size: 0.9rem;
        font-weight: 500;
        border: 1px solid #333333;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .coin-container {
        display: flex;
        flex-wrap: nowrap;
        gap: 0.3rem;
        align-items: center;
        justify-content: center;
    }

    .column-header {
        text-align: center;
        font-weight: 600;
        color: #FFD700;
        font-size: 0.95rem;
        padding-bottom: 0.5rem;
        padding-left: 0.5rem;
    }

    .column-data {
        text-align: center;
        color: #FFFFFF;
        font-size: 0.95rem;
    }

    /* Center content */
    .stContainer {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 1rem;
    }

    /* Title styling */
    .dashboard-title {
        text-align: center;
        margin-bottom: 2rem;
    }

    .dashboard-title h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFD700;
        margin: 0;
        padding: 2rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = []

# Title section
st.markdown("""
    <div style='background: linear-gradient(90deg, #111111, #1A1A1A); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; border: 1px solid #222222;'>
        <h1 style='color: #FFD700; margin: 0; font-size: 2.5rem; font-weight: 700; text-align: center;'>Strategy Evaluation Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# Strategy Leaderboard Section
st.markdown("### 📊 Strategy Leaderboard")

# Create a container for the leaderboard
with st.container():
    # Table headers with modern styling
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1, 2.5, 1.3, 1.3, 1.3, 0.8])
    headers = ["Strategy ID", "Target Coin", "Anchor Coins", "Total Return", "Sharpe Ratio", "Max Drawdown", "Action"]
    
    for col, header in zip([col1, col2, col3, col4, col5, col6, col7], headers):
        with col:
            st.markdown(f"<div class='column-header'>{header}</div>", unsafe_allow_html=True)

    # Strategy rows
    for i, strategy in enumerate(STRATEGIES):
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1, 2.5, 1.3, 1.3, 1.3, 0.8])
        
        with col1:
            st.markdown(f"<div class='column-data' style='font-weight: 500;'>{strategy['id']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='column-data'>{strategy['target']}</div>", unsafe_allow_html=True)
        with col3:
            # Format anchor coins as a single tag per coin, properly split by comma
            anchor_coins = ' '.join([f'<span class="coin-tag">{coin.strip()}</span>' for coin in strategy['anchors'].split(',')])
            st.markdown(f"<div class='coin-container column-data' style='justify-content: center;'>{anchor_coins}</div>", unsafe_allow_html=True)
        with col4:
            total_return = float(strategy['total_return'].replace('%', ''))
            value_class = 'positive-value' if total_return > 0 else 'negative-value' if total_return < 0 else 'neutral-value'
            st.markdown(f"<div class='{value_class} column-data' style='font-weight: 500;'>{strategy['total_return']}</div>", unsafe_allow_html=True)
        with col5:
            sharpe_ratio = float(strategy['sharpe_ratio'])
            value_class = 'positive-value' if sharpe_ratio > 0 else 'negative-value' if sharpe_ratio < 0 else 'neutral-value'
            st.markdown(f"<div class='{value_class} column-data'>{sharpe_ratio:.2f}</div>", unsafe_allow_html=True)
        with col6:
            max_drawdown = float(strategy['max_drawdown'].replace('%', ''))
            value_class = 'negative-value' if max_drawdown < 0 else 'neutral-value'
            st.markdown(f"<div class='{value_class} column-data' style='font-weight: 500;'>{strategy['max_drawdown']}</div>", unsafe_allow_html=True)
        with col7:
            if st.button("Run", key=f"btn_{i}"):
                st.session_state.evaluation_results = []
                try:
                    print(f"\n=== Starting Strategy Evaluation for {strategy['id']} ===")
                    st.write(f"### 🔍 Evaluating Strategy {strategy['id']}")
                    
                    result = run_strategy_evaluation(strategy['id'])
                    print(f"\n=== Strategy Result ===")
                    print(result)
                    
                    if isinstance(result, dict) and 'error' in result:
                        error_msg = f"Strategy evaluation failed: {result['error']}"
                        print(f"\n=== Error ===")
                        print(error_msg)
                        st.error(error_msg)
                        st.session_state.evaluation_results.append({
                            'strategy_name': f"Strategy {strategy['id']}",
                            'result': {'status': 'failed', 'error': result['error']}
                        })
                    else:
                        print(f"\n=== Success ===")
                        print("Strategy evaluation completed successfully")
                        st.success("Strategy evaluation completed successfully")
                        st.session_state.evaluation_results.append({
                            'strategy_name': f"Strategy {strategy['id']}",
                            'result': result
                        })
                except Exception as e:
                    error_msg = f"Error running strategy: {str(e)}"
                    print(f"\n=== Exception ===")
                    print(error_msg)
                    st.error(error_msg)
                    st.session_state.evaluation_results.append({
                        'strategy_name': f"Strategy {strategy['id']}",
                        'result': {'status': 'failed', 'error': str(e)}
                    })
                st.rerun()

# Results section
st.markdown("### 📈 Evaluation Results")

if st.session_state.evaluation_results:
    for result in st.session_state.evaluation_results:
        strategy_result = result['result']
        
        if strategy_result.get('status') == 'failed':
            st.error(f"❌ {result['strategy_name']} - Error: {strategy_result.get('error', 'Unknown error')}")
            continue
            
        # Results container with modern styling
        with st.container():
            st.markdown(f"""
                <div style='background: #111111; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #222222;'>
                    <h3 style='color: #FFD700; margin: 0; font-size: 1.5rem;'>📊 {result['strategy_name']} Results</h3>
                </div>
            """, unsafe_allow_html=True)
            
            # Key metrics in modern cards
            col1, col2, col3, col4 = st.columns(4)
            metrics = [
                ("Total Return", f"{strategy_result.get('return_percentage', 0):.2f}%", f"{strategy_result.get('return_percentage', 0):.2f}%"),
                ("Max Drawdown", f"{strategy_result.get('max_drawdown_percentage', 0):.2f}%", f"-{strategy_result.get('max_drawdown_percentage', 0):.2f}%", "inverse"),
                ("Sharpe Ratio", f"{strategy_result.get('sharpe_ratio', 0):.2f}", None),
                ("Final Capital", f"${strategy_result.get('final_capital', 0):.2f}", f"${strategy_result.get('final_capital', 0) - strategy_result.get('initial_capital', 0):.2f}")
            ]
            
            for col, (label, value, delta, *args) in zip([col1, col2, col3, col4], metrics):
                with col:
                    st.metric(label, value, delta=delta, delta_color=args[0] if args else "normal")
            
            # Detailed metrics in expandable section
            with st.expander("📊 Detailed Performance Metrics", expanded=True):
                # Trading Statistics
                st.markdown("#### Trading Statistics")
                cols = st.columns(4)
                stats = [
                    ("Win Rate", f"{strategy_result['win_rate']:.2f}%"),
                    ("Total Trades", str(strategy_result['total_trades'])),
                    ("Avg Win", f"${strategy_result['avg_win']:.2f}"),
                    ("Avg Loss", f"${strategy_result['avg_loss']:.2f}"),
                    ("Profit Factor", "∞" if strategy_result['profit_factor'] == float('inf') else f"{strategy_result['profit_factor']:.2f}"),
                    ("Max Consecutive Wins", str(strategy_result['max_consecutive_wins'])),
                    ("Max Consecutive Losses", str(strategy_result['max_consecutive_losses'])),
                    ("Drawdown Count", str(strategy_result['drawdown_count']))
                ]
                
                for col, (label, value) in zip(cols * 2, stats):
                    with col:
                        st.metric(label, value)
            
            # Trade log visualization
            if 'tradelog' in strategy_result:
                st.markdown("#### 📈 Trade History")
                tradelog_df = pd.DataFrame(strategy_result['tradelog'])
                
                # Plot capital over time with modern styling
                st.line_chart(
                    tradelog_df.set_index('timestamp')['capital'],
                    use_container_width=True
                )
                
                # Show complete trade log in a modern table
                st.markdown("#### 📊 Complete Trade Log")
                if not tradelog_df.empty:
                    display_columns = ['timestamp', 'entry_price', 'exit_price', 'PnL', 'capital']
                    display_columns = [col for col in display_columns if col in tradelog_df.columns]
                    
                    st.dataframe(
                        tradelog_df[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
            
            st.markdown("---")
else:
    st.info("👈 Select a strategy and click 'Run' to start evaluation")

# Footer
st.markdown("""
    <div style='text-align: center; padding: 2rem; color: #666;'>
        Powered by <a href='https://lunor.quest/' style='color: #FFD700; text-decoration: none; font-weight: 500;'>Lunor</a>
    </div>
""", unsafe_allow_html=True)
   
