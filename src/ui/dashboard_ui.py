import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
SHARED_STATE_PATH = os.path.join(LOGS_DIR, "shared_state.json")

# ---------- CONFIG ----------
st.set_page_config(page_title="TradePilot Pro", layout="wide", page_icon="📊")

# ---------- MOBILE MODE TOGGLE ----------
mobile_mode = st.toggle(
    "Mode Mobile",
    value=False,
    key="mobile_mode_toggle",
    help="Active l'interface simplifiée pour smartphone/tablette",
)

if mobile_mode:
    st.markdown(
        """
    <style>
    .stApp, body { background: #181C20 !important; color: #fff; font-size: 1.15rem; }
    .mobile-btn { width: 100%; font-size: 1.3rem !important; padding: 1.1rem 0.5rem !important; margin: 0.6rem 0 1.1rem 0; border-radius: 1.2rem; font-weight: 700; }
    .mobile-section { background: #23272B; border-radius: 18px; box-shadow: 0 4px 18px #0003; padding: 1.2rem 1rem; margin-bottom: 1.2rem; }
    .mobile-label { font-size: 1.1rem; color: #7dd3fc; font-weight: 600; margin-bottom: 0.6rem; }
    .mobile-signal { font-size: 1.15rem; color: #fff; margin-bottom: 0.8rem; }
    .mobile-chatbox { margin-top: 1.2rem; }
    .mobile-copy-btn { margin-left: 0.7rem; font-size: 1.1rem !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Sélecteur mode
    state = {}
    import datetime
    import json
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
    SHARED_STATE_PATH = os.path.join(LOGS_DIR, "shared_state.json")

    def read_shared_state():
        try:
            with open(SHARED_STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def write_shared_state(key, value):
        state = read_shared_state()
        state[key] = value
        state["timestamp"] = datetime.datetime.now().isoformat()
        with open(SHARED_STATE_PATH, "w") as f:
            json.dump(state, f)

    state = read_shared_state()
    mode = state.get("mode", "Démo")
    mode_select = st.radio(
        "Mode",
        options=["Démo", "Live"],
        index=0 if mode == "Démo" else 1,
        horizontal=True,
    )
    if mode_select != mode:
        write_shared_state("mode", mode_select)
        st.rerun()
    # Bouton Activer/Pause bot
    bot_on = state.get("bot_on", True)
    if bot_on:
        bot_label = "⏸️ Mettre en pause le bot"
        bot_color = "#ef4444"
    else:
        bot_label = "🟢 Activer le bot"
        bot_color = "#10b981"
    if st.button(
        "{} {}".format(
            "⏸️" if bot_on else "🟢",
            "Mettre en pause le bot" if bot_on else "Activer le bot",
        ),
        key="mobile_bot_toggle",
        help="Active/désactive le bot",
        use_container_width=True,
    ):
        write_shared_state("bot_on", not bot_on)
        st.rerun()
    # Bouton Analyser maintenant
    if st.button(
        "🚀 Analyser maintenant",
        key="mobile_llm_now",
        help="Force une analyse immédiate",
        use_container_width=True,
    ):
        write_shared_state("force_llm_analysis", True)
        st.success(
            "Analyse LLM demandée ! (sera prise en compte à la prochaine itération du backend)"
        )
    # Bloc Dernier signal détecté
    last_signal = state.get("last_signal")
    st.markdown("<div class='mobile-section'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='mobile-label'>Dernier signal détecté</div>", unsafe_allow_html=True
    )
    if last_signal:
        asset = last_signal.get("symbol", "Asset inconnu")
        sizing = last_signal.get("risk_pct", "?")
        sig_txt = f"{last_signal.get('type','?')} {last_signal.get('side','?')} - {asset} {last_signal.get('timeframe','?')}<br>SL: {last_signal.get('sl','?')} | TP: {last_signal.get('tp','?')} | Sizing: {sizing}%"
        st.markdown(
            f"<div class='mobile-signal'>{sig_txt}</div>", unsafe_allow_html=True
        )
        if st.button(
            "🛒 Exécuter ce trade", key="mobile_exec_trade", use_container_width=True
        ):
            write_shared_state("execute_trade", True)
            st.success("Signal transmis pour exécution !")
    else:
        st.markdown(
            "<div class='mobile-signal' style='color:#aaa;'>Aucun signal détecté.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    # Console GPT simplifiée
    st.markdown("<div class='mobile-section mobile-chatbox'>", unsafe_allow_html=True)
    st.markdown("<div class='mobile-label'>Console GPT</div>", unsafe_allow_html=True)
    if "mobile_gpt_history" not in st.session_state:
        st.session_state["mobile_gpt_history"] = []
    gpt_q = st.text_input("Pose ta question à GPT", "", key="mobile_gpt_input")
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Envoyer à GPT", key="mobile_gpt_send") and gpt_q.strip():
            st.session_state["mobile_gpt_history"] = []
            st.session_state["mobile_gpt_lastq"] = gpt_q
            st.session_state["awaiting_gpt"] = gpt_q
            st.rerun()
    with col2:
        if st.button("🧽 Effacer historique", key="mobile_gpt_clear"):
            st.session_state["mobile_gpt_history"] = []
            st.rerun()
    # Affichage réponse
    import os

    LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
    LLM_RESPONSE_PATH = os.path.join(LOGS_DIR, "llm_response.json")
    if os.path.exists(LLM_RESPONSE_PATH):
        try:
            with open(LLM_RESPONSE_PATH, "r") as f:
                resp = json.load(f)
            if resp.get("query") and resp.get("response"):
                if (
                    "mobile_gpt_lastq" in st.session_state
                    and resp["query"] == st.session_state["mobile_gpt_lastq"]
                ):
                    if not any(
                        h["q"] == resp["query"] and h["a"] == resp["response"]
                        for h in st.session_state["mobile_gpt_history"]
                    ):
                        st.session_state["mobile_gpt_history"].append(
                            {"q": resp["query"], "a": resp["response"]}
                        )
                    st.session_state["awaiting_gpt"] = None
                    st.session_state["mobile_gpt_lastq"] = ""
        except Exception:
            pass
    if st.session_state["mobile_gpt_history"]:
        item = st.session_state["mobile_gpt_history"][-1]
        st.markdown(
            f"<div style='margin-bottom:0.6rem;'><b>Q :</b> {item['q']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='margin-bottom:0.6rem;'><b>Réponse GPT :</b></div>",
            unsafe_allow_html=True,
        )
        st.markdown(item["a"], unsafe_allow_html=False)
        st.button(
            "📋 Copier la réponse",
            key="mobile_gpt_copy",
            on_click=lambda: st.session_state.update({"copied_gpt": item["a"]}),
            help="Copier la réponse dans le presse-papier",
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------- CSS CUSTOM ----------
st.markdown(
    """
<style>
body, .stApp { background: #f7f9fa !important; color: #222 !important; }
.card-kpi {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px #0001;
  border: 1px solid #e3e8ee;
  padding: 1.3rem 1rem;
  margin-bottom: 1rem;
  text-align: center;
}
.card-kpi .big {
  font-size: 2.2rem;
  font-weight: bold;
  color: #2e86de;
}
.card-kpi .label {
  color: #6b7a90;
  font-size: .97rem;
  margin-top: 0.3rem;
}
.card-section {
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 2px 12px #0001;
  border: 1px solid #e3e8ee;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.tag {
  display: inline-block;
  background: #e6f0fa;
  border-radius: 999px;
  padding: .2rem .9rem;
  margin: .2rem .3rem .2rem 0;
  font-size: .9rem;
  font-weight: 500;
  color: #2e86de;
}
.tag-fvg { background: #d0e6ff; color: #2563eb; }
.tag-ob { background: #d1f7e6; color: #10b981; }
.tag-bos { background: #fff4d7; color: #f59e0b; }
.tag-sweep { background: #ffe0e0; color: #ef4444; }
.status-badge {
  display: inline-block;
  border-radius: 999px;
  padding: .15rem .9rem;
  font-size: .85rem;
  font-weight: 600;
  background: #e6f0fa;
  color: #2563eb;
}
.status-simulation { background: #e0e7ff; color: #3b82f6; }
.status-demo { background: #fff4e0; color: #f59e0b; }
.status-live { background: #d1f7e6; color: #10b981; }
.switch-btn { float: right; margin-left: 1rem; }
.stButton > button {
  background: #2e86de;
  color: #fff !important;
  border-radius: 8px;
  border: none;
  padding: 0.5rem 1.2rem;
  font-weight: 600;
  box-shadow: 0 1px 4px #0001;
  transition: background 0.2s;
}
.stButton > button:hover {
  background: #2563eb;
}
.stDataFrame thead tr {
  background: #f1f5f9;
}
.stDataFrame tbody tr:nth-child(even) {
  background: #f7f9fa;
}
.stDataFrame tbody tr:nth-child(odd) {
  background: #fff;
}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
  color: #2563eb;
  font-weight: 700;
}
@media (max-width: 900px) {
  .stApp { font-size: 15px; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- HEADER ----------
colA, colB = st.columns([6, 2])
with colA:
    st.markdown(
        """
    <h1 style='margin-bottom:0;'>📊 TradePilot Pro</h1>
    <span style='color:#6b7a90;font-size:1.1rem;'>Tableau de bord IA</span>
    """,
        unsafe_allow_html=True,
    )
with colB:
    import datetime

    # Toujours utiliser le chemin logs/shared_state.json
    def read_shared_state():
        try:
            with open(SHARED_STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def write_shared_state(on_value):
        state = read_shared_state()
        state["bot_on"] = on_value
        state["timestamp"] = datetime.datetime.now().isoformat()
        with open(SHARED_STATE_PATH, "w") as f:
            json.dump(state, f)

    # Lecture de l'état réel à chaque affichage du toggle
    state = read_shared_state()
    bot_on = state.get("bot_on", True)
    new_bot_on = st.toggle(
        "Bot IA", value=bot_on, key="bot_on", help="Active/désactive le bot et le LLM"
    )
    if new_bot_on != bot_on:
        write_shared_state(new_bot_on)
        st.rerun()

    # --- Bouton Analyser maintenant ---
    force_llm = st.button(
        "Analyser maintenant 🚀", help="Force une analyse immédiate par le LLM (GPT-4)"
    )
    if force_llm:
        state = read_shared_state()
        state["force_llm_analysis"] = True
        with open("shared_state.json", "w") as f:
            json.dump(state, f)
        st.success(
            "Analyse LLM demandée ! (sera prise en compte à la prochaine itération du backend)"
        )

    # --- Affichage de l'heure du dernier appel LLM ---
    state = read_shared_state()
    last_llm = state.get("last_llm_analysis")
    if last_llm:
        try:
            last_llm_dt = datetime.datetime.fromisoformat(last_llm)
            last_llm_str = last_llm_dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            last_llm_str = last_llm
        st.markdown(
            f"<span style='color:#7dd3fc;font-size:0.97rem;'>Dernière analyse LLM : <b>{last_llm_str}</b></span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span style='color:#7dd3fc;font-size:0.97rem;'>Dernière analyse LLM : <b>Jamais</b></span>",
            unsafe_allow_html=True,
        )

    status_class = "status-live" if bot_on else "status-demo"
    status_label = "ACTIF" if bot_on else "INACTIF"
    st.markdown(
        f"<span class='status-badge {status_class}'>{status_label}</span>",
        unsafe_allow_html=True,
    )

# ---------- BACKEND STATUS INDICATOR ----------
import datetime
import json

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
CONFIG_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../config"))

SHARED_STATE_PATH = os.path.join(LOGS_DIR, "shared_state.json")


def read_shared_state():
    try:
        with open(SHARED_STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


state = read_shared_state()
last_update = state.get("timestamp")
bot_mode = state.get("mode", "Simulation")

status_color = "🟢"
status_label_backend = "En ligne"
if last_update:
    try:
        last_dt = datetime.datetime.fromisoformat(last_update)
        delta = (datetime.datetime.now() - last_dt).total_seconds()
        if delta > 120:
            status_color = "🔴"
            status_label_backend = "Bot hors ligne"
        elif delta > 30:
            status_color = "🟠"
            status_label_backend = "En veille"
    except Exception:
        status_color = "⚪️"
        status_label_backend = "Statut inconnu"
else:
    status_color = "⚪️"
    status_label_backend = "Statut inconnu"

st.markdown(
    f"""
<div style='margin-bottom:0.5rem;'>
    <b>Status backend :</b> {status_color} <span style='font-weight:600;'>{status_label_backend}</span>
    <span style='color:#888;font-size:0.95rem;'>(dernière mise à jour : {last_update if last_update else 'inconnue'})</span>
</div>
""",
    unsafe_allow_html=True,
)


# ---------- KPI GRID ----------
# ----------- KPIs dynamiques à partir du CSV -----------
capital_initial = 10000
trade_history_path = os.path.join(LOGS_DIR, "trade_history.csv")

# --- Affichage du capital réel IBKR demo ---
ibkr_capital = "N/A"
try:
    from src.bot.ibkr_connector import IBKRConnector

    ibkr_connector = IBKRConnector()
    ib = ibkr_connector.connect()
    account_values = ib.accountSummary()
    for row in account_values:
        if row.tag == "NetLiquidation":
            ibkr_capital = f"{float(row.value):,.2f} €".replace(",", " ")
            break
    ib.disconnect()
except Exception:
    ibkr_capital = "N/A"

st.markdown(
    f"<div style='font-size:1.2rem; margin-bottom:0.3em;'><b>Capital IBKR démo :</b> <span style='color:#10b981;font-weight:700'>{ibkr_capital}</span></div>",
    unsafe_allow_html=True,
)

# --- Résumé compte IBKR (sous les KPI) ---
account_summary = None
try:
    import json

    SHARED_STATE_PATH = os.path.join(LOGS_DIR, "shared_state.json")
    if os.path.exists(SHARED_STATE_PATH):
        with open(SHARED_STATE_PATH, "r") as f:
            shared = json.load(f)
            account_summary = shared.get("account_summary")
except Exception:
    account_summary = None

if account_summary:
    st.markdown(
        """
    <div class='card-section' style='margin-bottom:1.2rem;'>
      <b>Résumé compte IBKR</b><br>
      <ul style='list-style:none;padding:0;margin:0;'>
        <li>💰 <b>Capital total :</b> {netliq} €</li>
        <li>💵 <b>Cash dispo :</b> {cash} €</li>
        <li>🔋 <b>Buying Power :</b> {bp} €</li>
        <li>📈 <b>PnL non réalisé :</b> {upnl} €</li>
        <li>📊 <b>PnL réalisé :</b> {rpnl} €</li>
        <li>⚠️ <b>Drawdown :</b> {dd} %</li>
      </ul>
    </div>
    """.format(
            netliq=(
                f"{account_summary.get('NetLiquidation', 'N/A'):,}"
                if account_summary.get("NetLiquidation") is not None
                else "N/A"
            ),
            cash=(
                f"{account_summary.get('TotalCashValue', 'N/A'):,}"
                if account_summary.get("TotalCashValue") is not None
                else "N/A"
            ),
            bp=(
                f"{account_summary.get('BuyingPower', 'N/A'):,}"
                if account_summary.get("BuyingPower") is not None
                else "N/A"
            ),
            upnl=(
                f"{account_summary.get('UnrealizedPnL', 'N/A'):,}"
                if account_summary.get("UnrealizedPnL") is not None
                else "N/A"
            ),
            rpnl=(
                f"{account_summary.get('RealizedPnL', 'N/A'):,}"
                if account_summary.get("RealizedPnL") is not None
                else "N/A"
            ),
            dd=(
                f"{account_summary.get('Drawdown', 'N/A')}"
                if account_summary.get("Drawdown") is not None
                else "N/A"
            ),
        ),
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='card-section' style='margin-bottom:1.2rem;'><b>Résumé compte IBKR</b><br><span style='color:#888'>Données indisponibles</span></div>",
        unsafe_allow_html=True,
    )

# --- Historique du compte IBKR (graphique interactif) ---
from datetime import datetime

st.markdown(
    "<div style='margin-top:1em;'><b>📈 Historique du compte IBKR</b></div>",
    unsafe_allow_html=True,
)
ACC_HIST_PATH = os.path.join(LOGS_DIR, "account_history.json")
if os.path.exists(ACC_HIST_PATH):
    try:
        with open(ACC_HIST_PATH, "r") as f:
            acc_hist = json.load(f)
        if acc_hist and isinstance(acc_hist, list):
            dates = [
                datetime.fromisoformat(e.get("timestamp")[:19])
                for e in acc_hist
                if e.get("timestamp")
            ]
            capitals = [float(e.get("NetLiquidation", 0) or 0) for e in acc_hist]
            drawdowns = [float(e.get("Drawdown", 0) or 0) for e in acc_hist]
            upnl = [float(e.get("UnrealizedPnL", 0) or 0) for e in acc_hist]
            rpnl = [float(e.get("RealizedPnL", 0) or 0) for e in acc_hist]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=capitals,
                    mode="lines+markers",
                    name="Capital",
                    line=dict(color="#10b981"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=drawdowns,
                    mode="lines+markers",
                    name="Drawdown (%)",
                    yaxis="y2",
                    line=dict(color="#f59e42"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=upnl,
                    mode="lines",
                    name="PnL non réalisé",
                    line=dict(color="#6366f1", dash="dot"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=rpnl,
                    mode="lines",
                    name="PnL réalisé",
                    line=dict(color="#a21caf", dash="dash"),
                )
            )
            fig.update_layout(
                title="Évolution du compte (capital, drawdown, PnL)",
                xaxis_title="Date/Heure",
                yaxis=dict(title="Capital (€)", side="left"),
                yaxis2=dict(
                    title="Drawdown (%)", overlaying="y", side="right", showgrid=False
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                margin=dict(l=40, r=40, t=40, b=40),
                template="plotly_white",
            )
            fig.update_traces(marker=dict(size=6), selector=dict(mode="lines+markers"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée historique de compte disponible.")
    except Exception as e:
        st.warning(f"Erreur lors du chargement de l'historique compte : {e}")
else:
    st.info("Aucun historique de compte trouvé (logs/account_history.json).")

if os.path.exists(trade_history_path):
    try:
        df_trades = pd.read_csv(trade_history_path)
        # On ne prend en compte que les trades clôturés
        df_closed = df_trades[df_trades["status"].isin(["gagné", "perdu"])].copy()
        # Nettoyage PnL
        df_closed["pnl"] = pd.to_numeric(df_closed["pnl"], errors="coerce").fillna(0)
        # Profit net
        profit_net = df_closed["pnl"].sum()
        # Total gains
        total_gains = df_closed[df_closed["pnl"] > 0]["pnl"].sum()
        # Total pertes
        total_pertes = df_closed[df_closed["pnl"] < 0]["pnl"].sum()
        # Win/Loss
        nb_gagnants = (df_closed["pnl"] > 0).sum()
        nb_perdants = (df_closed["pnl"] <= 0).sum()
        nb_trades = len(df_closed)
        winrate = f"{round(100*nb_gagnants/nb_trades,1)} %" if nb_trades > 0 else "0 %"
        # Drawdown max (calcul sur l'évolution du capital)
        equity_curve = [capital_initial]
        for pnl in df_closed["pnl"]:
            equity_curve.append(equity_curve[-1] + pnl)
        drawdowns = [0]
        peak = capital_initial
        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(dd)
        drawdown_max = f"{round(max(drawdowns),2)} %" if drawdowns else "N/A"
        # Capital actuel
        capital_actuel = capital_initial + profit_net
        # Formatages
        profit_net_str = (
            f"{profit_net:,.0f} €".replace(",", " ") if nb_trades > 0 else "0 €"
        )
        total_gains_str = (
            f"{total_gains:,.0f} €".replace(",", " ") if nb_trades > 0 else "0 €"
        )
        total_pertes_str = (
            f"{total_pertes:,.0f} €".replace(",", " ") if nb_trades > 0 else "0 €"
        )
        capital_actuel_str = (
            f"{capital_actuel:,.0f} €".replace(",", " ")
            if nb_trades > 0
            else f"{capital_initial:,.0f} €".replace(",", " ")
        )
        nb_gagnants_str = str(nb_gagnants) if nb_trades > 0 else "0"
        nb_perdants_str = str(nb_perdants) if nb_trades > 0 else "0"
    except Exception:
        profit_net_str = total_gains_str = total_pertes_str = capital_actuel_str = (
            winrate
        ) = drawdown_max = nb_gagnants_str = nb_perdants_str = "N/A"
else:
    profit_net_str = total_gains_str = total_pertes_str = capital_actuel_str = (
        winrate
    ) = drawdown_max = nb_gagnants_str = nb_perdants_str = "0 €"
    capital_actuel_str = f"{capital_initial:,.0f} €".replace(",", " ")

kpi_cols = st.columns(4)
kpis = [
    ("Capital actuel", capital_actuel_str, "💰"),
    ("Profit net", profit_net_str, "📈"),
    ("Total gains", total_gains_str, "🟢"),
    ("Total pertes", total_pertes_str, "🔴"),
]
for i, (label, value, icon) in enumerate(kpis):
    with kpi_cols[i]:
        st.markdown(
            f"<div class='card-kpi'><div class='big'>{icon} {value}</div><div class='label'>{label}</div></div>",
            unsafe_allow_html=True,
        )

kpi_cols2 = st.columns(4)
kpis2 = [
    ("Win/Loss", winrate, "🥧"),
    ("Drawdown max", drawdown_max, "📉"),
    ("Trades gagnants", nb_gagnants_str, "✅"),
    ("Trades perdants", nb_perdants_str, "❌"),
]
for i, (label, value, icon) in enumerate(kpis2):
    with kpi_cols2[i]:
        st.markdown(
            f"<div class='card-kpi'><div class='big'>{icon} {value}</div><div class='label'>{label}</div></div>",
            unsafe_allow_html=True,
        )


# ----------- AFFICHAGE HISTORIQUE TRADES -----------
import pandas as pd

trade_history_path = os.path.join(LOGS_DIR, "trade_history.csv")
if os.path.exists(trade_history_path):
    try:
        trade_history_df = pd.read_csv(trade_history_path)
        st.markdown(
            "<div class='card-section' style='margin-top:2.2rem;'><b>Historique des trades</b></div>",
            unsafe_allow_html=True,
        )
        # ----------- FILTRES DYNAMIQUES -----------
        filt_col1, filt_col2, filt_col3, filt_col4, filt_col5 = st.columns(
            [1.4, 1.1, 1.1, 1.1, 1.3]
        )
        with filt_col1:
            asset_filter = st.multiselect(
                "Asset",
                options=sorted(trade_history_df["asset"].dropna().unique()),
                default=sorted(trade_history_df["asset"].dropna().unique()),
            )
        with filt_col2:
            type_filter = st.multiselect(
                "Type",
                options=sorted(trade_history_df["type"].dropna().unique()),
                default=sorted(trade_history_df["type"].dropna().unique()),
            )
        with filt_col3:
            strategy_filter = st.multiselect(
                "Stratégie",
                options=sorted(trade_history_df["strategy"].dropna().unique()),
                default=sorted(trade_history_df["strategy"].dropna().unique()),
            )
        with filt_col4:
            status_filter = st.multiselect(
                "Statut",
                options=sorted(trade_history_df["status"].dropna().unique()),
                default=sorted(trade_history_df["status"].dropna().unique()),
            )
        with filt_col5:
            # Période sur la date d'entrée (timestamp_entry)
            min_date = pd.to_datetime(
                trade_history_df["timestamp_entry"], errors="coerce"
            ).min()
            max_date = pd.to_datetime(
                trade_history_df["timestamp_entry"], errors="coerce"
            ).max()
            date_range = st.date_input(
                "Période entrée",
                value=(
                    min_date.date() if not pd.isnull(min_date) else None,
                    max_date.date() if not pd.isnull(max_date) else None,
                ),
                min_value=min_date.date() if not pd.isnull(min_date) else None,
                max_value=max_date.date() if not pd.isnull(max_date) else None,
            )
        # Application des filtres
        df_filtered = trade_history_df.copy()
        if asset_filter:
            df_filtered = df_filtered[df_filtered["asset"].isin(asset_filter)]
        if type_filter:
            df_filtered = df_filtered[df_filtered["type"].isin(type_filter)]
        if strategy_filter:
            df_filtered = df_filtered[df_filtered["strategy"].isin(strategy_filter)]
        if status_filter:
            df_filtered = df_filtered[df_filtered["status"].isin(status_filter)]
        if date_range and len(date_range) == 2:
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            df_filtered = df_filtered[
                (
                    pd.to_datetime(df_filtered["timestamp_entry"], errors="coerce")
                    >= start
                )
                & (
                    pd.to_datetime(df_filtered["timestamp_entry"], errors="coerce")
                    <= end
                )
            ]
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        csv_export = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📤 Exporter en CSV",
            data=csv_export,
            file_name="trade_history.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.warning(f"Erreur lors du chargement de l'historique des trades : {e}")
else:
    st.info("Aucun trade enregistré pour le moment.")

st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)

# ---------- GRAPHIQUES ----------
graph_cols = st.columns([2, 1, 1])
with graph_cols[0]:
    st.markdown(
        "<div class='card-section'><b>Évolution du Profit (PnL)</b>",
        unsafe_allow_html=True,
    )
    # Placeholder PnL
    dates = pd.date_range("2025-05-01", periods=18)
    pnl = [
        2800,
        2950,
        3100,
        3050,
        2900,
        3000,
        3150,
        3200,
        3100,
        3050,
        3200,
        3300,
        3350,
        3400,
        3350,
        3400,
        3430,
        3452,
    ]
    fig = px.line(x=dates, y=pnl, labels={"x": "Date", "y": "PnL (€)"})
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor="#23272B",
        paper_bgcolor="#23272B",
        font_color="#fff",
    )
    fig.update_traces(line_color="#2eccc6")
    st.plotly_chart(fig, use_container_width=True)
with graph_cols[1]:
    st.markdown(
        "<div class='card-section'><b>Répartition Trades</b>", unsafe_allow_html=True
    )
    # Placeholder Pie
    fig = go.Figure(
        go.Pie(
            values=[67, 33],
            labels=["Gagnants", "Perdants"],
            hole=0.7,
            marker_colors=["#2eccc6", "#ff4b4b"],
            textinfo="none",
        )
    )
    fig.update_layout(
        showlegend=True,
        height=180,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="#23272B",
        font_color="#fff",
        legend=dict(orientation="h", y=-0.1),
    )
    fig.update_traces(textfont_size=14)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with graph_cols[2]:
    st.markdown("<div class='card-section'><b>Drawdown max</b>", unsafe_allow_html=True)
    # Placeholder Drawdown
    fig = px.area(
        x=dates,
        y=[
            0,
            1,
            2,
            2,
            3.4,
            2.5,
            2.1,
            2.3,
            2.8,
            3.4,
            3.2,
            2.9,
            2.2,
            2.1,
            2.0,
            1.8,
            1.7,
            1.5,
        ],
        labels={"x": "Date", "y": "Drawdown %"},
    )
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor="#23272B",
        paper_bgcolor="#23272B",
        font_color="#fff",
    )
    fig.update_traces(line_color="#ff4b4b", fillcolor="rgba(255,75,75,0.2)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- CONTEXTE MACRO ----------
st.markdown(
    "<div class='card-section' style='min-height:160px; max-height:210px; overflow-y:auto;'><b>Synthèse Macroéconomique</b><br>\
<ul><li>Les ventes au détail aux États-Unis attendues mercredi pourraient indiquer un ralentissement de la consommation, affectant potentiellement l'USD.</li><li>La décision de taux de la BCE prévue jeudi est susceptible de créer des mouvements pour l'EUR.</li></ul><br><b>Résumé :</b> Approche risk-off recommandée en raison des incertitudes économiques.<br><br><button style='background:#2eccc6;color:#181C20;border:none;padding:0.3rem 1.1rem;border-radius:7px;font-weight:600;margin-top:0.7rem;'>Voir plus</button></div>",
    unsafe_allow_html=True,
)

# ---------- CONSOLE GPT (LLM) ----------
st.markdown(
    "<div class='card-section' style='margin-top:1.2rem;'><b>Console GPT 🤖</b><br><span style='font-size:0.97rem;color:#b8b8b8;'>Posez une question sur le marché, la stratégie ou le contexte trading. La réponse s'affichera ici.</span></div>",
    unsafe_allow_html=True,
)

import time

LLM_QUERY_PATH = os.path.join(LOGS_DIR, "llm_query.json")
LLM_RESPONSE_PATH = os.path.join(LOGS_DIR, "llm_response.json")

# Historique en session (non persistant)
if "gpt_history" not in st.session_state:
    st.session_state["gpt_history"] = []

# Effacer l'historique
col_hist, col_clear = st.columns([7, 1])
with col_clear:
    if st.button("🗑️ Effacer l'historique", key="clear_gpt_hist"):
        st.session_state["gpt_history"] = []
        st.rerun()

# Formulaire question
with st.form(key="gpt_console_form"):
    user_query = st.text_input(
        "Votre question à GPT",
        "",
        placeholder="Ex : Quelle est la tendance EURUSD aujourd'hui ?",
    )
    submit_gpt = st.form_submit_button("Envoyer à GPT")

# Gestion de l'envoi
if submit_gpt and user_query.strip():
    # Charger le contexte de marché actuel
    try:
        state = read_shared_state()
        context = {
            "macro": state.get("macro_context"),
            "structures": state.get("structures_detected"),
            "pnl": state.get("pnl_summary"),
        }
    except Exception:
        context = {}
    # Écrire la question dans llm_query.json
    with open(LLM_QUERY_PATH, "w") as f:
        json.dump(
            {
                "query": user_query,
                "timestamp": datetime.now().isoformat(),
                "context": context,
            },
            f,
            indent=2,
        )
    st.session_state["awaiting_gpt"] = user_query
    st.info(
        "Votre question a été transmise à GPT. La réponse s'affichera ci-dessous dès qu'elle sera disponible."
    )

# Affichage spinner si attente
if st.session_state.get("awaiting_gpt"):
    with st.spinner("En attente de la réponse de GPT..."):
        time.sleep(0.7)

# Affichage de la réponse GPT si disponible
response_displayed = False
if os.path.exists(LLM_RESPONSE_PATH):
    try:
        with open(LLM_RESPONSE_PATH, "r") as f:
            resp = json.load(f)
        if resp.get("query") and resp.get("response"):
            afficher = False
            # Si la réponse correspond à la question en attente, on l'affiche et on l'ajoute à l'historique
            if st.session_state.get("awaiting_gpt") == resp["query"]:
                afficher = True
                st.session_state["awaiting_gpt"] = None
            # Fallback : si aucune question en attente mais réponse disponible, on affiche aussi
            elif not st.session_state.get("awaiting_gpt"):
                afficher = True
            # Ajoute à l'historique si pas déjà présent
            if afficher:
                if not any(
                    h["q"] == resp["query"] and h["a"] == resp["response"]
                    for h in st.session_state["gpt_history"]
                ):
                    st.session_state["gpt_history"].append(
                        {"q": resp["query"], "a": resp["response"]}
                    )
                st.markdown(
                    "<div class='card-section' style='background:#20232a;margin-top:0.6rem;'><b>Réponse GPT :</b></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(resp["response"], unsafe_allow_html=False)
                st.button(
                    "📋 Copier la réponse",
                    key="copy_gpt_last",
                    on_click=lambda: st.session_state.update(
                        {"copied_gpt": resp["response"]}
                    ),
                )
                response_displayed = True
    except Exception as e:
        st.warning(f"Erreur lors de la lecture de la réponse GPT : {e}")

# Affichage de l'historique (questions/réponses)
if st.session_state["gpt_history"]:
    st.markdown(
        "<div class='card-section' style='background:#23272B;margin-top:0.7rem;'><b>Historique Console GPT</b></div>",
        unsafe_allow_html=True,
    )
    for i, item in enumerate(reversed(st.session_state["gpt_history"])):
        st.markdown(f"<b>Q :</b> {item['q']}", unsafe_allow_html=True)
        st.markdown("<b>Réponse GPT :</b>", unsafe_allow_html=True)
        st.markdown(item["a"], unsafe_allow_html=False)
        st.button(
            "📋 Copier",
            key=f"copy_gpt_hist_{i}",
            on_click=lambda txt=item["a"]: st.session_state.update({"copied_gpt": txt}),
        )
        st.markdown(
            "<hr style='border:0;border-top:1px solid #333;margin:0.5rem 0 0.7rem 0;'>",
            unsafe_allow_html=True,
        )

# ---------- ANALYSE MACRO LLM ET BIAIS ----------
try:
    # Tentative de récupération de l'analyse macro à partir du LLMBrain
    import importlib.util
    import sys

    # Vérifier si le module est déjà importé
    if "src.bot.llm_brain" in sys.modules:
        llm_brain_module = sys.modules["src.bot.llm_brain"]
    else:
        # Importer dynamiquement le module
        spec = importlib.util.spec_from_file_location(
            "llm_brain", os.path.join(BASE_DIR, "../bot/llm_brain.py")
        )
        llm_brain_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(llm_brain_module)

    # Récupérer les données macro via shared_state
    state = read_shared_state()
    last_macro_analysis = state.get(
        "last_macro_analysis", "Aucune analyse macro disponible pour le moment."
    )
    currency_biases = state.get("currency_biases", {})
    freeze_periods = state.get("freeze_periods", {})

    # Afficher l'analyse macro
    st.markdown(
        "<div class='card-section'><b>Analyse Macroéconomique LLM</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(last_macro_analysis)

    # Afficher les biais par devise
    if currency_biases:
        st.markdown(
            "<div class='card-section'><b>Biais Macro par Devise</b></div>",
            unsafe_allow_html=True,
        )

        # Créer un tableau à deux colonnes (Devise / Biais)
        bias_data = []
        for currency, bias in sorted(currency_biases.items()):
            emoji = "🔴" if bias == "bearish" else "🟢" if bias == "bullish" else "⚪"
            bias_display = f"{emoji} {bias.capitalize()}"
            bias_data.append({"Devise": currency, "Biais": bias_display})

        if bias_data:
            bias_df = pd.DataFrame(bias_data)
            st.dataframe(bias_df, hide_index=True, use_container_width=True)
        else:
            st.info("Aucun biais identifié pour le moment.")

    # Afficher les périodes de gel actives
    now = datetime.datetime.now()
    active_freeze_periods = []

    # Traiter les périodes de gel depuis shared_state
    for currency, periods in freeze_periods.items():
        for period in periods:
            try:
                start = datetime.datetime.fromisoformat(period.get("start", ""))
                end = datetime.datetime.fromisoformat(period.get("end", ""))

                # Vérifier si la période est active ou imminente (< 60 min)
                if end > now and (start - now).total_seconds() < 3600:
                    # Calculer temps restant
                    if start <= now:
                        # Période active
                        minutes_left = int((end - now).total_seconds() / 60)
                        status = f"ACTIF (fin dans {minutes_left} min)"
                        is_active = True
                    else:
                        # Période imminente
                        minutes_to_start = int((start - now).total_seconds() / 60)
                        status = f"IMMINENT (début dans {minutes_to_start} min)"
                        is_active = False

                    active_freeze_periods.append(
                        {
                            "Devise": currency,
                            "Statut": status,
                            "Début": start.strftime("%H:%M"),
                            "Fin": end.strftime("%H:%M"),
                            "Actif": is_active,
                        }
                    )
            except Exception:
                pass

    if active_freeze_periods:
        st.markdown(
            "<div class='card-section'><b>Périodes de Gel (Trading Suspendu)</b></div>",
            unsafe_allow_html=True,
        )
        freeze_df = pd.DataFrame(active_freeze_periods)

        # Appliquer un style conditionnel pour mettre en évidence les périodes actives
        def highlight_active(val):
            if val == True:
                return "background-color: rgba(255, 107, 107, 0.2)"
            return ""

        # Afficher avec le style conditionnel
        st.dataframe(
            (
                freeze_df.drop(columns=["Actif"])
                if "Actif" in freeze_df.columns
                else freeze_df
            ),
            hide_index=True,
            use_container_width=True,
        )

    # Statistiques de filtrage (si disponibles)
    if "macro_filter_stats" in state:
        filter_stats = state.get("macro_filter_stats", {})
        st.markdown(
            "<div class='card-section'><b>Statistiques de Filtrage Macro</b></div>",
            unsafe_allow_html=True,
        )
        stats_cols = st.columns(3)
        with stats_cols[0]:
            st.metric("Signaux Acceptés", filter_stats.get("accepted", 0))
        with stats_cols[1]:
            st.metric("Signaux Filtrés", filter_stats.get("filtered", 0))
        with stats_cols[2]:
            filtered_pct = 0
            total = filter_stats.get("accepted", 0) + filter_stats.get("filtered", 0)
            if total > 0:
                filtered_pct = int(filter_stats.get("filtered", 0) / total * 100)
            st.metric("% Filtrage", f"{filtered_pct}%")

except Exception as e:
    st.markdown(
        "<div class='card-section'><b>Analyse Macroéconomique LLM</b><br>Impossible de récupérer l'analyse macro. Erreur: {}</div>".format(
            e
        ),
        unsafe_allow_html=True,
    )

# ---------- STRUCTURES DETECTEES ----------
st.markdown(
    "<div class='card-section'><b>Structures Détectées</b><br>\
<span class='tag tag-fvg'>FVG</span><span class='tag tag-ob'>OB</span><span class='tag tag-bos'>BOS</span><span class='tag tag-sweep'>Sweep</span></div>",
    unsafe_allow_html=True,
)

# ---------- DERNIER SIGNAL ----------
st.markdown(
    "<div class='card-section'><b>Dernier signal détecté</b><br>\
Stratégie : <b>OB</b> | Asset : <b>EURUSD</b> | Timeframe : <b>M15</b> | SL/TP : <b>20/40 pips</b> | Sizing : <b>1%</b></div>",
    unsafe_allow_html=True,
)

# ---------- HISTORIQUE SIGNAUX ----------
st.markdown(
    "<div class='card-section' style='max-height:220px;overflow-y:auto;'><b>Historique des signaux</b><br>\
<ul style='padding-left:1.1rem;'>\
<li>[2025-05-17 10:15] OB LONG M15 EURUSD SL:20 TP:40</li>\
<li>[2025-05-16 14:50] Sweep SHORT M5 GBPUSD SL:10 TP:25</li>\
<li>[2025-05-16 09:22] BOS LONG H1 USDJPY SL:30 TP:60</li>\
<li>[2025-05-15 16:10] FVG SHORT M30 EURJPY SL:18 TP:36</li>\
<li>[2025-05-15 11:05] OB LONG M15 EURUSD SL:20 TP:40</li>\
</ul></div>",
    unsafe_allow_html=True,
)

# ---------- MESSAGE PAUSE EN HAUT ----------
if not bot_on:
    st.markdown(
        """
    <div style='background:#181C20;padding:1.1rem 0 0.5rem 0;'>
        <div style='color:#fff;font-size:2.1rem;font-weight:700;margin-bottom:0.2rem;'>🛑 Bot en pause</div>
        <div style='color:#b8b8b8;font-size:1.1rem;'>L'exécution du bot et du LLM est désactivée. Vous pouvez réactiver le bot à tout moment avec le switch en haut à droite.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Appliquer une classe CSS pour griser le dashboard si le bot est en pause
if not bot_on:
    st.markdown(
        """
    <style>
    .card-kpi, .card-section, .element-container {
        opacity: 0.45 !important;
        filter: grayscale(0.7);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
