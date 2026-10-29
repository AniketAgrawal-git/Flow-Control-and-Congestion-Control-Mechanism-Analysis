"""
performance.py
Metrics extraction, statistical aggregation, and comparative evaluation for network simulations.
"""

from typing import List, Dict, Any
import pandas as pd
from simulation.network_model import SimulationResult


def extract_metrics_dataframe(results: List[SimulationResult]) -> pd.DataFrame:
    """
    Consolidates metrics from multiple SimulationResults into a structured Pandas DataFrame.
    """
    rows = []
    for res in results:
        m = res.metrics
        cfg = res.config
        rows.append({
            "Protocol": res.protocol_name,
            "Throughput (Mbps)": m.get("throughput_mbps", 0.0),
            "Link Utilization (%)": m.get("link_utilization_pct", 0.0),
            "Avg Delay (ms)": m.get("avg_packet_delay_ms", 0.0),
            "Retransmissions": m.get("retransmissions", 0),
            "Retransmission Overhead (%)": m.get("retransmission_overhead_pct", 0.0),
            "Packet Delivery Ratio (%)": m.get("packet_delivery_ratio_pct", 0.0),
            "Timeouts": m.get("timeouts", 0),
            "Fast Retransmits": m.get("fast_retransmits", 0),
            "Completion Time (ms)": m.get("completion_time_ms", 0.0),
            "Bottleneck": res.bottleneck_type
        })
    return pd.DataFrame(rows)


def calculate_speedup_ratio(baseline_result: SimulationResult, target_result: SimulationResult) -> float:
    """
    Calculates speedup ratio in throughput: target / baseline.
    """
    b_th = baseline_result.metrics.get("throughput_mbps", 0.001)
    t_th = target_result.metrics.get("throughput_mbps", 0.001)
    return round(t_th / max(b_th, 1e-6), 2)

