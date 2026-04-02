import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nids.pipeline.processor import Pipeline, simulate_flow, Alert, NetworkFlow
from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.data.loader import FEATURE_COLUMNS


st.set_page_config(
    page_title="NIDS Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_model_and_explainer():
    """Load the trained model and SHAP explainer."""
    try:
        classifier = NIDSClassifier()
        classifier.load("models/nids_model.pkl")

        explainer = SHAPExplainer(classifier.model, FEATURE_COLUMNS)

        return classifier, explainer
    except Exception as e:
        st.warning(f"Could not load model: {e}. Using demo mode.")
        return None, None


def init_pipeline():
    """Initialize or get the pipeline from session state."""
    if "pipeline" not in st.session_state:
        classifier, explainer = load_model_and_explainer()

        def on_alert(alert):
            if "alerts" not in st.session_state:
                st.session_state.alerts = []
            st.session_state.alerts.insert(0, alert)
            if len(st.session_state.alerts) > 100:
                st.session_state.alerts = st.session_state.alerts[:100]

        st.session_state.pipeline = Pipeline(classifier, explainer, on_alert)
        st.session_state.alerts = []
        st.session_state.start_time = time.time()
        st.session_state.flow_count = 0

    return st.session_state.pipeline


def simulate_and_process(pipeline: Pipeline, num_flows: int = 1):
    """Simulate network flows and process them."""
    for _ in range(num_flows):
        flow = simulate_flow()
        pipeline.process_flow(flow)
        st.session_state.flow_count += 1


def main():
    st.title("🛡️ Network Intrusion Detection System")
    st.markdown("**Real-time traffic classification & alert dashboard**")

    pipeline = init_pipeline()

    col1, col2, col3, col4 = st.columns(4)

    stats = pipeline.get_stats()

    with col1:
        st.metric("Total Flows Processed", stats["total_flows"])
    with col2:
        st.metric("Normal Traffic", stats["normal_flows"])
    with col3:
        st.metric("Attacks Detected", stats["attack_flows"])
    with col4:
        avg_latency = stats.get("avg_inference_time_ms", 0)
        st.metric("Avg Inference Time", f"{avg_latency:.1f}ms")

    st.divider()

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Traffic Distribution")
        if stats["total_flows"] > 0:
            labels = ["Normal", "Attack"]
            sizes = [stats["normal_flows"], stats["attack_flows"]]
            chart_data = pd.DataFrame({"Type": labels, "Count": sizes})
            st.bar_chart(chart_data.set_index("Type"))
        else:
            st.info("No data yet. Start traffic simulation to see results.")

    with col_chart2:
        st.subheader("Attack Type Distribution")
        if stats["attack_distribution"]:
            attack_df = pd.DataFrame(
                list(stats["attack_distribution"].items()),
                columns=["Attack Type", "Count"],
            )
            st.bar_chart(attack_df.set_index("Attack Type"))
        else:
            st.info("No attacks detected yet.")

    st.divider()

    col_controls, col_stats = st.columns([1, 2])

    with col_controls:
        st.subheader("🎛️ Control Panel")

        auto_run = st.checkbox("Auto-simulate traffic", value=True, key="auto_run")
        flow_rate = st.slider("Flows per second", 1, 100, 10, disabled=not auto_run)

        if st.button("▶️ Process Flows", type="primary"):
            simulate_and_process(pipeline, 10)
            st.rerun()

        if st.button("🔄 Reset Statistics"):
            pipeline.reset_stats()
            st.session_state.alerts = []
            st.rerun()

        st.caption(
            f"Running for {int(time.time() - st.session_state.start_time)} seconds"
        )

    with col_stats:
        st.subheader("📊 Live Alert Feed")

        if st.session_state.alerts:
            alerts_df = pd.DataFrame(
                [
                    {
                        "ID": a.id,
                        "Timestamp": a.timestamp,
                        "Source IP": a.src_ip,
                        "Dest IP": a.dst_ip,
                        "Attack Type": a.attack_type,
                        "Confidence": f"{a.confidence:.2%}",
                        "Severity": a.severity,
                    }
                    for a in st.session_state.alerts[:20]
                ]
            )
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
        else:
            st.info("No alerts yet. Alerts will appear here when attacks are detected.")

    st.divider()

    st.subheader("🔍 Latest Alert Details")

    if st.session_state.alerts:
        latest_alert = st.session_state.alerts[0]

        col_det1, col_det2 = st.columns(2)

        with col_det1:
            st.markdown(f"**Attack Type:** {latest_alert.attack_type}")
            st.markdown(f"**Source IP:** {latest_alert.src_ip}")
            st.markdown(f"**Destination IP:** {latest_alert.dst_ip}")
            st.markdown(f"**Confidence:** {latest_alert.confidence:.2%}")

        with col_det2:
            st.markdown(f"**Severity:** {latest_alert.severity.upper()}")
            st.markdown(f"**Timestamp:** {latest_alert.timestamp}")

        st.markdown("**Top 3 Triggering Features:**")

        for i, feat in enumerate(latest_alert.top_3_features, 1):
            with st.expander(f"#{i}: {feat.get('feature', 'Unknown')}", expanded=True):
                st.markdown(f"- **Value:** {feat.get('value', 'N/A'):.4f}")
                st.markdown(
                    f"- **SHAP Importance:** {feat.get('importance', 'N/A'):.4f}"
                )
                st.markdown(
                    f"- **Absolute Importance:** {feat.get('abs_importance', 'N/A'):.4f}"
                )
    else:
        st.info("No alert details to display. Process some flows to see alerts.")

    if auto_run:
        simulate_and_process(pipeline, flow_rate // 10 + 1)
        time.sleep(0.1)
        st.rerun()


if __name__ == "__main__":
    main()
