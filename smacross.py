import os
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timedelta
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import gc
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# evnironemnt variables
load_dotenv()

#setup streamlit
st.set_page_config(page_title="SMA Crossover Trading Dashboard", layout="wide")
st.title("📈 SMA Crossover Strategy with Alpaca & Backtrader")

def reset_app():
    st.session_state.clear()
    st.experimental_rerun()

# sidebar
with st.sidebar:
    st.header("Strategy Parameters")
    
    if st.button("Reset App"):
        reset_app()
    
    symbol = st.selectbox("Stock Symbol", ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA"], index=0)
    timeframe = st.selectbox("Timeframe", ["Hour", "Day", "Week"], index=0)
    fast_sma = st.slider("Fast SMA Period", 1, 50, 5)
    slow_sma = st.slider("Slow SMA Period", 10, 100, 20)
    days_back = st.slider("Days of Historical Data", 1, 365, 30)
    initial_cash = st.number_input("Initial Capital ($)", 1000, 100000, 10000)
    run_backtest = st.button("Run Backtest")

# backtrader
class AlpacaDataFeed(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
    )

# smacrossover strategy
class SmaCross(bt.Strategy):
    params = (('pfast', 5), ('pslow', 20))
    
    def __init__(self):
        self.sma1 = bt.ind.SMA(period=self.p.pfast)
        self.sma2 = bt.ind.SMA(period=self.p.pslow)
        self.crossover = bt.ind.CrossOver(self.sma1, self.sma2)
        
    def next(self):
        if not hasattr(st.session_state, 'trade_log'):
            st.session_state.trade_log = []
            
        if self.crossover > 0:
            self.buy()
            st.session_state.trade_log.append(f"{self.data.datetime.date()}: BUY at {self.data.close[0]:.2f}")
        elif self.crossover < 0:
            self.sell()
            st.session_state.trade_log.append(f"{self.data.datetime.date()}: SELL at {self.data.close[0]:.2f}")

# getting data with alpaca api
@st.cache_resource(ttl=3600)
def get_alpaca_data(symbol, timeframe, days_back):
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")

    tf_mapping = {
        "Hour": TimeFrame.Hour,
        "Day": TimeFrame.Day,
        "Week": TimeFrame.Week
    }
    
    try:
        data_client = StockHistoricalDataClient(api_key, secret_key)
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf_mapping[timeframe],
            start=(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d'),
            feed='iex'
        )
        
        bars = data_client.get_stock_bars(request_params)
        df = bars.df.reset_index()  
        df['timestamp'] = pd.to_datetime(df['timestamp'])  
        df.rename(columns={'timestamp': 'datetime'}, inplace=True)
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to get data: {e}")
        return None


if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []

# backtest
if run_backtest:
    st.session_state.trade_log = []
    
    with st.spinner("Running backtest..."):
        try:
       
            cerebro = bt.Cerebro()
            cerebro.broker.set_cash(initial_cash)
            cerebro.broker.setcommission(commission=0.001)
            
            alpaca_data = get_alpaca_data(symbol, timeframe, days_back)
            if alpaca_data is not None:
                data = AlpacaDataFeed(dataname=alpaca_data)
                cerebro.adddata(data)
                
                cerebro.addstrategy(SmaCross, pfast=fast_sma, pslow=slow_sma)
                
                start_value = cerebro.broker.getvalue()
                results = cerebro.run()
                end_value = cerebro.broker.getvalue()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Starting Value", f"${start_value:,.2f}")
                with col2:
                    st.metric("Final Value", f"${end_value:,.2f}")
                
                st.metric("Return", f"{((end_value - start_value)/start_value)*100:.2f}%")
                
                st.subheader("Strategy Performance")
                
                fig = plt.figure(figsize=(12, 8))
                
                plotter = cerebro.plot(style='candlestick', fig=fig, iplot=False, barup='green', bardown='red')
                
                plt.tight_layout()
                
                st.pyplot(fig)
                
                plt.close(fig)
                
                st.subheader("Trade Signals")
                if st.session_state.trade_log:
                    for log in st.session_state.trade_log:
                        st.write(log)
                else:
                    st.write("No trades were executed")
            
            gc.collect()
            
        except Exception as e:
            st.error(f"Backtest failed: {str(e)}")

with st.expander("ℹ️ About This Strategy"):
    st.write("""
    **SMA Crossover Strategy**:
    - Buy when fast SMA crosses above slow SMA
    - Sell when fast SMA crosses below slow SMA
    
    **Key Parameters**:
    - Fast SMA: {fast_sma} periods
    - Slow SMA: {slow_sma} periods
    - Timeframe: {timeframe}
    """.format(fast_sma=fast_sma, slow_sma=slow_sma, timeframe=timeframe))