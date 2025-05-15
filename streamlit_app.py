import streamlit as st
import pandas as pd
from ibkr_client import IbkrClient
from bias import MarketBias
from strategy import MultiSMCStrategy
from filter_news import filter_high_impact
from nlp_news import LLMAnalyzer
import plotly.graph_objects as go
import datetime
from db import SessionLocal, Signal
from sqlalchemy.exc import IntegrityError
from execution import execute_trades

# --- Mock OandaClient.get_ohlc for demo mode (no real API credentials) ---
def fake_get_ohlc(self, symbol, granularity, count):
    import pandas as pd
    times = pd.date_range('2025-01-01', periods=count, freq='H')
    return pd.DataFrame({
        'time': times,
        'open': list(range(count)),
        'high': list(range(count)),
        'low': list(range(count)),
        'close': list(range(count)),
        'volume': [100] * count
    })
# 

# --- Mock filter_high_impact for demo mode (no real scraping) ---
def fake_filter_high_impact():
    # simulate some news events
    return [
        {'time': '2025-05-11 12:00', 'event': 'Nonfarm Payrolls', 'impact': 'High'},
        {'time': '2025-05-11 14:30', 'event': 'Fed Rate Decision', 'impact': 'High'},
        {'time': '2025-05-11 17:00', 'event': 'CPI MoM', 'impact': 'Medium'},
    ]
filter_high_impact = fake_filter_high_impact

