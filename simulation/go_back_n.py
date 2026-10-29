"""
go_back_n.py
Discrete-event simulation of the Go-Back-N (GBN) Sliding Window ARQ protocol.
Sender maintains a window of size N. Cumulative ACKs are used.
Receiver accepts packets strictly in order. On timeout, all unacknowledged packets are retransmitted.
"""

import heapq
import random
from typing import List, Dict, Any, Optional
from simulation.network_model import (
    NetworkConfig, SimulationResult, SimulationEvent, LadderEntry
)


def simulate_go_back_n(
    total_packets: int,
    window_size: int,
    config: NetworkConfig,
    max_simulation_time_ms: float = 300_000.0
) -> SimulationResult:
    """
    Simulates Go-Back-N ARQ protocol using an exact discrete-event priority queue.
    """
    if config.random_seed is not None:
        rng = random.Random(config.random_seed)
    else:
        rng = random.Random()

    events: List[SimulationEvent] = []
    ladder: List[LadderEntry] = []
    time_series: List[Dict[str, Any]] = []

    t_trans = config.trans_delay_data_ms
    t_prop = config.prop_delay_ms
    t_ack_trans = config.trans_delay_ack_ms
    rto = config.default_rto_ms

    # Simulation State
    sender_base = 0
    sender_next = 0
    expected_seq_at_receiver = 0
    current_time = 0.0
    sender_free_at = 0.0
    timer_expiry: Optional[float] = None
    timer_base_seq: Optional[int] = None

    packets_delivered = 0
    total_transmissions = 0
    retransmissions = 0
    timeouts_count = 0

    # Event Queue: (time, event_id, event_type, payload)
    # event_types:
    # 1: 'CHECK_SEND'
    # 2: 'PKT_ARRIVE'
    # 3: 'ACK_ARRIVE'
    # 4: 'TIMEOUT'
    event_queue: List[tuple] = []
    event_counter = 0

    def push_event(ev_time: float, ev_type: str, payload: dict):
        nonlocal event_counter
        event_counter += 1
        heapq.heappush(event_queue, (ev_time, event_counter, ev_type, payload))

    # Initial event: sender checks if it can send packets
    push_event(0.0, "CHECK_SEND", {})

    time_series.append({
        "time": 0.0,
        "sender_base": 0,
        "sender_next": 0,
        "window_size": float(window_size),
        "cwnd": float(window_size),
        "rwnd": window_size,
        "in_flight": 0,
        "bytes_delivered": 0,
        "packets_delivered": 0,
        "state": "IDLE"
    })

    last_ts_record = 0.0

    while event_queue and current_time < max_simulation_time_ms:
        ev_time, _, ev_type, payload = heapq.heappop(event_queue)
        current_time = ev_time

        if packets_delivered >= total_packets and sender_base >= total_packets:
            break

        # Periodic time series tracking
        if current_time - last_ts_record >= 5.0 or ev_type in ("TIMEOUT", "ACK_ARRIVE"):
            last_ts_record = current_time
            time_series.append({
                "time": round(current_time, 2),
                "sender_base": sender_base,
                "sender_next": sender_next,
                "window_size": float(window_size),
                "cwnd": float(window_size),
                "rwnd": window_size,
                "in_flight": max(0, sender_next - sender_base),
                "bytes_delivered": packets_delivered * config.packet_size_bytes,
                "packets_delivered": packets_delivered,
                "state": "ACTIVE"
            })

        if ev_type == "CHECK_SEND":
            # Send as many packets as the window permits
            while sender_next < sender_base + window_size and sender_next < total_packets:
                pkt_seq = sender_next
                send_start = max(current_time, sender_free_at)
                send_end = send_start + t_trans
                arr_time = send_start + t_trans + t_prop

                sender_free_at = send_end
                sender_next += 1
                total_transmissions += 1

                # If timer is not running, start it for sender_base
                if timer_expiry is None:
                    timer_expiry = send_start + rto
                    timer_base_seq = sender_base
                    push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                # Determine if packet is lost on the forward channel
                is_lost = rng.random() < config.loss_prob

                events.append(SimulationEvent(
                    time=round(send_start, 2),
                    event_type="PKT_SEND",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=sender_next - sender_base,
                    description=f"GBN Sender transmitted Packet #{pkt_seq} (Window: [{sender_base}..{sender_base + window_size - 1}])"
                ))

                if is_lost:
                    ladder.append(LadderEntry(
                        from_node="Sender",
                        to_node="Receiver",
                        t_start=round(send_start, 2),
                        t_end=round(send_start + t_trans + (t_prop * 0.5), 2),
                        seq_or_ack=pkt_seq,
                        is_ack=False,
                        is_lost=True,
                        label=f"Pkt #{pkt_seq} [LOST]"
                    ))
                    # Packet dropped in transit, receiver never receives it
                else:
                    ladder.append(LadderEntry(
                        from_node="Sender",
                        to_node="Receiver",
                        t_start=round(send_start, 2),
                        t_end=round(arr_time, 2),
                        seq_or_ack=pkt_seq,
                        is_ack=False,
                        is_lost=False,
                        label=f"Pkt #{pkt_seq}"
                    ))
                    push_event(arr_time, "PKT_ARRIVE", {"seq_num": pkt_seq})

        elif ev_type == "PKT_ARRIVE":
            pkt_seq = payload["seq_num"]
            if pkt_seq == expected_seq_at_receiver:
                # In-order packet arrived
                expected_seq_at_receiver += 1
                ack_num = pkt_seq

                ack_send_start = current_time
                ack_arr_time = ack_send_start + t_ack_trans + t_prop

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="PKT_RECV",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"Receiver accepted in-order Packet #{pkt_seq}. Sending ACK #{ack_num}."
                ))

                ack_lost = rng.random() < config.ack_loss_prob
                if ack_lost:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_send_start, 2),
                        t_end=round(ack_send_start + t_ack_trans + (t_prop * 0.5), 2),
                        seq_or_ack=ack_num,
                        is_ack=True,
                        is_lost=True,
                        label=f"ACK #{ack_num} [LOST]"
                    ))
                else:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_send_start, 2),
                        t_end=round(ack_arr_time, 2),
                        seq_or_ack=ack_num,
                        is_ack=True,
                        is_lost=False,
                        label=f"ACK #{ack_num}"
                    ))
                    push_event(ack_arr_time, "ACK_ARRIVE", {"ack_num": ack_num})

            else:
                # Out-of-order packet: GBN discards it and resends cumulative ACK
                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="PKT_DISCARD",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"Receiver discarded out-of-order Packet #{pkt_seq} (Expecting #{expected_seq_at_receiver})."
                ))

                # Re-ACK the highest consecutive packet received
                if expected_seq_at_receiver > 0:
                    dup_ack_num = expected_seq_at_receiver - 1
                    ack_send_start = current_time
                    ack_arr_time = ack_send_start + t_ack_trans + t_prop

                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_send_start, 2),
                        t_end=round(ack_arr_time, 2),
                        seq_or_ack=dup_ack_num,
                        is_ack=True,
                        is_lost=False,
                        label=f"ACK #{dup_ack_num} (dup)"
                    ))
                    push_event(ack_arr_time, "ACK_ARRIVE", {"ack_num": dup_ack_num, "is_dup": True})

        elif ev_type == "ACK_ARRIVE":
            ack_num = payload["ack_num"]
            if ack_num >= sender_base:
                # Cumulative ACK advances the base
                new_delivered = (ack_num + 1) - sender_base
                packets_delivered += new_delivered
                sender_base = ack_num + 1

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="ACK_RECV",
                    ack_num=ack_num,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"Sender received cumulative ACK #{ack_num}. Window slides base to #{sender_base}."
                ))

                if sender_base == sender_next:
                    # No outstanding packets in flight, stop timer
                    timer_expiry = None
                    timer_base_seq = None
                else:
                    # Restart timer for the oldest remaining unACKed packet
                    timer_expiry = current_time + rto
                    timer_base_seq = sender_base
                    push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                # Window moved forward, trigger send check
                push_event(current_time, "CHECK_SEND", {})

            else:
                # Duplicate ACK received (ignored by pure GBN sender until timeout)
                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="DUP_ACK",
                    ack_num=ack_num,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"Sender received duplicate ACK #{ack_num} (base is #{sender_base})."
                ))

        elif ev_type == "TIMEOUT":
            # Check if this timeout is still valid for current sender_base
            if (timer_expiry is not None and
                abs(current_time - payload["expected_expiry"]) < 1e-4 and
                sender_base == payload["timer_seq"] and
                sender_base < total_packets):

                timeouts_count += 1
                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="TIMEOUT",
                    seq_num=sender_base,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"TIMEOUT on Packet #{sender_base}! GBN retransmitting all unACKed packets [{sender_base}..{sender_next - 1}]."
                ))

                # GBN resets next_seq to base and retransmits entire window!
                packets_to_retransmit = sender_next - sender_base
                retransmissions += packets_to_retransmit
                sender_next = sender_base

                # Restart timer for base
                timer_expiry = current_time + rto
                timer_base_seq = sender_base
                push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                # Sender immediately initiates retransmissions
                push_event(current_time, "CHECK_SEND", {})

    completion_time = round(current_time, 2)
    total_time_sec = max(completion_time / 1000.0, 1e-6)
    bytes_delivered = packets_delivered * config.packet_size_bytes
    throughput_mbps = (bytes_delivered * 8.0) / (total_time_sec * 1_000_000.0)

    a = config.prop_delay_ms / max(config.trans_delay_data_ms, 1e-6)
    ideal_eff = min(1.0, float(window_size) / (1.0 + 2.0 * a))

    metrics = {
        "throughput_mbps": round(throughput_mbps, 3),
        "packets_delivered": packets_delivered,
        "total_transmissions": total_transmissions,
        "retransmissions": retransmissions,
        "retransmission_overhead_pct": round((retransmissions / max(packets_delivered, 1)) * 100.0, 1),
        "packet_delivery_ratio_pct": round((packets_delivered / max(total_transmissions, 1)) * 100.0, 1),
        "avg_packet_delay_ms": round(completion_time / max(packets_delivered, 1), 2),
        "link_utilization_pct": round((throughput_mbps / max(config.bandwidth_mbps, 1e-6)) * 100.0, 2),
        "theoretical_efficiency_pct": round(ideal_eff * 100.0, 2),
        "completion_time_ms": completion_time,
        "timeouts": timeouts_count,
        "fast_retransmits": 0
    }

    return SimulationResult(
        protocol_name=f"Go-Back-N ARQ (N={window_size})",
        config=config,
        total_packets_to_send=total_packets,
        completion_time_ms=completion_time,
        events=events,
        ladder_data=ladder,
        time_series=time_series,
        metrics=metrics,
        delivered_packets=packets_delivered,
        total_transmissions=total_transmissions,
        retransmissions=retransmissions,
        timeouts=timeouts_count,
        fast_retransmits=0,
        bottleneck_type="GBN Head-of-Line Blocking on Loss (Discarding out-of-order packets)"
    )

