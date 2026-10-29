"""
stop_and_wait.py
Discrete-event simulation of the Stop-and-Wait ARQ (Automatic Repeat reQuest) protocol.
Window size = 1. Sender transmits one packet and waits for its ACK before proceeding.
"""

import random
from typing import List, Dict, Any
from simulation.network_model import (
    NetworkConfig, SimulationResult, SimulationEvent, LadderEntry
)


def simulate_stop_and_wait(
    total_packets: int,
    config: NetworkConfig,
    max_simulation_time_ms: float = 300_000.0
) -> SimulationResult:
    """
    Simulates Stop-and-Wait ARQ protocol under the given network configuration.
    """
    if config.random_seed is not None:
        rng = random.Random(config.random_seed)
    else:
        rng = random.Random()

    events: List[SimulationEvent] = []
    ladder: List[LadderEntry] = []
    time_series: List[Dict[str, Any]] = []

    current_time_ms = 0.0
    packets_delivered = 0
    total_transmissions = 0
    retransmissions = 0
    timeouts_count = 0

    t_trans = config.trans_delay_data_ms
    t_prop = config.prop_delay_ms
    t_ack_trans = config.trans_delay_ack_ms
    rto = config.default_rto_ms

    current_seq = 0
    bytes_delivered = 0

    # Record initial state
    time_series.append({
        "time": 0.0,
        "sender_base": 0,
        "sender_next": 0,
        "window_size": 1.0,
        "cwnd": 1.0,
        "rwnd": 1,
        "in_flight": 0,
        "bytes_delivered": 0,
        "packets_delivered": 0,
        "state": "IDLE"
    })

    while packets_delivered < total_packets and current_time_ms < max_simulation_time_ms:
        seq = current_seq
        is_retrans = False
        retrans_attempts = 0

        # Attempt transmission until ACK is successfully received
        while current_time_ms < max_simulation_time_ms:
            total_transmissions += 1
            if is_retrans:
                retransmissions += 1

            send_start_time = current_time_ms
            send_finish_time = send_start_time + t_trans
            arr_time = send_start_time + t_trans + t_prop
            timeout_time = send_start_time + rto

            # Determine if forward packet is lost
            pkt_lost = rng.random() < config.loss_prob

            events.append(SimulationEvent(
                time=round(send_start_time, 2),
                event_type="PKT_RETRANS" if is_retrans else "PKT_SEND",
                seq_num=seq,
                sender_base=seq,
                sender_next=seq + 1,
                window_size=1.0,
                in_flight=1,
                description=f"Sender transmits Packet #{seq}" + (" (Retransmission)" if is_retrans else "")
            ))

            if pkt_lost:
                # Packet lost on data link
                ladder.append(LadderEntry(
                    from_node="Sender",
                    to_node="Receiver",
                    t_start=round(send_start_time, 2),
                    t_end=round(send_start_time + t_trans + (t_prop * 0.5), 2),
                    seq_or_ack=seq,
                    is_ack=False,
                    is_lost=True,
                    is_retransmission=is_retrans,
                    label=f"Pkt #{seq} [LOST]"
                ))

                # Advance clock to timeout
                current_time_ms = timeout_time
                timeouts_count += 1
                is_retrans = True
                retrans_attempts += 1

                events.append(SimulationEvent(
                    time=round(timeout_time, 2),
                    event_type="TIMEOUT",
                    seq_num=seq,
                    sender_base=seq,
                    sender_next=seq + 1,
                    window_size=1.0,
                    in_flight=0,
                    description=f"Timeout expired for Packet #{seq} at {round(timeout_time, 2)} ms. Triggering Retransmission."
                ))

                time_series.append({
                    "time": round(timeout_time, 2),
                    "sender_base": seq,
                    "sender_next": seq + 1,
                    "window_size": 1.0,
                    "cwnd": 1.0,
                    "rwnd": 1,
                    "in_flight": 0,
                    "bytes_delivered": bytes_delivered,
                    "packets_delivered": packets_delivered,
                    "state": "TIMEOUT"
                })
                continue

            # Packet successfully arrived at receiver
            ladder.append(LadderEntry(
                from_node="Sender",
                to_node="Receiver",
                t_start=round(send_start_time, 2),
                t_end=round(arr_time, 2),
                seq_or_ack=seq,
                is_ack=False,
                is_lost=False,
                is_retransmission=is_retrans,
                label=f"Pkt #{seq}"
            ))

            events.append(SimulationEvent(
                time=round(arr_time, 2),
                event_type="PKT_RECV",
                seq_num=seq,
                sender_base=seq,
                sender_next=seq + 1,
                window_size=1.0,
                in_flight=1,
                description=f"Receiver accepted Packet #{seq}. Generating ACK #{seq}."
            ))

            # Receiver prepares ACK
            ack_start_time = arr_time
            ack_arr_time = ack_start_time + t_ack_trans + t_prop

            # Determine if ACK is lost
            ack_lost = rng.random() < config.ack_loss_prob

            if ack_lost:
                # ACK dropped on reverse path
                ladder.append(LadderEntry(
                    from_node="Receiver",
                    to_node="Sender",
                    t_start=round(ack_start_time, 2),
                    t_end=round(ack_start_time + t_ack_trans + (t_prop * 0.5), 2),
                    seq_or_ack=seq,
                    is_ack=True,
                    is_lost=True,
                    is_retransmission=False,
                    label=f"ACK #{seq} [LOST]"
                ))

                current_time_ms = timeout_time
                timeouts_count += 1
                is_retrans = True
                retrans_attempts += 1

                events.append(SimulationEvent(
                    time=round(timeout_time, 2),
                    event_type="TIMEOUT",
                    seq_num=seq,
                    sender_base=seq,
                    sender_next=seq + 1,
                    window_size=1.0,
                    in_flight=0,
                    description=f"Timeout expired for Packet #{seq} (ACK was lost). Triggering Retransmission."
                ))
                continue

            # ACK safely arrived at sender
            ladder.append(LadderEntry(
                from_node="Receiver",
                to_node="Sender",
                t_start=round(ack_start_time, 2),
                t_end=round(ack_arr_time, 2),
                seq_or_ack=seq,
                is_ack=True,
                is_lost=False,
                is_retransmission=False,
                label=f"ACK #{seq}"
            ))

            packets_delivered += 1
            bytes_delivered += config.packet_size_bytes
            current_time_ms = ack_arr_time

            events.append(SimulationEvent(
                time=round(ack_arr_time, 2),
                event_type="ACK_RECV",
                seq_num=seq,
                ack_num=seq,
                sender_base=seq + 1,
                sender_next=seq + 1,
                window_size=1.0,
                in_flight=0,
                description=f"Sender received ACK #{seq}. Moving window to Packet #{seq + 1}."
            ))

            time_series.append({
                "time": round(current_time_ms, 2),
                "sender_base": seq + 1,
                "sender_next": seq + 1,
                "window_size": 1.0,
                "cwnd": 1.0,
                "rwnd": 1,
                "in_flight": 0,
                "bytes_delivered": bytes_delivered,
                "packets_delivered": packets_delivered,
                "state": "ACKED"
            })

            current_seq += 1
            break

    total_time_sec = max(current_time_ms / 1000.0, 1e-6)
    throughput_mbps = (bytes_delivered * 8.0) / (total_time_sec * 1_000_000.0)
    ideal_eff = 1.0 / (1.0 + 2.0 * (t_prop / max(t_trans, 1e-6)))

    metrics = {
        "throughput_mbps": round(throughput_mbps, 3),
        "packets_delivered": packets_delivered,
        "total_transmissions": total_transmissions,
        "retransmissions": retransmissions,
        "retransmission_overhead_pct": round((retransmissions / max(packets_delivered, 1)) * 100.0, 1),
        "packet_delivery_ratio_pct": round((packets_delivered / max(total_transmissions, 1)) * 100.0, 1),
        "avg_packet_delay_ms": round(current_time_ms / max(packets_delivered, 1), 2),
        "link_utilization_pct": round((throughput_mbps / max(config.bandwidth_mbps, 1e-6)) * 100.0, 2),
        "theoretical_efficiency_pct": round(ideal_eff * 100.0, 2),
        "completion_time_ms": round(current_time_ms, 2),
        "timeouts": timeouts_count,
        "fast_retransmits": 0
    }

    return SimulationResult(
        protocol_name="Stop-and-Wait ARQ",
        config=config,
        total_packets_to_send=total_packets,
        completion_time_ms=round(current_time_ms, 2),
        events=events,
        ladder_data=ladder,
        time_series=time_series,
        metrics=metrics,
        delivered_packets=packets_delivered,
        total_transmissions=total_transmissions,
        retransmissions=retransmissions,
        timeouts=timeouts_count,
        fast_retransmits=0,
        bottleneck_type="Stop-and-Wait Half-Duplex (Window=1, Link Idle during RTT)"
    )

