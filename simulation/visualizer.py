"""
visualizer.py
Clean, unified visualizations for the network simulator:
- Space-Time Sequence Diagram: Packets moving Sender -> Receiver, ACKs returning Receiver -> Sender, and channel losses
- TCP window dynamics plot (cwnd, rwnd, ssthresh)
- Comparative benchmark bar charts
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List, Tuple
from simulation.network_model import SimulationResult, LadderEntry


def create_simulation_ladder_diagram(
    result: SimulationResult,
    current_time: Optional[float] = None,
    max_packets_to_show: int = 25
) -> go.Figure:
    """
    Unified Space-Time Sequence Diagram:
    - Packets travel from Sender (x=0) to Receiver (x=1)
    - ACKs travel from Receiver (x=1) back to Sender (x=0)
    - Channel losses stop midway with red ❌
    - As current_time changes, lines progressively advance in real-time!
    """
    entries = [e for e in result.ladder_data if e.seq_or_ack < max_packets_to_show]
    if not entries:
        t_max = max(result.completion_time_ms, 50.0)
    else:
        t_max = max(max(e.t_end for e in entries) * 1.05, 50.0)

    # If current_time is None, show the entire completed diagram
    is_live = (current_time is not None and current_time < t_max)
    t_limit = current_time if is_live else t_max

    fig = go.Figure()

    # Host Vertical Timelines
    fig.add_trace(go.Scatter(
        x=[0, 0],
        y=[0, t_max],
        mode="lines",
        line=dict(color="#2563EB", width=3.5),
        name="Sender Host (Tx)",
        hoverinfo="none",
        legendgroup="hosts"
    ))
    fig.add_trace(go.Scatter(
        x=[1, 1],
        y=[0, t_max],
        mode="lines",
        line=dict(color="#16A34A", width=3.5),
        name="Receiver Host (Rx)",
        hoverinfo="none",
        legendgroup="hosts"
    ))

    # Keep legend clean: show each category only once
    shown_in_legend = {
        "data": False,
        "retrans": False,
        "lost": False,
        "ack": False,
        "dup_ack": False
    }

    # Markers for packet drop points
    drop_x, drop_y, drop_hover = [], [], []

    # Active in-flight markers (moving at current_time)
    active_x, active_y, active_text, active_colors = [], [], [], []

    for entry in entries:
        if entry.t_start > t_limit:
            continue  # Hasn't started yet at current_time

        is_ack = entry.is_ack
        is_lost = entry.is_lost
        is_retrans = entry.is_retransmission

        # Calculate arrival coordinates
        if is_ack:
            x_start = 1.0
            x_target = 0.5 if is_lost else 0.0
        else:
            x_start = 0.0
            x_target = 0.5 if is_lost else 1.0

        # Check if transmission is complete or currently in flight
        duration = max(entry.t_end - entry.t_start, 0.001)

        if entry.t_end <= t_limit:
            # Completed transmission
            x_end = x_target
            y_end = entry.t_end

            if is_lost:
                drop_x.append(x_target)
                drop_y.append(entry.t_end)
                drop_hover.append(f"<b>💥 {entry.label}</b><br>Dropped midway in channel at {entry.t_end:.1f} ms<br><i>(Packet never reached Receiver)</i>")
        else:
            # Currently in-flight at t_limit!
            frac = min(1.0, max(0.0, (t_limit - entry.t_start) / duration))
            x_end = x_start + frac * (x_target - x_start)
            y_end = t_limit

            active_x.append(x_end)
            active_y.append(y_end)
            active_text.append(f"{'📬' if is_ack else '📦'} #{entry.seq_or_ack}")
            active_colors.append("#FB8C00" if is_ack else "#29B6F6")

        # Color and line styling
        if is_lost:
            color = "#DC2626"
            dash = "dash"
            cat_key = "lost"
            legend_label = "Lost Packet (❌ Drop)"
        elif is_retrans:
            color = "#9333EA"
            dash = "dot"
            cat_key = "retrans"
            legend_label = "Retransmitted Packet"
        elif is_ack:
            is_dup = "(dup)" in entry.label
            color = "#D97706" if is_dup else "#16A34A"
            dash = "dot" if is_dup else "solid"
            cat_key = "dup_ack" if is_dup else "ack"
            legend_label = "Duplicate ACK" if is_dup else "Successful ACK"
        else:
            color = "#0284C7"
            dash = "solid"
            cat_key = "data"
            legend_label = "Data Packet"

        show_leg = not shown_in_legend[cat_key]
        shown_in_legend[cat_key] = True

        dir_str = "Receiver (Rx) ➡️ Sender (Tx)" if is_ack else "Sender (Tx) ➡️ Receiver (Rx)"
        status_str = "❌ Dropped in transit" if is_lost else ("🔁 Selective Retransmission" if is_retrans else "✅ Delivered")
        hover_txt = (
            f"<b>{entry.label}</b><br>"
            f"Direction: {dir_str}<br>"
            f"Timeline: {entry.t_start:.1f} ms ➔ {entry.t_end:.1f} ms<br>"
            f"Status: {status_str}"
        )

        fig.add_trace(go.Scatter(
            x=[x_start, x_end],
            y=[entry.t_start, y_end],
            mode="lines",
            line=dict(color=color, width=2.0, dash=dash),
            name=legend_label,
            showlegend=show_leg,
            hoverinfo="text",
            hovertext=hover_txt
        ))

    # Add red explosion markers for dropped packets
    if drop_x:
        fig.add_trace(go.Scatter(
            x=drop_x,
            y=drop_y,
            mode="markers+text",
            marker=dict(size=12, symbol="x", color="#DC2626", line=dict(width=2.5, color="#991B1B")),
            text=[" ✖ [LOST]" for _ in drop_x],
            textposition="middle right",
            textfont=dict(size=11, color="#DC2626", family="JetBrains Mono, monospace"),
            name="Dropped in Transit",
            showlegend=False,
            hoverinfo="text",
            hovertext=drop_hover
        ))

    # Add moving in-flight packet badges if scrubbing in live simulation mode
    if active_x:
        fig.add_trace(go.Scatter(
            x=active_x,
            y=active_y,
            mode="markers+text",
            marker=dict(size=12, symbol="circle", color=active_colors, line=dict(width=2, color="#0F172A")),
            text=active_text,
            textposition="top center",
            textfont=dict(size=10, color="#FFFFFF", family="Inter, sans-serif"),
            name="In-Flight Packet",
            showlegend=False,
            hoverinfo="none"
        ))

    # If live scrubbing, draw horizontal clock line
    if is_live:
        fig.add_trace(go.Scatter(
            x=[-0.1, 1.1],
            y=[t_limit, t_limit],
            mode="lines+text",
            line=dict(color="#DC2626", width=2.2, dash="dash"),
            text=["", f" ⏱️ Current Time: {t_limit:.1f} ms"],
            textposition="bottom right",
            textfont=dict(color="#DC2626", size=11, family="Inter, sans-serif"),
            name="Current Time",
            showlegend=False,
            hoverinfo="none"
        ))

    # Timeout events
    timeouts = [ev for ev in result.events if ev.event_type == "TIMEOUT" and ev.time <= t_limit]
    for ev in timeouts:
        fig.add_annotation(
            x=0.0,
            y=ev.time,
            text=f"⏱️ Timeout #{ev.seq_num}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#D97706",
            arrowsize=1,
            arrowwidth=1.5,
            ax=50,
            ay=0,
            bgcolor="rgba(254, 243, 199, 0.95)",
            bordercolor="#D97706",
            borderwidth=1,
            font=dict(size=10, color="#92400E", family="JetBrains Mono, monospace")
        )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#1E293B"),
        xaxis=dict(
            tickvals=[0, 1],
            ticktext=["<b>🖥️ Sender Host (Tx)</b>", "<b>🌐 Receiver Host (Rx)</b>"],
            tickfont=dict(size=13, color="#0F172A", family="Inter, sans-serif"),
            range=[-0.15, 1.25],
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text="<b>Simulation Time (ms) ⬇️</b>", font=dict(color="#334155", size=12, family="Inter, sans-serif")),
            autorange="reversed",
            showgrid=True,
            gridcolor="#E2E8F0",
            tickfont=dict(color="#475569", size=11, family="Inter, sans-serif"),
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="#E2E8F0",
            borderwidth=1,
            font=dict(color="#334155", size=11, family="Inter, sans-serif")
        ),
        margin=dict(l=60, r=40, t=50, b=40),
        height=620,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF"
    )

    return fig


# Backward compatibility alias
create_ladder_diagram = create_simulation_ladder_diagram


def create_tcp_dynamics_plot(result: SimulationResult) -> go.Figure:
    """
    Plots cwnd, rwnd, ssthresh, and in_flight over time for TCP simulations.
    """
    ts = result.time_series
    if not ts:
        return go.Figure()

    df = pd.DataFrame(ts)
    fig = go.Figure()

    if "cwnd" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["cwnd"],
            mode="lines",
            name="Congestion Window (cwnd)",
            line=dict(color="#2563EB", width=3)
        ))

    if "rwnd" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["rwnd"],
            mode="lines",
            name="Receiver Advertised Window (rwnd)",
            line=dict(color="#16A34A", width=2, dash="dash")
        ))

    if "ssthresh" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["ssthresh"],
            mode="lines",
            name="Slow Start Threshold (ssthresh)",
            line=dict(color="#D97706", width=2, dash="dot")
        ))

    if "in_flight" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["in_flight"],
            mode="lines",
            name="Packets In-Flight",
            line=dict(color="#9333EA", width=1.5),
            opacity=0.7
        ))

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#1E293B"),
        title="<b>TCP Window Dynamics Over Time</b> ($W_{eff} = \\min(rwnd, cwnd)$)",
        xaxis=dict(title="Simulation Time (ms)", gridcolor="#E2E8F0"),
        yaxis=dict(title="Window Size (Packets / MSS)", gridcolor="#E2E8F0"),
        hovermode="x unified",
        height=400,
        margin=dict(l=50, r=30, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0", borderwidth=1),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF"
    )

    return fig


def create_throughput_comparison_bar(df_metrics: pd.DataFrame) -> go.Figure:
    """
    Generates comparative bar chart for throughput and link utilization.
    """
    fig = px.bar(
        df_metrics,
        x="Protocol",
        y="Throughput (Mbps)",
        color="Protocol",
        text_auto=".2f",
        title="Throughput Comparison Under Identical Network Conditions",
        template="plotly_white"
    )
    fig.update_layout(
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#1E293B"),
        showlegend=False,
        height=380,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=40, r=20, t=50, b=40)
    )
    return fig


def create_overhead_comparison_bar(df_metrics: pd.DataFrame) -> go.Figure:
    """
    Generates comparative bar chart for retransmission overhead and lost packets.
    """
    fig = px.bar(
        df_metrics,
        x="Protocol",
        y="Retransmission Overhead (%)",
        color="Protocol",
        text_auto=".1f",
        title="Retransmission Overhead (%) Comparison",
        template="plotly_white"
    )
    fig.update_layout(
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#1E293B"),
        showlegend=False,
        height=380,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=40, r=20, t=50, b=40)
    )
    return fig