def main():
    st.title("Forex Trading Bot Dashboard")
    import yaml
    cfg = yaml.safe_load(open('config.yaml'))
    use_killzone = cfg.get('USE_KILLZONE', False)
    killzones = cfg.get('KILLZONES', [])
    # Parse killzone times
    kz_periods = []
    if use_killzone:
        for kz in killzones:
            start = datetime.datetime.strptime(kz['start'], '%H:%M').time()
            end = datetime.datetime.strptime(kz['end'], '%H:%M').time()
            kz_periods.append((start, end))

    # Live mode toggle
    import yaml
    cfg = yaml.safe_load(open('config.yaml'))
    default_live = cfg.get('LIVE', False)
    live_mode = st.sidebar.checkbox("Live Mode", value=default_live)
    if live_mode:
        st.sidebar.error(" LIVE MODE ACTIVE")
    # pass live_mode to session state
    st.session_state['live_mode'] = live_mode

    # Initialize history in session
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    # DB session
    session = SessionLocal()

    # Sidebar options
    symbols = ["EUR_USD", "GBP_USD", "USD_JPY"]
    symbol = st.sidebar.selectbox("Chart Symbol", symbols)
    htf = st.sidebar.selectbox("Bias Timeframe", ["D", "H4", "H1"], index=0)
    ltf = st.sidebar.selectbox("Signals Timeframe", ["M15", "M5", "H1"], index=1)
    lookback = st.sidebar.slider("Strategy Lookback", 5, 50, 20)
    refresh = st.sidebar.button("Refresh")
    # History symbol filter
    history_symbols = st.sidebar.multiselect("History Symbols", symbols, default=[symbol])

    # Market Bias
    st.subheader("Market Bias")
    mb = MarketBias(symbols=[symbol])
    biases = mb.get_current_bias()
    bias_val = biases[symbol]['htf'].get(htf, 'NEUTRAL')
    st.metric(label=f"Bias ({htf})", value=bias_val)

    # Price Chart with Signals
    st.subheader("Price Chart & Signals")
    client = OandaClient()
    df = client.get_ohlc(symbol, granularity=ltf, count=lookback + 100)
    df['time'] = pd.to_datetime(df['time'])
    st.write(df.head())  # TEMP: vérifier les colonnes et valeurs simulées

    fig = go.Figure(data=[
        go.Candlestick(
            x=df['time'],
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name="Price"
        )
    ])
    strat = MultiSMCStrategy(df, lookback=lookback)
    raw_signals = strat.scan()
    # Enrich signals with symbol and timestamp for execution
    current_time = df['time'].iloc[-1]
    signals = [ {**sig, 'symbol': symbol, 'time': current_time} for sig in raw_signals ]

    # Killzone filter
    if use_killzone:
        def in_kz(ts):
            t = ts.time()
            return any(s <= t <= e for (s, e) in kz_periods)
        raw_before = len(signals)
        signals = [sig for sig in signals if in_kz(sig['time'])]
        filtered = raw_before - len(signals)
        if filtered > 0:
            st.warning(f"{filtered} signal(s) outside killzone filtered.")

    def round_fx(val, sym):
        if any(x in sym for x in ['USD', 'EUR', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF']):
            ndigits = 4 if not sym.endswith('JPY') and 'JPY' not in sym else 2
        else:
            ndigits = 2
        return round(val, ndigits)

    for sig in signals:
        marker = dict(symbol='triangle-up' if sig['side']=='BUY' else 'triangle-down', size=12,
                      color='green' if sig['side']=='BUY' else 'red')
        idx = df[df['time'] == sig['time']].index
        entry_r = round_fx(sig['entry'], sig['symbol'])
        if not idx.empty:
            i = idx[0]
            fig.add_trace(
                go.Scatter(x=[sig['time']], y=[entry_r], mode='markers',
                           marker=marker, name=sig['side'])
            )
        # record in session_state
        rec = sig.copy()
        rec['time'] = sig['time']
        rec['entry'] = entry_r
        rec['stop'] = round_fx(sig['stop'], sig['symbol'])
        rec['tp'] = round_fx(sig['tp'], sig['symbol'])
        st.session_state.history.append(rec)
        # persist to SQLite
        db_sig = Signal(
            time=rec['time'], symbol=rec['symbol'], side=rec['side'], pattern=rec.get('pattern',''),
            entry=rec['entry'], stop=rec['stop'], tp=rec['tp']
        )
        try:
            session.add(db_sig)
            session.commit()
        except IntegrityError:
            session.rollback()
    st.plotly_chart(fig, use_container_width=True)
    # Execute trades when refresh is clicked
    if refresh:
        execute_trades(signals, live_override=st.session_state['live_mode'])

    # News & Sentiment
    st.subheader("High-Impact News Sentiment")
    events = filter_high_impact()
    analyzer = LLMAnalyzer()
    results = analyzer.analyze(events)
    for ev in results:
        color = {'positive':'green','negative':'red'}.get(ev['sentiment'], 'grey')
        st.markdown(
            f"<span style='color:{color}'><b>{ev['time']}</b> - {ev['event']} | Sentiment: {ev['sentiment']} ({ev['polarity']:.2f})</span>",
            unsafe_allow_html=True
        )

    # Signal History
    st.subheader("Signal History")
    if st.session_state.history:
        hist_df = pd.DataFrame(st.session_state.history)
        hist_df = hist_df[hist_df['symbol'].isin(history_symbols)]
        # Arrondi pour l'affichage
        for col in ['entry', 'stop', 'tp']:
            if col in hist_df:
                hist_df[col] = [round_fx(v, s) for v, s in zip(hist_df[col], hist_df['symbol'])]
        st.dataframe(hist_df.sort_values('time', ascending=False).reset_index(drop=True))

    # Backtest
    with st.expander("Backtest"):
        st.header("Backtest")
        # Select backtest date range
        start_date, end_date = st.date_input(
            "Select Backtest Range",
            [df['time'].min().date(), df['time'].max().date()]
        )
        if start_date and end_date and start_date <= end_date:
            # Load data for backtest
            df_bt = client.get_ohlc(symbol, granularity=ltf, count=1000)
            df_bt['time'] = pd.to_datetime(df_bt['time'])
            mask = (df_bt['time'].dt.date >= start_date) & (df_bt['time'].dt.date <= end_date)
            df_bt_sel = df_bt.loc[mask].reset_index(drop=True)
            # Rolling strategy
            bt_signals = []
            for i in range(lookback, len(df_bt_sel)):
                sub_df = df_bt_sel.iloc[:i+1]
                strat_bt = MultiSMCStrategy(sub_df, lookback=lookback)
                sigs = strat_bt.scan()
                for s in sigs:
                    rec_bt = s.copy()
                    rec_bt['time'] = sub_df['time'].iloc[-1]
                    rec_bt['symbol'] = symbol  # Ajout pour compatibilité arrondi
                    bt_signals.append(rec_bt)
            if bt_signals:
                bt_df = pd.DataFrame(bt_signals)
                # Arrondi pour l'affichage
                for col in ['entry', 'stop', 'tp']:
                    if col in bt_df:
                        bt_df[col] = [round_fx(v, s) for v, s in zip(bt_df[col], bt_df['symbol'])]
                # Compute PnL
                bt_df['pnl'] = bt_df.apply(lambda r: (r['tp'] - r['entry']) if r['side']=='BUY' else (r['entry'] - r['tp']), axis=1)
                bt_df['cum_pnl'] = bt_df['pnl'].cumsum()
                # Plot cumulative PnL
                fig2 = go.Figure()
                fig2.add_trace(
                    go.Scatter(
                        x=bt_df['time'], y=bt_df['cum_pnl'], mode='lines+markers', name='Cumulative PnL'
                    )
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.dataframe(bt_df[['time','side','entry','stop','tp','pnl','cum_pnl']])
            else:
                st.write("No signals in this period.")

    # close DB session
    session.close()

if __name__ == '__main__':
    main()
