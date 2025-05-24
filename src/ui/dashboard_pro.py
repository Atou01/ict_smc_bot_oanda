# --- SIDEBAR ---
import streamlit as st

with st.sidebar:
    st.markdown(
        """
    <div class="sidebar-glass">
      <div class="sidebar-icon selected">⏱</div>
      <div class="sidebar-icon">📈</div>
      <div class="sidebar-icon">📊</div>
      <div class="sidebar-icon">💬</div>
      <div class="sidebar-icon">⚙️</div>
      <div class="sidebar-icon">☰</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# --- READ DATA ---
def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


shared = load_json(SHARED_STATE_PATH) or {}
account = shared.get("account_summary", {})
acc_hist = load_json(ACC_HIST_PATH) or []

# --- HERO KPIs ---
st.markdown('<div class="hero-kpi-row">', unsafe_allow_html=True)
kpi_card("Capital", account.get("NetLiquidation", 0), "$", accent=True)
kpi_card("Cash", account.get("TotalCashValue", 0), "$k")
kpi_card("Drawdown", account.get("Drawdown", 0), "%", danger=True)
kpi_card("Unrealized PnL", account.get("UnrealizedPnL", 0), "$", posneg=True)
kpi_card("Buying Power", account.get("BuyingPower", 0), "$k")
st.markdown("</div>", unsafe_allow_html=True)

# --- ACCOUNT SUMMARY & CHARTS ---
st.markdown('<div class="main-row">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Account Summary</div>', unsafe_allow_html=True)
    line_chart(
        acc_hist,
        y_keys=["NetLiquidation", "TotalCashValue"],
        labels=["Capital", "Cash"],
    )
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Max Drawdown</div>', unsafe_allow_html=True)
    area_chart(acc_hist, y_key="Drawdown", color="#f43f5e")
    st.markdown("</div>", unsafe_allow_html=True)
with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-title">Trade Allocation</div>', unsafe_allow_html=True
    )
    donut_chart(acc_hist)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- MACRO + LLM INSIGHT ---
st.markdown('<div class="main-row">', unsafe_allow_html=True)
col4, col5 = st.columns([2, 1])
with col4:
    macro_card(shared)
with col5:
    st.markdown(
        '<div class="card">No trades recorded at the moment</div>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

# --- GPT CONSOLE ---
st.markdown('<div class="card gpt-console">', unsafe_allow_html=True)
user_input = st.chat_input("Ask GPT… (⌘↵ send)")
if user_input:
    st.markdown(f"<div class='gpt-user-msg'>{user_input}</div>", unsafe_allow_html=True)
    # (GPT response logic placeholder)
st.markdown("</div>", unsafe_allow_html=True)

# --- MOBILE BOTTOM BAR ---
st.markdown(
    """
<div class="bottom-bar-glass">
  <div class="fab">▶️</div>
  <div class="fab">💬</div>
  <div class="fab">☰</div>
</div>
""",
    unsafe_allow_html=True,
)
