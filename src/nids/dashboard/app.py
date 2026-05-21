"""
NIDS Live Alert Dashboard — Premium Streamlit UI
"""

import os
import sys
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.nids.data.loader import FEATURE_COLUMNS
from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.pipeline.processor import Pipeline, simulate_flow

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(page_title="NIDS · Threat Detection", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

# ── Premium Dark Theme CSS ───────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-primary: #0a0e17;
    --bg-secondary: #111827;
    --bg-card: #1a2332;
    --bg-card-hover: #1f2b3d;
    --border: #2a3a4e;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --accent-cyan: #06b6d4;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-amber: #f59e0b;
    --accent-purple: #8b5cf6;
    --glow-cyan: 0 0 20px rgba(6,182,212,0.3);
    --glow-red: 0 0 20px rgba(239,68,68,0.3);
}

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--bg-secondary) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stToolbar"] { display: none !important; }

/* Metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--bg-card) 0%, #15202e 100%) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 20px 24px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--glow-cyan) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}

/* Headings */
h1, h2, h3, h4 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; }

/* Divider */
hr { border-color: var(--border) !important; opacity: 0.5 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent-cyan) 0%, #0891b2 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(6,182,212,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* Slider */
.stSlider > div > div { color: var(--text-secondary) !important; }

/* Checkbox */
.stCheckbox label span { color: var(--text-secondary) !important; }

/* Plotly charts: transparent background handled in code */

