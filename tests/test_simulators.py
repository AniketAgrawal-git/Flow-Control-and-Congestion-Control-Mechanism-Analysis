"""
test_simulators.py
Unit and integration tests for flow control and congestion control simulators.
"""

import pytest
from simulation.network_model import NetworkConfig
from simulation.stop_and_wait import simulate_stop_and_wait
from simulation.go_back_n import simulate_go_back_n
from simulation.selective_repeat import simulate_selective_repeat
from simulation.tcp_congestion import simulate_tcp
from simulation.engine import run_protocol_simulation
from metrics.analyzer import generate_single_protocol_analysis, generate_comparative_analysis
from experiments.run_comparisons import sweep_window_sizes


def test_stop_and_wait_zero_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=10.0, loss_prob=0.0, random_seed=123)
    res = simulate_stop_and_wait(total_packets=10, config=cfg)
    assert res.delivered_packets == 10
    assert res.retransmissions == 0
    assert res.metrics["throughput_mbps"] > 0
    assert len(res.events) > 0


def test_stop_and_wait_with_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=10.0, loss_prob=0.2, random_seed=42)
    res = simulate_stop_and_wait(total_packets=10, config=cfg)
    assert res.delivered_packets == 10
    assert res.retransmissions > 0
    assert res.timeouts > 0


def test_go_back_n_zero_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=15.0, loss_prob=0.0, random_seed=42)
    res = simulate_go_back_n(total_packets=20, window_size=5, config=cfg)
    assert res.delivered_packets == 20
    assert res.retransmissions == 0
    assert res.metrics["link_utilization_pct"] > 0


def test_go_back_n_with_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=15.0, loss_prob=0.1, random_seed=42)
    res = simulate_go_back_n(total_packets=20, window_size=5, config=cfg)
    assert res.delivered_packets == 20
    assert res.retransmissions > 0


def test_selective_repeat_zero_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=15.0, loss_prob=0.0, random_seed=42)
    res = simulate_selective_repeat(total_packets=20, window_size=5, config=cfg)
    assert res.delivered_packets == 20
    assert res.retransmissions == 0


def test_selective_repeat_with_loss():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=15.0, loss_prob=0.1, random_seed=42)
    res = simulate_selective_repeat(total_packets=20, window_size=5, config=cfg)
    assert res.delivered_packets == 20
    assert res.retransmissions > 0


def test_tcp_reno_and_tahoe():
    cfg = NetworkConfig(bandwidth_mbps=15.0, prop_delay_ms=20.0, loss_prob=0.05, random_seed=42)
    res_reno = simulate_tcp(total_packets=30, variant="Reno", rwnd=16, config=cfg)
    res_tahoe = simulate_tcp(total_packets=30, variant="Tahoe", rwnd=16, config=cfg)
    assert res_reno.delivered_packets == 30
    assert res_tahoe.delivered_packets == 30
    assert "TCP Reno" in res_reno.protocol_name
    assert "TCP Tahoe" in res_tahoe.protocol_name


def test_analysis_generation():
    cfg = NetworkConfig(bandwidth_mbps=10.0, prop_delay_ms=10.0, loss_prob=0.05, random_seed=42)
    res1 = run_protocol_simulation("Go-Back-N ARQ", total_packets=15, config=cfg, window_size=4)
    res2 = run_protocol_simulation("Selective Repeat ARQ", total_packets=15, config=cfg, window_size=4)
    report_single = generate_single_protocol_analysis(res1)
    report_comp = generate_comparative_analysis([res1, res2])
    assert len(report_single) > 50
    assert "Go-Back-N" in report_single
    assert len(report_comp) > 50


def test_experiment_sweep():
    df = sweep_window_sizes(window_sizes=[2, 4], protocols=["Go-Back-N ARQ"], total_packets=10)
    assert not df.empty
    assert "Window Size (N)" in df.columns
    assert len(df) == 2

