"""
app.py
Interactive Web Application for:
Analysis of Flow Control and Congestion Control Mechanisms
Author: Computer Networks Academic Project
Tech Stack: Streamlit, Plotly, Pandas, Python Discrete-Event Simulation
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

from simulation.network_model import NetworkConfig
from simulation.engine import run_protocol_simulation, AVAILABLE_PROTOCOLS
from simulation.visualizer import (
    create_simulation_ladder_diagram,
    create_ladder_diagram,
    create_tcp_dynamics_plot,
    create_throughput_comparison_bar,
    create_overhead_comparison_bar
)
from metrics.performance import extract_metrics_dataframe
from metrics.analyzer import (
    generate_single_protocol_analysis,
    generate_comparative_analysis
)
from experiments.run_comparisons import (
    sweep_window_sizes,
    sweep_packet_loss,
    sweep_rtt_latency,
    sweep_flow_vs_congestion
)


# ==========================================
# STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Flow & Congestion Control Analyzer",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Light Theme & Typography Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Font Override */
    html, body, [class*="css"], .stMarkdown, .stText, p, span, label, div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    code, pre, .stCode, kbd {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Light Theme App Shell */
    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        color: #0F172A !important;
        letter-spacing: -0.025em !important;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.03em;
        margin-bottom: 0.25rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #334155 !important;
    }

    /* KPI Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #CBD5E1 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -1px rgba(0, 0, 0, 0.04) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-size: 1.65rem !important;
        font-weight: 800 !important;
    }

    /* Buttons */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        font-size: 0.9rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #334155 !important;
        border: 1px solid #CBD5E1 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #F8FAFC !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
    }

    /* Plotly Chart Container Card */
    div[data-testid="stPlotlyChart"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    /* Dataframe & Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background-color: #FFFFFF !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #64748B !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #2563EB !important;
        border-bottom-color: #2563EB !important;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        border: 1px solid #E2E8F0 !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SIDEBAR CONTROLS & NAVIGATION
# ==========================================
st.sidebar.markdown("## 🌐 Navigation")
nav_choice = st.sidebar.radio(
    "Choose Module",
    [
        "🚀 1. Interactive Protocol Simulator",
        "⚖️ 2. Multi-Protocol Head-to-Head",
        "🔬 3. Automated Parameter Sweeps"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Channel Physics & Workload")

total_packets = st.sidebar.slider("Total Packets to Send", min_value=10, max_value=150, value=40, step=5)
bandwidth_mbps = st.sidebar.slider("Bandwidth (Mbps)", min_value=1.0, max_value=50.0, value=10.0, step=1.0)
prop_delay_ms = st.sidebar.slider("Propagation Delay (ms, one-way)", min_value=5.0, max_value=100.0, value=25.0, step=5.0)
loss_prob_pct = st.sidebar.slider("Packet Loss Rate (%)", min_value=0.0, max_value=25.0, value=5.0, step=1.0)
random_seed = st.sidebar.number_input("Random Seed (for reproducibility)", value=42, step=1)

# Derived Physical Parameters
cfg = NetworkConfig(
    bandwidth_mbps=float(bandwidth_mbps),
    prop_delay_ms=float(prop_delay_ms),
    loss_prob=float(loss_prob_pct / 100.0),
    random_seed=int(random_seed)
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📡 Derived Link Metrics")
st.sidebar.markdown(f"- **Physical RTT:** `{cfg.min_rtt_ms:.2f} ms`")
st.sidebar.markdown(f"- **Transmission Delay:** `{cfg.trans_delay_data_ms:.2f} ms`")
st.sidebar.markdown(f"- **Bandwidth-Delay Product:** `{cfg.bdp_packets:.2f} pkts`")
st.sidebar.markdown(f"- **Default RTO:** `{cfg.default_rto_ms:.2f} ms`")


# ==========================================
# HEADER
# ==========================================
st.markdown('<div class="main-title">Analysis of Flow Control and Congestion Control Mechanisms</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">A Unified Discrete-Event Network Simulator, Performance Benchmark, and Educational Platform</div>', unsafe_allow_html=True)


# ==============================================================================
# TAB 1: INTERACTIVE PROTOCOL SIMULATOR
# ==============================================================================
if "1. Interactive Protocol Simulator" in nav_choice:
    st.markdown("### 🚀 Module 1 & 2: Interactive Discrete-Event Protocol Simulator")
    st.markdown(
        "Execute individual Flow Control or TCP Congestion Control protocols, inspect the exact space-time packet "
        "transmission sequence, and observe window state transitions."
    )

    col_proto, col_win, col_rwnd = st.columns([2, 1, 1])

    with col_proto:
        selected_protocol = st.selectbox("Select Protocol", AVAILABLE_PROTOCOLS, index=1)

    is_tcp = "TCP" in selected_protocol
    is_sliding_window = "Go-Back-N" in selected_protocol or "Selective" in selected_protocol

    with col_win:
        if is_sliding_window:
            window_size = st.slider("Sender Window (N)", min_value=1, max_value=32, value=8)
        else:
            window_size = 1
            st.text_input("Sender Window (N)", value="1 (Fixed)" if "Stop" in selected_protocol else "Dynamic (cwnd)", disabled=True)

    with col_rwnd:
        if is_tcp:
            rwnd_val = st.slider("Receiver Buffer (rwnd)", min_value=2, max_value=64, value=16)
        else:
            rwnd_val = 32
            st.text_input("Receiver Buffer (rwnd)", value="N/A (Flow Control Only)", disabled=True)

    sim_params_key = (
        f"{selected_protocol}_{total_packets}_{bandwidth_mbps}_{prop_delay_ms}_"
        f"{loss_prob_pct}_{random_seed}_{window_size}_{rwnd_val}"
    )

    btn_run = st.button("▶️ Run Simulation", type="primary")

    if btn_run or "active_sim" not in st.session_state or st.session_state.get("sim_params_key") != sim_params_key:
        with st.spinner(f"Simulating {selected_protocol}..."):
            result = run_protocol_simulation(
                protocol=selected_protocol,
                total_packets=total_packets,
                config=cfg,
                window_size=window_size,
                rwnd=rwnd_val,
                initial_ssthresh=16.0
            )
            st.session_state["active_sim"] = result
            st.session_state["sim_params_key"] = sim_params_key
            st.session_state["slider_sim_clock"] = 0.0

    result = st.session_state["active_sim"]

    st.success(f"Simulation completed in {result.completion_time_ms:.2f} ms!")

    # KPI Metrics Row
    m = result.metrics
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Throughput", f"{m['throughput_mbps']:.2f} Mbps")
    kpi2.metric("Link Utilization", f"{m['link_utilization_pct']:.1f}%")
    kpi3.metric("Avg Packet Delay", f"{m['avg_packet_delay_ms']:.1f} ms")
    kpi4.metric("Retransmissions", f"{m['retransmissions']} pkts ({m['retransmission_overhead_pct']:.1f}%)")
    kpi5.metric("Completion Time", f"{m['completion_time_ms']:.1f} ms")

    # ==============================================================================
    # SPACE-TIME SIMULATION DIAGRAM (SENDER ↔ RECEIVER)
    # ==============================================================================
    st.markdown("---")
    st.markdown("### 📡 Live Packet Simulation Diagram")
    st.caption(
        "Watch packets move from Sender (left) to Receiver (right), ACKs return (right to left), "
        "and dropped packets stop midway with ❌ in real time."
    )

    max_t = float(result.completion_time_ms)
    event_times = sorted(list({round(e.time, 1) for e in result.events}))
    key_loss_times = sorted(list({
        round(l.t_end, 1) for l in result.ladder_data if l.is_lost
    } | {
        round(e.time, 1) for e in result.events if e.event_type in ("TIMEOUT", "FAST_RETRANSMIT")
    }))

    if "slider_sim_clock" not in st.session_state:
        st.session_state["slider_sim_clock"] = 0.0
    st.session_state["slider_sim_clock"] = min(max(0.0, float(st.session_state["slider_sim_clock"])), max_t)

    current_t = float(st.session_state["slider_sim_clock"])

    def set_sim_clock(val: float):
        st.session_state["slider_sim_clock"] = min(max(0.0, round(float(val), 2)), max_t)

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.5, 1.2, 2.3])

    with col_ctrl1:
        show_all = st.checkbox("Show Complete Trace (All Packets)", value=False)
        c_p1, c_p2 = st.columns([1.3, 1.0])
        auto_play = c_p1.button("▶️ Auto-Play", type="primary", help="Watch the simulation animate continuously on its own!")
        if auto_play:
            st.session_state["slider_sim_clock"] = max_t
        anim_speed = c_p2.selectbox("Speed", options=["1x (Normal)", "2x (Fast)", "0.5x (Slow)"], index=0, label_visibility="collapsed")

    with col_ctrl2:
        max_ladder_pkts = st.slider(
            "Packets to Display",
            min_value=5,
            max_value=total_packets,
            value=min(20, total_packets),
            step=5
        )

    with col_ctrl3:
        st.markdown("**Step Control:**")
        step_c1, step_c2, step_c3, step_c4, step_c5 = st.columns(5)

        step_c1.button("⏮️ Start", on_click=set_sim_clock, args=(0.0,), help="Go to Start (t=0.0 ms)")

        earlier = [t for t in event_times if t < current_t - 0.2]
        prev_t = earlier[-1] if earlier else 0.0
        step_c2.button("◀️ Prev", on_click=set_sim_clock, args=(prev_t,), help="Step back to previous event")

        later = [t for t in event_times if t > current_t + 0.2]
        next_t = later[0] if later else max_t
        step_c3.button("▶️ Next", on_click=set_sim_clock, args=(next_t,), help="Step forward to next event")

        later_loss = [t for t in key_loss_times if t > current_t + 0.2]
        next_loss_t = later_loss[0] if later_loss else (key_loss_times[0] if key_loss_times else max_t)
        step_c4.button("⚡ Loss", on_click=set_sim_clock, args=(next_loss_t,), help="Jump directly to next Loss/Timeout event")

        step_c5.button("⏩ End", on_click=set_sim_clock, args=(max_t,), help="Jump to completion time")

    speed_delay = {"1x (Normal)": 0.08, "2x (Fast)": 0.03, "0.5x (Slow)": 0.20}.get(anim_speed, 0.08)

    if not show_all:
        sim_clock = st.slider(
            "⏱️ Simulation Clock (ms) — Slide or use step buttons to advance:",
            min_value=0.0,
            max_value=max_t,
            step=max(0.1, round(max_t / 200.0, 1)),
            key="slider_sim_clock"
        )
        active_t = sim_clock
    else:
        active_t = None

    if auto_play:
        start_t = 0.0 if current_t >= max_t - 2.0 else current_t
        relevant_events = [t for t in event_times if t >= start_t]
        step_count = min(30, len(relevant_events))
        if step_count > 1:
            step_idx = [int(i * (len(relevant_events) - 1) / (step_count - 1)) for i in range(step_count)]
            anim_frames = [relevant_events[i] for i in step_idx]
        else:
            anim_frames = relevant_events

        if not anim_frames or anim_frames[-1] != max_t:
            anim_frames.append(max_t)

        status_ph = st.empty()
        chart_ph = st.empty()
        run_id = int(time.time() * 1000)

        for i, t_frame in enumerate(anim_frames):
            fig_frame = create_simulation_ladder_diagram(
                result=result,
                current_time=t_frame,
                max_packets_to_show=max_ladder_pkts
            )
            ev = next((e for e in reversed(result.events) if e.time <= t_frame + 1e-3), result.events[0])
            status_ph.info(f"📍 **Simulation Time: {t_frame:.1f} ms** | Event: `{ev.event_type}` — {ev.description}")
            chart_ph.plotly_chart(fig_frame, use_container_width=True, key=f"anim_frame_{run_id}_{i}")
            time.sleep(speed_delay)
    else:
        # Status indicator
        if active_t is not None:
            active_ev = next((e for e in reversed(result.events) if e.time <= active_t + 1e-3), result.events[0])
            st.info(f"📍 **Simulation Time: {active_t:.1f} ms** | Event: `{active_ev.event_type}` — {active_ev.description}")

        # The ONE Diagram
        fig_sim = create_simulation_ladder_diagram(
            result=result,
            current_time=active_t,
            max_packets_to_show=max_ladder_pkts
        )
        st.plotly_chart(fig_sim, use_container_width=True, key="main_sim_ladder_chart")

    # ==============================================================================
    # TCP DYNAMICS (IF TCP)
    # ==============================================================================
    if is_tcp and result.time_series:
        st.markdown("---")
        st.markdown("### 📈 TCP Window Dynamics ($W_{eff} = \\min(rwnd, cwnd)$)")
        st.caption("Observing Slow Start (exponential), Congestion Avoidance (linear AIMD), and Fast Recovery/Timeout drops.")
        fig_tcp = create_tcp_dynamics_plot(result)
        st.plotly_chart(fig_tcp, use_container_width=True)

    # ==============================================================================
    # INTELLIGENT RULE-BASED ANALYSIS
    # ==============================================================================
    st.markdown("---")
    with st.container():
        report = generate_single_protocol_analysis(result)
        st.markdown(report)

    # ==============================================================================
    # DISCRETE EVENT LOG & CSV EXPORT
    # ==============================================================================
    st.markdown("---")
    st.markdown("### 📜 Discrete Event Trace Log")
    events_data = [
        {
            "Time (ms)": round(e.time, 1),
            "Event": e.event_type,
            "Seq #": str(e.seq_num) if e.seq_num is not None else "-",
            "ACK #": str(e.ack_num) if e.ack_num is not None else "-",
            "Sender Base": str(e.sender_base),
            "Next Seq": str(e.sender_next),
            "Window Size": f"{e.window_size:.1f}",
            "In Flight": e.in_flight,
            "Description": e.description
        }
        for e in result.events
    ]
    df_events = pd.DataFrame(events_data)
    st.dataframe(df_events, use_container_width=True, height=300)

    csv_events = df_events.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Event Log (CSV)",
        data=csv_events,
        file_name=f"{selected_protocol.replace(' ', '_')}_events.csv",
        mime="text/csv"
    )


# ==============================================================================
# TAB 2: MULTI-PROTOCOL HEAD-TO-HEAD BENCHMARK
# ==============================================================================
elif "2. Multi-Protocol Head-to-Head" in nav_choice:
    st.markdown("### ⚖️ Module 3: Multi-Protocol Controlled Benchmark")
    st.markdown(
        "Execute multiple protocols under **identical physical channel conditions** (same bandwidth, RTT, loss rate, and seed) "
        "to objectively compare throughput, delay, and retransmission overhead."
    )

    selected_protos = st.multiselect(
        "Select Algorithms to Compare",
        AVAILABLE_PROTOCOLS,
        default=["Stop-and-Wait ARQ", "Go-Back-N ARQ", "Selective Repeat ARQ", "TCP Reno"]
    )

    c1, c2 = st.columns(2)
    with c1:
        comp_window = st.slider("Window Size N (for GBN & SR)", min_value=2, max_value=32, value=8)
    with c2:
        comp_rwnd = st.slider("Receiver Buffer rwnd (for TCP)", min_value=4, max_value=64, value=32)

    btn_bench = st.button("🚀 Run Comparative Benchmark", type="primary")

    if btn_bench:
        if not selected_protos:
            st.warning("Please select at least one algorithm.")
        else:
            with st.spinner("Executing controlled multi-protocol simulations..."):
                results = []
                for p in selected_protos:
                    res = run_protocol_simulation(
                        protocol=p,
                        total_packets=total_packets,
                        config=cfg,
                        window_size=comp_window,
                        rwnd=comp_rwnd,
                        initial_ssthresh=16.0
                    )
                    results.append(res)
                st.session_state["benchmark_results"] = results
                st.session_state["benchmark_protos"] = selected_protos

    if "benchmark_results" in st.session_state:
        results = st.session_state["benchmark_results"]
        st.success("Benchmark completed!")

        # Consolidated Metrics Table
        df_metrics = extract_metrics_dataframe(results)
        st.markdown("#### 📋 Consolidated Performance Metrics")
        st.dataframe(df_metrics, use_container_width=True)

        # Bar Charts
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig_th = create_throughput_comparison_bar(df_metrics)
            st.plotly_chart(fig_th, use_container_width=True)
        with chart_col2:
            fig_ov = create_overhead_comparison_bar(df_metrics)
            st.plotly_chart(fig_ov, use_container_width=True)

        # Delay & Completion Time Chart
        fig_delay = px.bar(
            df_metrics,
            x="Protocol",
            y="Completion Time (ms)",
            color="Protocol",
            text_auto=".1f",
            title="Total Completion Time (ms) - Lower is Better",
            template="plotly_white"
        )
        fig_delay.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig_delay, use_container_width=True)

        # Automated Comparative Analysis & Recommendations
        st.markdown("---")
        comp_report = generate_comparative_analysis(results)
        st.markdown(comp_report)

        # Download CSV
        csv_comp = df_metrics.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Comparative Results (CSV)",
            data=csv_comp,
            file_name="comparative_benchmark_results.csv",
            mime="text/csv"
        )


# ==============================================================================
# TAB 3: AUTOMATED PARAMETER SWEEPS (EXPERIMENTS 1-4)
# ==============================================================================
elif "3. Automated Parameter Sweeps" in nav_choice:
    st.markdown("### 🔬 Academic Research Experiments & Sensitivity Sweeps")
    st.markdown(
        "Execute systematic parameter sweeps to explore fundamental networking trade-offs across window size, "
        "packet loss rates, network latency, and receiver buffer bottlenecks."
    )

    exp_tab1, exp_tab2, exp_tab3, exp_tab4 = st.tabs([
        "1️⃣ Window Size Sweep (BDP Saturation)",
        "2️⃣ Packet Loss Sweep (Throughput Collapse)",
        "3️⃣ RTT Latency Sweep (Long Fat Networks)",
        "4️⃣ Flow vs Congestion Interplay (rwnd vs cwnd)"
    ])

    with exp_tab1:
        st.markdown("#### Experiment 1: Window Size Scaling & Bandwidth-Delay Product (BDP)")
        st.markdown(
            "Investigate how increasing the sender window size $N$ enhances throughput until saturating the link's "
            "Bandwidth-Delay Product ($N \\ge \\text{BDP}$). Beyond BDP, throughput plateaus."
        )

        if st.button("▶️ Run Window Size Sweep", key="btn_exp1"):
            with st.spinner("Sweeping window sizes from N=1 to N=32..."):
                df_w = sweep_window_sizes(
                    window_sizes=[1, 2, 4, 8, 12, 16, 24, 32],
                    protocols=["Go-Back-N ARQ", "Selective Repeat ARQ"],
                    total_packets=50,
                    config=cfg
                )
            st.success("Sweep finished!")

            fig_w = px.line(
                df_w,
                x="Window Size (N)",
                y="Throughput (Mbps)",
                color="Protocol",
                markers=True,
                title=f"Throughput vs Window Size N (Link Bandwidth: {cfg.bandwidth_mbps} Mbps, BDP: {cfg.bdp_packets:.1f} pkts)",
                template="plotly_white"
            )
            # Add vertical line for BDP
            fig_w.add_vline(x=cfg.bdp_packets, line_dash="dash", line_color="red", annotation_text="BDP Saturation Point")
            st.plotly_chart(fig_w, use_container_width=True)

            st.dataframe(df_w, use_container_width=True)

    with exp_tab2:
        st.markdown("#### Experiment 2: Packet Loss Sweep & Protocol Resilience")
        st.markdown(
            "Sweep packet loss from 0% to 20% to observe the catastrophic throughput collapse in Go-Back-N "
            "compared to the resilient targeted retransmission of Selective Repeat and TCP Reno."
        )

        if st.button("▶️ Run Packet Loss Sweep", key="btn_exp2"):
            with st.spinner("Simulating across loss rates 0% -> 20%..."):
                df_loss = sweep_packet_loss(
                    loss_rates=[0.0, 0.01, 0.03, 0.05, 0.08, 0.12, 0.16, 0.20],
                    protocols=["Stop-and-Wait ARQ", "Go-Back-N ARQ", "Selective Repeat ARQ", "TCP Reno", "TCP Tahoe"],
                    total_packets=45,
                    window_size=8,
                    base_config=cfg
                )
            st.success("Sweep finished!")

            fig_loss = px.line(
                df_loss,
                x="Loss Rate (%)",
                y="Throughput (Mbps)",
                color="Protocol",
                markers=True,
                title="Throughput Degradation Under Increasing Packet Loss",
                template="plotly_white"
            )
            st.plotly_chart(fig_loss, use_container_width=True)

            fig_loss_ret = px.line(
                df_loss,
                x="Loss Rate (%)",
                y="Retransmission Overhead (%)",
                color="Protocol",
                markers=True,
                title="Retransmission Overhead (%) vs Packet Loss",
                template="plotly_white"
            )
            st.plotly_chart(fig_loss_ret, use_container_width=True)

            st.dataframe(df_loss, use_container_width=True)

    with exp_tab3:
        st.markdown("#### Experiment 3: Round-Trip Latency Sweep (Long Fat Networks)")
        st.markdown(
            "Observe how high propagation latency (e.g., satellite or transcontinental links) cripples "
            "Stop-and-Wait efficiency while sliding window and TCP protocols pipeline packets to sustain utilization."
        )

        if st.button("▶️ Run RTT Latency Sweep", key="btn_exp3"):
            with st.spinner("Sweeping RTT from 10 ms to 200 ms..."):
                df_rtt = sweep_rtt_latency(
                    rtt_ms_list=[10.0, 25.0, 50.0, 100.0, 150.0, 200.0],
                    protocols=["Stop-and-Wait ARQ", "Go-Back-N ARQ", "Selective Repeat ARQ", "TCP Reno"],
                    total_packets=45,
                    window_size=8,
                    loss_prob=0.02
                )
            st.success("Sweep finished!")

            fig_rtt = px.line(
                df_rtt,
                x="RTT (ms)",
                y="Throughput (Mbps)",
                color="Protocol",
                markers=True,
                title="Throughput vs Round-Trip Time (RTT)",
                template="plotly_white"
            )
            st.plotly_chart(fig_rtt, use_container_width=True)

            st.dataframe(df_rtt, use_container_width=True)

    with exp_tab4:
        st.markdown("#### Experiment 4: Flow Control (rwnd) vs Congestion Control (cwnd) Interplay")
        st.markdown(
            "Evaluate TCP under varying receiver advertised windows (`rwnd = 2 ... 64`). Demonstrates that when "
            "the receiver's buffer is small, throughput is clamped at $W_{eff} = rwnd$ even when the network link has zero loss."
        )

        if st.button("▶️ Run Flow vs Congestion Sweep", key="btn_exp4"):
            with st.spinner("Evaluating rwnd bottlenecks under 0% and 5% loss..."):
                df_fc = sweep_flow_vs_congestion(
                    rwnd_values=[2, 4, 8, 16, 24, 32, 64],
                    loss_rates=[0.0, 0.05],
                    total_packets=50,
                    base_config=cfg
                )
            st.success("Sweep finished!")

            fig_fc = px.line(
                df_fc,
                x="Receiver Buffer (rwnd)",
                y="Throughput (Mbps)",
                color="Protocol",
                line_dash="Condition",
                markers=True,
                title="Throughput vs Receiver Advertised Window (rwnd)",
                template="plotly_white"
            )
            st.plotly_chart(fig_fc, use_container_width=True)

            st.dataframe(df_fc, use_container_width=True)