/* Alert severity badges */
.severity-high { color: #ef4444; background: rgba(239,68,68,0.15); padding: 2px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
.severity-medium { color: #f59e0b; background: rgba(245,158,11,0.15); padding: 2px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
.severity-low { color: #10b981; background: rgba(16,185,129,0.15); padding: 2px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }

/* Glowing header bar */
.header-bar {
    background: linear-gradient(90deg, var(--bg-card) 0%, #0f1b2d 50%, var(--bg-card) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.header-bar::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-purple), transparent);
}
.header-bar h1 {
    margin: 0 !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #06b6d4, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header-bar p {
    margin: 4px 0 0 0 !important;
    color: var(--text-secondary) !important;
    font-size: 0.9rem !important;
}

/* Status indicator */
.status-live {
    display: inline-flex; align-items: center; gap: 6px;
    color: var(--accent-green); font-weight: 600; font-size: 0.85rem;
}
.status-live::before {
    content: '';
    width: 8px; height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse-dot 1.5s infinite;
}
@keyframes pulse-dot {
    0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }
    50% { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
}

/* Alert card */
.alert-card {
    background: linear-gradient(135deg, rgba(239,68,68,0.08) 0%, var(--bg-card) 100%);
    border: 1px solid rgba(239,68,68,0.25);
    border-left: 4px solid var(--accent-red);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: all 0.2s;
}
.alert-card:hover { border-color: rgba(239,68,68,0.5); }
.alert-card .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.alert-card .alert-type { font-weight: 700; color: var(--accent-red); font-size: 0.95rem; }
.alert-card .alert-time { color: var(--text-secondary); font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; }
.alert-card .alert-ips { color: var(--text-secondary); font-size: 0.85rem; font-family: 'JetBrains Mono', monospace; }
.alert-card .alert-conf { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.alert-card .shap-feat { color: var(--accent-cyan); font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; }

/* Section title */
.section-title {
    font-size: 1.05rem; font-weight: 700; color: var(--text-primary);
    margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px;
}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Plotly Theme ─────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8"),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
)

ATTACK_COLORS = {
    "Normal": "#10b981",
    "DoS": "#ef4444",
    "Port Scan": "#f59e0b",
    "Brute Force": "#8b5cf6",
    "Data Exfiltration": "#ec4899",
}


# ── Model Loading ────────────────────────────────────────────
@st.cache_resource
def load_model():
    try:
        clf = NIDSClassifier()
        clf.load("models/nids_model.pkl")
        exp = SHAPExplainer(clf.model, FEATURE_COLUMNS)
        return clf, exp
    except Exception as e:
        st.error(f"⚠️ Model not found. Run `python train_model.py` first.\n\nError: {e}")
        return None, None


# ── Session State Init ───────────────────────────────────────
def init_state():
    if "pipeline" not in st.session_state:
        clf, exp = load_model()
        if clf is None:
            st.stop()

        def on_alert(alert):
            if "alerts" not in st.session_state:
                st.session_state.alerts = []
            st.session_state.alerts.insert(0, alert)
            if len(st.session_state.alerts) > 200:
                st.session_state.alerts = st.session_state.alerts[:200]

        st.session_state.pipeline = Pipeline(clf, exp, on_alert)
        st.session_state.alerts = []
        st.session_state.start_time = time.time()
        st.session_state.latency_history = []
        st.session_state.flow_timeline = []


def process_flows(n: int):
    pipeline = st.session_state.pipeline
    for _ in range(n):
        flow = simulate_flow()
        pipeline.process_flow(flow)
        stats = pipeline.get_stats()
        if stats["inference_times"]:
            st.session_state.latency_history.append(stats["inference_times"][-1])
            if len(st.session_state.latency_history) > 500:
                st.session_state.latency_history = st.session_state.latency_history[-500:]
        st.session_state.flow_timeline.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "total": stats["total_flows"],
            "attacks": stats["attack_flows"],
        })
        if len(st.session_state.flow_timeline) > 100:
            st.session_state.flow_timeline = st.session_state.flow_timeline[-100:]


# ── Main App ─────────────────────────────────────────────────
def main():
    init_state()
    pipeline = st.session_state.pipeline
    stats = pipeline.get_stats()

    # Header
    uptime = int(time.time() - st.session_state.start_time)
    st.markdown(f"""
    <div class="header-bar">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <h1>🛡️ NIDS — Network Intrusion Detection System</h1>
                <p>Real-time AI-powered threat detection · XGBoost + SHAP Explainability</p>
            </div>
            <div style="text-align:right;">
                <div class="status-live">LIVE MONITORING</div>
                <p style="color:#64748b;font-size:0.8rem;margin:4px 0 0 0;font-family:'JetBrains Mono',monospace;">
                    Uptime: {uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric Cards ─────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    avg_lat = stats.get("avg_inference_time_ms", 0)
    attack_rate = (stats["attack_flows"] / max(stats["total_flows"], 1)) * 100

    c1.metric("Total Flows", f"{stats['total_flows']:,}")
    c2.metric("Normal", f"{stats['normal_flows']:,}")
    c3.metric("🚨 Attacks", f"{stats['attack_flows']:,}")
    c4.metric("Avg Latency", f"{avg_lat:.1f} ms")
    c5.metric("Attack Rate", f"{attack_rate:.1f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Charts Row ───────────────────────────────────────────
    chart1, chart2, chart3 = st.columns([1, 1, 1])

    with chart1:
        st.markdown('<div class="section-title">📊 Attack Distribution</div>', unsafe_allow_html=True)
        dist = stats.get("attack_distribution", {})
        if dist and sum(v for k, v in dist.items() if k != "Normal") > 0:
            attack_only = {k: v for k, v in dist.items() if k != "Normal"}
            labels = list(attack_only.keys())
            values = list(attack_only.values())
            colors = [ATTACK_COLORS.get(lbl, "#64748b") for lbl in labels]
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color="#1a2332", width=2)),
                textinfo="label+percent", textfont=dict(size=11, color="#e2e8f0"),
                hole=0.55,
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False)
            fig.add_annotation(text=f"<b>{sum(values)}</b><br>attacks",
                             x=0.5, y=0.5, showarrow=False,
                             font=dict(size=16, color="#ef4444"))
            st.plotly_chart(fig, use_container_width=True, key="pie")
        else:
            st.info("No attacks detected yet.")

    with chart2:
        st.markdown('<div class="section-title">⚡ Inference Latency (ms)</div>', unsafe_allow_html=True)
        lat_hist = st.session_state.latency_history
        if lat_hist:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=lat_hist[-100:], mode="lines",
                line=dict(color="#06b6d4", width=2),
                fill="tozeroy", fillcolor="rgba(6,182,212,0.1)",
            ))
            fig.add_hline(y=50, line_dash="dash", line_color="#ef4444",
                         annotation_text="50ms target", annotation_font_color="#ef4444")
            fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
                            xaxis=dict(showgrid=False, showticklabels=False),
                            yaxis=dict(showgrid=True, gridcolor="rgba(42,58,78,0.5)"))
            st.plotly_chart(fig, use_container_width=True, key="lat")
        else:
            st.info("Processing flows to show latency data...")

    with chart3:
        st.markdown('<div class="section-title">📈 Traffic Over Time</div>', unsafe_allow_html=True)
        timeline = st.session_state.flow_timeline
        if len(timeline) > 2:
            tdf = pd.DataFrame(timeline[-50:])
            fig = go.Figure()
            fig.add_trace(go.Bar(x=tdf["time"], y=tdf["total"], name="Total",
                               marker_color="rgba(6,182,212,0.6)"))
            fig.add_trace(go.Bar(x=tdf["time"], y=tdf["attacks"], name="Attacks",
                               marker_color="rgba(239,68,68,0.8)"))
            fig.update_layout(**PLOTLY_LAYOUT, height=280, barmode="overlay",
                            xaxis=dict(showgrid=False, showticklabels=False),
                            yaxis=dict(showgrid=True, gridcolor="rgba(42,58,78,0.5)"))
            st.plotly_chart(fig, use_container_width=True, key="timeline")
        else:
            st.info("Accumulating traffic data...")

    st.divider()

    # ── Live Alert Feed + Controls ───────────────────────────
    left, right = st.columns([3, 1])

    with right:
        st.markdown('<div class="section-title">🎛️ Control Panel</div>', unsafe_allow_html=True)
        auto_run = st.checkbox("Auto-simulate traffic", value=True, key="auto_run")
        flow_rate = st.slider("Flows per batch", 1, 50, 10, disabled=not auto_run)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("▶️ Process", type="primary", use_container_width=True):
                process_flows(20)
                st.rerun()
        with col_b2:
            if st.button("🔄 Reset", use_container_width=True):
                pipeline.reset_stats()
                st.session_state.alerts = []
                st.session_state.latency_history = []
                st.session_state.flow_timeline = []
                st.rerun()

        # Performance summary
        st.markdown("---")
        st.markdown('<div class="section-title">📋 Performance</div>', unsafe_allow_html=True)
        lat_hist = st.session_state.latency_history
        if lat_hist:
            sorted_l = sorted(lat_hist)
            n = len(sorted_l)
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:#94a3b8;line-height:2;">
                P50: <b style="color:#10b981">{sorted_l[int(n*0.5)]:.1f}ms</b><br>
                P95: <b style="color:#f59e0b">{sorted_l[min(int(n*0.95), n-1)]:.1f}ms</b><br>
                P99: <b style="color:#ef4444">{sorted_l[min(int(n*0.99), n-1)]:.1f}ms</b><br>
                Max: <b style="color:#ef4444">{max(lat_hist):.1f}ms</b>
            </div>
            """, unsafe_allow_html=True)

    with left:
        st.markdown('<div class="section-title">🚨 Live Alert Feed</div>', unsafe_allow_html=True)
        alerts = st.session_state.alerts

        if alerts:
            for a in alerts[:12]:
                sev_class = "severity-high" if a.severity == "high" else "severity-medium"
                conf_color = "#ef4444" if a.confidence > 0.8 else "#f59e0b"
                top_feats = ""
                for f in a.top_3_features[:3]:
                    fname = f.get("feature", "?")
                    fval = f.get("value", 0)
                    fimp = f.get("abs_importance", 0)
                    top_feats += f'<span class="shap-feat">▸ {fname}: {fval:.1f} (imp: {fimp:.3f})</span><br>'

                ts_short = a.timestamp.split("T")[-1][:8] if "T" in a.timestamp else a.timestamp[:8]

                st.markdown(f"""
                <div class="alert-card">
                    <div class="alert-header">
                        <span class="alert-type">⚠ {a.attack_type}</span>
                        <span class="{sev_class}">{a.severity.upper()}</span>
                    </div>
                    <div class="alert-ips">{a.src_ip} → {a.dst_ip}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
                        <div>{top_feats}</div>
                        <div style="text-align:right;">
                            <div class="alert-conf" style="color:{conf_color}">{a.confidence:.1%}</div>
                            <div class="alert-time">{ts_short}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#64748b;">
                <div style="font-size:3rem;margin-bottom:12px;">🔍</div>
                <div style="font-size:1rem;">No threats detected yet</div>
                <div style="font-size:0.85rem;margin-top:4px;">Start traffic simulation to monitor for intrusions</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Auto-refresh ─────────────────────────────────────────
    if auto_run:
        process_flows(flow_rate)
        time.sleep(0.15)
        st.rerun()


if __name__ == "__main__":
    main()
