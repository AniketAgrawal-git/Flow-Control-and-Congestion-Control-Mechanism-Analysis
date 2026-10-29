"""
engine.py
Unified coordinator to invoke any flow control or congestion control simulation.
"""

from typing import Optional
from simulation.network_model import NetworkConfig, SimulationResult
from simulation.stop_and_wait import simulate_stop_and_wait
from simulation.go_back_n import simulate_go_back_n
from simulation.selective_repeat import simulate_selective_repeat
from simulation.tcp_congestion import simulate_tcp


AVAILABLE_PROTOCOLS = [
    "Stop-and-Wait ARQ",
    "Go-Back-N ARQ",
    "Selective Repeat ARQ",
    "TCP Reno",
    "TCP Tahoe",
    "TCP Cubic"
]


def run_protocol_simulation(
    protocol: str,
    total_packets: int = 50,
    config: Optional[NetworkConfig] = None,
    window_size: int = 8,
    rwnd: int = 32,
    initial_ssthresh: float = 16.0
) -> SimulationResult:
    """
    Dispatches and executes the selected protocol simulation.
    """
    if config is None:
        config = NetworkConfig()

    p_norm = protocol.lower()

    if "stop" in p_norm:
        return simulate_stop_and_wait(total_packets=total_packets, config=config)
    elif "go-back-n" in p_norm or "gbn" in p_norm:
        return simulate_go_back_n(total_packets=total_packets, window_size=window_size, config=config)
    elif "selective" in p_norm or "sr" in p_norm:
        return simulate_selective_repeat(total_packets=total_packets, window_size=window_size, config=config)
    elif "tahoe" in p_norm:
        return simulate_tcp(
            total_packets=total_packets,
            variant="Tahoe",
            initial_ssthresh=initial_ssthresh,
            rwnd=rwnd,
            config=config
        )
    elif "cubic" in p_norm:
        return simulate_tcp(
            total_packets=total_packets,
            variant="Cubic",
            initial_ssthresh=initial_ssthresh,
            rwnd=rwnd,
            config=config
        )
    else:
        # Default to TCP Reno
        return simulate_tcp(
            total_packets=total_packets,
            variant="Reno",
            initial_ssthresh=initial_ssthresh,
            rwnd=rwnd,
            config=config
        )

