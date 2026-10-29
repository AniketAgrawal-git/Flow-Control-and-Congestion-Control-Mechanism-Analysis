"""
run_comparisons.py
Pre-built parameter sweep experiment runner for rigorous comparative networking analysis.
Runs controlled benchmarks across window sizes, packet loss rates, RTTs, and receiver buffer capacities.
"""

from typing import List, Dict, Any, Callable
import pandas as pd
from simulation.network_model import NetworkConfig, SimulationResult
from simulation.engine import run_protocol_simulation, AVAILABLE_PROTOCOLS


def sweep_window_sizes(
    window_sizes: List[int] = [1, 2, 4, 8, 16, 24, 32],
    protocols: List[str] = ["Go-Back-N ARQ", "Selective Repeat ARQ"],
    total_packets: int = 50,
    config: NetworkConfig = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=25.0, loss_prob=0.03)
) -> pd.DataFrame:
    """
    Experiment 1: Sweep sender window size N and analyze throughput scaling up to BDP.
    """
    records = []
    for w in window_sizes:
        for proto in protocols:
            res = run_protocol_simulation(
                protocol=proto,
                total_packets=total_packets,
                config=config,
                window_size=w
            )
            m = res.metrics
            records.append({
                "Window Size (N)": w,
                "Protocol": proto,
                "Throughput (Mbps)": m["throughput_mbps"],
                "Link Utilization (%)": m["link_utilization_pct"],
                "Retransmissions": m["retransmissions"],
                "Completion Time (ms)": m["completion_time_ms"],
                "Avg Delay (ms)": m["avg_packet_delay_ms"]
            })
    return pd.DataFrame(records)


def sweep_packet_loss(
    loss_rates: List[float] = [0.0, 0.01, 0.03, 0.05, 0.10, 0.15, 0.20],
    protocols: List[str] = ["Stop-and-Wait ARQ", "Go-Back-N ARQ", "Selective Repeat ARQ", "TCP Reno", "TCP Tahoe"],
    total_packets: int = 50,
    window_size: int = 8,
    base_config: NetworkConfig = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=25.0)
) -> pd.DataFrame:
    """
    Experiment 2: Sweep packet loss probability from 0% to 20% under identical seeds.
    """
    records = []
    for loss in loss_rates:
        cfg = NetworkConfig(
            bandwidth_mbps=base_config.bandwidth_mbps,
            prop_delay_ms=base_config.prop_delay_ms,
            loss_prob=loss,
            random_seed=42  # Exact same loss sequence across all runs for scientific fairness
        )
        for proto in protocols:
            res = run_protocol_simulation(
                protocol=proto,
                total_packets=total_packets,
                config=cfg,
                window_size=window_size,
                rwnd=32
            )
            m = res.metrics
            records.append({
                "Loss Rate (%)": round(loss * 100.0, 1),
                "Protocol": proto,
                "Throughput (Mbps)": m["throughput_mbps"],
                "Retransmissions": m["retransmissions"],
                "Retransmission Overhead (%)": m["retransmission_overhead_pct"],
                "Completion Time (ms)": m["completion_time_ms"],
                "Link Utilization (%)": m["link_utilization_pct"]
            })
    return pd.DataFrame(records)


def sweep_rtt_latency(
    rtt_ms_list: List[float] = [10.0, 30.0, 50.0, 100.0, 150.0, 200.0],
    protocols: List[str] = ["Stop-and-Wait ARQ", "Go-Back-N ARQ", "Selective Repeat ARQ", "TCP Reno"],
    total_packets: int = 50,
    window_size: int = 8,
    loss_prob: float = 0.02
) -> pd.DataFrame:
    """
    Experiment 3: Sweep round-trip propagation latency and analyze protocol sensitivity.
    """
    records = []
    for rtt in rtt_ms_list:
        cfg = NetworkConfig(
            bandwidth_mbps=10.0,
            prop_delay_ms=rtt / 2.0,  # One-way delay
            loss_prob=loss_prob,
            random_seed=42
        )
        for proto in protocols:
            res = run_protocol_simulation(
                protocol=proto,
                total_packets=total_packets,
                config=cfg,
                window_size=window_size,
                rwnd=32
            )
            m = res.metrics
            records.append({
                "RTT (ms)": rtt,
                "Protocol": proto,
                "Throughput (Mbps)": m["throughput_mbps"],
                "Link Utilization (%)": m["link_utilization_pct"],
                "Avg Delay (ms)": m["avg_packet_delay_ms"],
                "Completion Time (ms)": m["completion_time_ms"]
            })
    return pd.DataFrame(records)


def sweep_flow_vs_congestion(
    rwnd_values: List[int] = [2, 4, 8, 16, 32, 64],
    loss_rates: List[float] = [0.0, 0.05],
    total_packets: int = 60,
    base_config: NetworkConfig = NetworkConfig(bandwidth_mbps=20.0, prop_delay_ms=20.0)
) -> pd.DataFrame:
    """
    Experiment 4: Investigate the interaction between Flow Control (rwnd) and Congestion Control (cwnd).
    Evaluates how rwnd caps throughput even on high-bandwidth uncongested links.
    """
    records = []
    for loss in loss_rates:
        for rwnd in rwnd_values:
            cfg = NetworkConfig(
                bandwidth_mbps=base_config.bandwidth_mbps,
                prop_delay_ms=base_config.prop_delay_ms,
                loss_prob=loss,
                random_seed=42
            )
            for proto in ["TCP Reno", "TCP Tahoe"]:
                res = run_protocol_simulation(
                    protocol=proto,
                    total_packets=total_packets,
                    config=cfg,
                    rwnd=rwnd,
                    initial_ssthresh=32.0
                )
                m = res.metrics
                records.append({
                    "Receiver Buffer (rwnd)": rwnd,
                    "Loss Rate (%)": round(loss * 100.0, 1),
                    "Condition": f"Loss={round(loss*100)}%",
                    "Protocol": proto,
                    "Throughput (Mbps)": m["throughput_mbps"],
                    "Link Utilization (%)": m["link_utilization_pct"],
                    "Bottleneck": res.bottleneck_type,
                    "Completion Time (ms)": m["completion_time_ms"]
                })
    return pd.DataFrame(records)

