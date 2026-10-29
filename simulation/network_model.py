"""
network_model.py
Fundamental data structures and models for network packet transmission,
propagation delay, bandwidth, link channel, and event tracking.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import random


@dataclass
class Packet:
    packet_id: int
    seq_num: int
    size_bytes: int = 1000
    is_ack: bool = False
    ack_num: int = 0
    sack_list: List[int] = field(default_factory=list)
    created_at: float = 0.0       # ms
    sent_at: float = 0.0          # ms
    delivered_at: Optional[float] = None  # ms
    is_retransmission: bool = False
    status: str = "IN_TRANSIT"    # "IN_TRANSIT", "DELIVERED", "LOST", "TIMEOUT"
    retransmit_count: int = 0


@dataclass
class NetworkConfig:
    bandwidth_mbps: float = 10.0       # Bandwidth in Megabits per second
    prop_delay_ms: float = 25.0        # One-way propagation delay in milliseconds
    packet_size_bytes: int = 1000      # Data packet payload size in bytes
    ack_size_bytes: int = 40           # ACK packet size in bytes
    loss_prob: float = 0.05            # Probability of packet loss on data link (0.0 - 1.0)
    ack_loss_prob: float = 0.0         # Probability of ACK loss on reverse link
    rto_ms: Optional[float] = None     # Retransmission Timeout; calculated from RTT if None
    random_seed: Optional[int] = 42    # Seed for deterministic reproducible comparisons

    @property
    def trans_delay_data_ms(self) -> float:
        """Transmission delay for a data packet in ms: (bits) / (bps) * 1000"""
        if self.bandwidth_mbps <= 0:
            return 0.1
        return (self.packet_size_bytes * 8.0) / (self.bandwidth_mbps * 1_000_000.0) * 1000.0

    @property
    def trans_delay_ack_ms(self) -> float:
        """Transmission delay for an ACK packet in ms: (bits) / (bps) * 1000"""
        if self.bandwidth_mbps <= 0:
            return 0.01
        return (self.ack_size_bytes * 8.0) / (self.bandwidth_mbps * 1_000_000.0) * 1000.0

    @property
    def min_rtt_ms(self) -> float:
        """Minimum physical Round Trip Time (ms) without queuing delays"""
        return 2.0 * self.prop_delay_ms + self.trans_delay_data_ms + self.trans_delay_ack_ms

    @property
    def default_rto_ms(self) -> float:
        """Default RTO if not explicitly set: 2 * RTT + safe margin"""
        if self.rto_ms is not None and self.rto_ms > 0:
            return self.rto_ms
        return max(2.2 * self.min_rtt_ms, self.min_rtt_ms + 20.0)

    @property
    def bdp_packets(self) -> float:
        """Bandwidth-Delay Product in number of packets: (Bandwidth * RTT) / PacketSize"""
        rtt_sec = self.min_rtt_ms / 1000.0
        bdp_bits = (self.bandwidth_mbps * 1_000_000.0) * rtt_sec
        return bdp_bits / (self.packet_size_bytes * 8.0)


@dataclass
class SimulationEvent:
    time: float                        # Timestamp in ms
    event_type: str                    # "PKT_SEND", "PKT_RECV", "ACK_SEND", "ACK_RECV", "TIMEOUT", "FAST_RETRANSMIT", "CWND_CHANGE"
    seq_num: Optional[int] = None      # Packet sequence number
    ack_num: Optional[int] = None      # ACK number
    sender_base: int = 0               # Window base sequence number
    sender_next: int = 0               # Next sequence number to send
    window_size: float = 1.0           # Effective window size in packets
    cwnd: float = 1.0                  # Congestion window (for TCP)
    rwnd: int = 64                     # Receiver advertised window
    ssthresh: float = 64.0             # Slow start threshold
    in_flight: int = 0                 # Unacknowledged packets in flight
    description: str = ""              # Human-readable explanation of event


@dataclass
class LadderEntry:
    from_node: str                     # "Sender" or "Receiver"
    to_node: str                       # "Receiver" or "Sender"
    t_start: float                     # Transmission start time (ms)
    t_end: float                       # Arrival time (ms)
    seq_or_ack: int                    # Sequence or ACK number
    is_ack: bool                       # True if ACK packet
    is_lost: bool                      # True if packet dropped on channel
    is_retransmission: bool = False    # True if retransmitted packet
    label: str = ""                    # Display annotation (e.g. "Pkt #3", "ACK #3 (dup)")


@dataclass
class SimulationResult:
    protocol_name: str
    config: NetworkConfig
    total_packets_to_send: int
    completion_time_ms: float
    events: List[SimulationEvent] = field(default_factory=list)
    ladder_data: List[LadderEntry] = field(default_factory=list)
    time_series: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    delivered_packets: int = 0
    total_transmissions: int = 0
    retransmissions: int = 0
    timeouts: int = 0
    fast_retransmits: int = 0
    bottleneck_type: str = "Unspecified"

