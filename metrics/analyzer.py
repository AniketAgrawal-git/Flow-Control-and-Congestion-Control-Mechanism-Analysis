"""
analyzer.py
Intelligent rule-based diagnostic and recommendation engine.
Evaluates simulation results and produces academic-grade insights into:
- Protocol efficiency vs theoretical Bandwidth-Delay Product (BDP)
- Flow Control (rwnd) vs Congestion Control (cwnd) bottleneck diagnosis
- Head-of-line blocking in Go-Back-N vs Selective Repeat
- TCP loss recovery behavior (Tahoe cwnd collapse vs Reno Fast Recovery)
"""

from typing import List, Dict, Any, Optional
from simulation.network_model import SimulationResult, NetworkConfig


def generate_single_protocol_analysis(result: SimulationResult) -> str:
    """
    Generates structured diagnostic report and insights for a single simulation run.
    """
    cfg = result.config
    m = result.metrics
    p_name = result.protocol_name
    th = m.get("throughput_mbps", 0.0)
    util = m.get("link_utilization_pct", 0.0)
    retrans = m.get("retransmissions", 0)
    overhead = m.get("retransmission_overhead_pct", 0.0)
    timeouts = m.get("timeouts", 0)
    fast_retrans = m.get("fast_retransmits", 0)

    # Physical link metrics
    t_trans = cfg.trans_delay_data_ms
    t_prop = cfg.prop_delay_ms
    rtt = cfg.min_rtt_ms
    a_param = t_prop / max(t_trans, 1e-4)
    bdp_pkts = cfg.bdp_packets

    insights = []
    recommendations = []

    insights.append(f"### 🔬 Executive Technical Evaluation: **{p_name}**")
    insights.append(
        f"- **Measured Throughput:** `{th:.3f} Mbps` (Link Bandwidth: `{cfg.bandwidth_mbps:.1f} Mbps`, "
        f"**Link Utilization: `{util:.1f}%`**)"
    )
    insights.append(
        f"- **Physical Link Parameters:** RTT = `{rtt:.2f} ms` (Prop Delay: `{t_prop:.1f} ms`, "
        f"Trans Delay: `{t_trans:.2f} ms`, Ratio `a = t_prop/t_trans = {a_param:.2f}`)"
    )
    insights.append(
        f"- **Bandwidth-Delay Product (BDP):** `{bdp_pkts:.2f} packets` (Window size required to saturate link: "
        f"`{int(bdp_pkts) + 1}` packets)"
    )

    # Protocol-specific deductions
    if "Stop-and-Wait" in p_name:
        theoretical_eff = 1.0 / (1.0 + 2.0 * a_param) * 100.0
        insights.append(
            f"- **Formula:** Theoretical Efficiency $\\eta = \\frac{{1}}{{1 + 2a}} = "
            f"\\frac{{1}}{{1 + 2({a_param:.2f})}} = {theoretical_eff:.2f}\\%$.\n"
            f"- **Physical Cause:** Because window size is locked at $N=1$, the sender must stay completely idle "
            f"for an entire RTT (`{rtt:.1f} ms`) after transmitting each `{t_trans:.2f} ms` frame. "
            f"The link is unused for `{round(100.0 - theoretical_eff, 1)}%` of the time even with zero packet loss!"
        )
        if retrans > 0:
            insights.append(
                f"- **Loss Impact:** Experienced `{retrans}` retransmissions over `{timeouts}` timeout events. "
                f"Each lost frame incurs an idle stall equal to the RTO (`{cfg.default_rto_ms:.1f} ms`), "
                f"further slashing realized throughput to `{th:.3f} Mbps`."
            )
        recommendations.append(
            f"**Upgrade to Sliding Window Pipelining:** Moving to Go-Back-N or Selective Repeat with window size "
            f"$N \\ge {int(bdp_pkts) + 1}$ would allow continuous transmission, potentially multiplying throughput by up to "
            f"`{min(cfg.bandwidth_mbps / max(th, 1e-4), bdp_pkts):.1f}x`."
        )

    elif "Go-Back-N" in p_name:
        insights.append(
            f"\n#### 🔁 Go-Back-N (GBN) Pipelining & Retransmission Overhead:\n"
            f"- **Pipelining Benefit:** Window pipelining elevated link utilization to `{util:.1f}%` compared to Stop-and-Wait."
        )
        if retrans > 0:
            insights.append(
                f"- **Head-of-Line Blocking & Cascading Retransmissions:** Due to GBN's cumulative ACK scheme and strict in-order receiver, "
                f"whenever a frame was dropped, the receiver **discarded all `{retrans}` subsequent out-of-order frames**.\n"
                f"- When the base timer expired, the sender was forced to retransmit the **entire unacknowledged window** rather than just the missing packet. "
                f"This generated a `{overhead:.1f}%` retransmission overhead."
            )
            recommendations.append(
                "**Deploy Selective Repeat (SR) or TCP SACK:** Buffer out-of-order frames at the receiver to eliminate the redundant retransmission of already delivered packets."
            )
        else:
            insights.append(
                "- **Loss-Free Ideal Flow:** With zero lost frames, GBN sustained uninterrupted pipelined flow without window stalls."
            )

    elif "Selective Repeat" in p_name:
        insights.append(
            f"\n#### 🎯 Selective Repeat (SR) Targeted Recovery:\n"
            f"- **Individual Buffering:** The receiver successfully buffered out-of-order frames within its receive window. "
            f"On packet loss, **only the single unacknowledged frame was retransmitted**."
        )
        if retrans > 0:
            insights.append(
                f"- **Bandwidth Conservation:** Retransmission overhead was confined to `{overhead:.1f}%`, avoiding GBN's window flush penalty."
            )
        recommendations.append(
            "Ensure receiver buffer space matches the sender window size to prevent receiver buffer overflow."
        )

    elif "TCP" in p_name:
        rwnd = m.get("rwnd_limit", 64)
        final_cwnd = m.get("final_cwnd", 1.0)
        bottleneck = m.get("bottleneck_diagnosis", "Unknown")

        insights.append(f"\n#### ⚡ TCP Dynamics & Flow vs Congestion Interaction:")
        insights.append(f"- **Primary Bottleneck Identified:** **{bottleneck}**")

        if "Flow Control Limited" in bottleneck:
            insights.append(
                f"- **Flow Control Throttling ($rwnd < cwnd$):** The receiver advertised window is capped at `rwnd = {rwnd} packets`. "
                f"Even though the network was capable of accommodating a larger congestion window (`cwnd = {final_cwnd:.1f}`), "
                f"the sender was restricted by the fundamental TCP law: "
                f"$$Effective\\_Window = \\min(rwnd, cwnd) = \\min({rwnd}, {int(final_cwnd)}) = {min(rwnd, int(final_cwnd))}$$.\n"
                f"- **System Implication:** The receiver's buffer or application processing rate is the limiting factor, not the network."
            )
            recommendations.append(
                f"Increase receiver buffer capacity (`rwnd`) from `{rwnd}` to at least `{int(bdp_pkts) + 2}` packets to match network BDP."
            )
        else:
            insights.append(
                f"- **Network Congestion Constrained ($cwnd \\le rwnd$):** The receiver provided generous buffer space (`rwnd = {rwnd}`), "
                f"so transmission rate was governed entirely by TCP's congestion window (`cwnd = {final_cwnd:.1f}`)."
            )

        if "Reno" in p_name:
            insights.append(
                f"- **Fast Retransmit & Fast Recovery:** Recorded `{fast_retrans}` Fast Retransmits and `{timeouts}` Timeouts. "
                f"Under 3 duplicate ACKs, TCP Reno executed Fast Retransmit without waiting for an RTO expiry, "
                f"cutting `ssthresh` in half and continuing in Congestion Avoidance rather than collapsing to `cwnd=1`."
            )
        elif "Tahoe" in p_name:
            insights.append(
                f"- **Tahoe Severe Penalty:** Upon detecting packet loss, TCP Tahoe reduced `cwnd` back to 1.0 MSS and reverted to Slow Start. "
                f"This caused recurring throughput dips compared to modern Fast Recovery implementations."
            )

    return "\n".join(insights) + ("\n\n#### 💡 Actionable Optimization Recommendations:\n" + "\n".join(f"- {r}" for r in recommendations) if recommendations else "")


