import streamlit as st
import plotly.graph_objects as go
from datetime import datetime


def kpi_card(label, value, unit="", accent=False, danger=False, posneg=False):
    style = "accent" if accent else "danger" if danger else ""
    sign = "+" if posneg and value and float(value) > 0 else ""
    v = f"{sign}{float(value):,.1f}" if value is not None else "N/A"
    st.markdown(
        f"""
    <div class='kpi-card {style}'>
      <div class='kpi-label'>{label}</div>
      <div class='kpi-value'>{v} <span class='kpi-unit'>{unit}</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def line_chart(data, y_keys, labels):
    if not data:
        return
    dates = [
        datetime.fromisoformat(e.get("timestamp")[:19])
        for e in data
        if e.get("timestamp")
    ]
    fig = go.Figure()
    for yk, lab in zip(y_keys, labels):
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[float(e.get(yk, 0) or 0) for e in data],
                mode="lines+markers",
                name=lab,
            )
        )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_dark",
        height=120,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def area_chart(data, y_key, color="#f43f5e"):
    if not data:
        return
    dates = [
        datetime.fromisoformat(e.get("timestamp")[:19])
        for e in data
        if e.get("timestamp")
    ]
    y = [float(e.get(y_key, 0) or 0) for e in data]
    fig = go.Figure(
        go.Scatter(x=dates, y=y, fill="tozeroy", mode="lines", line=dict(color=color))
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_dark",
        height=120,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def donut_chart(data):
    # Example: trades allocation (gains vs losses)
    gains = sum(
        float(e.get("RealizedPnL", 0) or 0)
        for e in data
        if (e.get("RealizedPnL", 0) or 0) > 0
    )
    losses = -sum(
        float(e.get("RealizedPnL", 0) or 0)
        for e in data
        if (e.get("RealizedPnL", 0) or 0) < 0
    )
    fig = go.Figure(
        go.Pie(
            labels=["Gains", "Losses"],
            values=[gains, losses],
            hole=0.7,
            marker_colors=["#10b981", "#f43f5e"],
        )
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False, height=120)
    st.plotly_chart(fig, use_container_width=True)


def macro_card(shared):
    macro = shared.get("macro_context", "")
    llm = shared.get("llm_strategy", "")
    st.markdown(
        f"""
    <div class='card macro-card'>
      <div class='macro-title'>Macroeconomic Insights</div>
      <div class='macro-text'>{macro}</div>
      <div class='llm-reco'><b>LLM Recommendation:</b> {llm}</div>
      <button class='copy-btn' onclick='navigator.clipboard.writeText(`{macro}\nLLM: {llm}`)'>Copy</button>
    </div>
    """,
        unsafe_allow_html=True,
    )