def generate_comparative_analysis(results: List[SimulationResult]) -> str:
    """
    Compares multiple algorithms evaluated under identical network conditions and explains why one outperformed another.
    """
    if not results:
        return "No simulation results available for comparison."

    # Sort by throughput descending
    sorted_res = sorted(results, key=lambda r: r.metrics.get("throughput_mbps", 0.0), reverse=True)
    best = sorted_res[0]
    worst = sorted_res[-1]

    cfg = best.config
    b_th = best.metrics.get("throughput_mbps", 0.0)
    w_th = worst.metrics.get("throughput_mbps", 0.0)
    speedup = b_th / max(w_th, 1e-4)

    report = []
    report.append(f"### 📊 Comparative Analysis & Benchmark Findings")
    report.append(
        f"Under identical network conditions (`Bandwidth = {cfg.bandwidth_mbps} Mbps`, `RTT = {cfg.min_rtt_ms:.1f} ms`, "
        f"`Loss Rate = {cfg.loss_prob * 100:.1f}%`):"
    )
    report.append(
        f"- 🏆 **Highest Performing Algorithm:** **{best.protocol_name}** (`{b_th:.3f} Mbps`, "
        f"`{best.metrics.get('link_utilization_pct', 0.0):.1f}%` link utilization)"
    )
    report.append(
        f"- ⚠️ **Lowest Performing Algorithm:** **{worst.protocol_name}** (`{w_th:.3f} Mbps`, "
        f"`{worst.metrics.get('link_utilization_pct', 0.0):.1f}%` link utilization)"
    )
    report.append(
        f"- **Performance Multiplier:** **{best.protocol_name}** achieved **`{speedup:.2f}x` higher throughput** than {worst.protocol_name}."
    )

    report.append("\n#### 🔍 Why did these differences occur?")

    # GBN vs Selective Repeat comparison
    gbn_res = next((r for r in results if "Go-Back-N" in r.protocol_name), None)
    sr_res = next((r for r in results if "Selective" in r.protocol_name), None)

    if gbn_res and sr_res and cfg.loss_prob > 0:
        gbn_ret = gbn_res.metrics.get("retransmissions", 0)
        sr_ret = sr_res.metrics.get("retransmissions", 0)
        report.append(
            f"1. **Selective Repeat vs Go-Back-N under Packet Loss:**\n"
            f"   - Selective Repeat retransmitted **`{sr_ret}` packets** while Go-Back-N was forced to retransmit **`{gbn_ret}` packets**.\n"
            f"   - **Reason:** Go-Back-N lacks out-of-order buffering at the receiver; any single dropped frame triggers the receiver to discard all subsequent "
            f"in-flight frames, requiring the sender to retransmit the entire window on timeout. Selective Repeat buffers out-of-order packets and retransmits "
            f"exclusively the unacknowledged frame, saving channel capacity and finishing faster."
        )

    # Stop-and-Wait vs Sliding Window
    snw_res = next((r for r in results if "Stop" in r.protocol_name), None)
    if snw_res and len(results) > 1:
        report.append(
            f"2. **Stop-and-Wait vs Pipelined Protocols (BDP Underutilization):**\n"
            f"   - Stop-and-Wait achieved only `{snw_res.metrics.get('throughput_mbps', 0.0):.3f} Mbps` because its window size is constrained to 1.\n"
            f"   - While the link bandwidth is `{cfg.bandwidth_mbps} Mbps`, the link remains idle for `{cfg.min_rtt_ms:.1f} ms` between successive packets. "
            f"Pipelined protocols keep multiple packets in the transmission pipe simultaneously, approaching link capacity."
        )

    # TCP Reno vs Tahoe
    reno_res = next((r for r in results if "Reno" in r.protocol_name), None)
    tahoe_res = next((r for r in results if "Tahoe" in r.protocol_name), None)
    if reno_res and tahoe_res:
        report.append(
            f"3. **TCP Reno vs TCP Tahoe (Fast Recovery Advantage):**\n"
            f"   - TCP Reno sustained `{reno_res.metrics.get('throughput_mbps', 0.0):.3f} Mbps` vs Tahoe's `{tahoe_res.metrics.get('throughput_mbps', 0.0):.3f} Mbps`.\n"
            f"   - **Reason:** On 3 duplicate ACKs, TCP Tahoe drops `cwnd` to 1 MSS and resets into Slow Start. "
            f"TCP Reno performs Fast Retransmit and enters Fast Recovery, deflating `cwnd` to `ssthresh` upon receiving a new ACK and staying in Congestion Avoidance. "
            f"This prevents the dramatic sawtooth throughput collapse suffered by Tahoe."
        )

    return "\n".join(report)
