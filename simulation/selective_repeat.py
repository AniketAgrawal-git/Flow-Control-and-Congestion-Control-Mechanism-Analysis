"""
selective_repeat.py
Discrete-event simulation of the Selective Repeat (SR) ARQ protocol.
Sender maintains window of size N with independent timers per packet.
Receiver maintains a buffer of size N and selectively acknowledges received packets.
Only damaged or lost packets are retransmitted upon individual timeout.
"""

import heapq
import random
from typing import List, Dict, Any, Set, Optional
from simulation.network_model import (
    NetworkConfig, SimulationResult, SimulationEvent, LadderEntry
)


def simulate_selective_repeat(
    total_packets: int,
    window_size: int,
    config: NetworkConfig,
    max_simulation_time_ms: float = 300_000.0
) -> SimulationResult:
    """
    Simulates Selective Repeat ARQ protocol using individual timers and receiver buffering.
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

    sender_base = 0
    sender_next = 0
    recv_base = 0
    current_time = 0.0
    sender_free_at = 0.0

    # Sender state tracking
    acked_by_sender: Set[int] = set()
    packet_timers: Dict[int, float] = {}  # seq_num -> expiry_time

    # Receiver buffer tracking
    recv_buffered: Set[int] = set()

    packets_delivered = 0
    total_transmissions = 0
    retransmissions = 0
    timeouts_count = 0

    event_queue: List[tuple] = []
    event_counter = 0

    def push_event(ev_time: float, ev_type: str, payload: dict):
        nonlocal event_counter
        event_counter += 1
        heapq.heappush(event_queue, (ev_time, event_counter, ev_type, payload))

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

        if current_time - last_ts_record >= 5.0 or ev_type in ("TIMEOUT", "ACK_ARRIVE"):
            last_ts_record = current_time
            in_flight = len([seq for seq in range(sender_base, sender_next) if seq not in acked_by_sender])
            time_series.append({
                "time": round(current_time, 2),
                "sender_base": sender_base,
                "sender_next": sender_next,
                "window_size": float(window_size),
                "cwnd": float(window_size),
                "rwnd": window_size,
                "in_flight": in_flight,
                "bytes_delivered": packets_delivered * config.packet_size_bytes,
                "packets_delivered": packets_delivered,
                "state": "ACTIVE"
            })

        if ev_type == "CHECK_SEND":
            # Send new packets while window allows
            while sender_next < sender_base + window_size and sender_next < total_packets:
                pkt_seq = sender_next
                send_start = max(current_time, sender_free_at)
                send_end = send_start + t_trans
                arr_time = send_start + t_trans + t_prop

                sender_free_at = send_end
                sender_next += 1
                total_transmissions += 1

                # Schedule individual timer for pkt_seq
                expiry = send_start + rto
                packet_timers[pkt_seq] = expiry
                push_event(expiry, "TIMEOUT", {"seq_num": pkt_seq, "expected_expiry": expiry})

                is_lost = rng.random() < config.loss_prob

                events.append(SimulationEvent(
                    time=round(send_start, 2),
                    event_type="PKT_SEND",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    in_flight=len([s for s in range(sender_base, sender_next) if s not in acked_by_sender]),
                    description=f"SR Sender sent Packet #{pkt_seq}. (Window [{sender_base}..{sender_base + window_size - 1}])"
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
            # Check if within receiver window: [recv_base .. recv_base + window_size - 1]
            if recv_base <= pkt_seq < recv_base + window_size:
                recv_buffered.add(pkt_seq)

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="PKT_RECV",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    description=f"Receiver buffered Packet #{pkt_seq} in receive window [{recv_base}..{recv_base + window_size - 1}]."
                ))

                # Slide receiver window forward over consecutive buffered packets
                while recv_base in recv_buffered:
                    recv_buffered.remove(recv_base)
                    recv_base += 1
                    packets_delivered += 1

                # Send selective individual ACK
                ack_start = current_time
                ack_arr = ack_start + t_ack_trans + t_prop

                ack_lost = rng.random() < config.ack_loss_prob
                if ack_lost:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_start, 2),
                        t_end=round(ack_start + t_ack_trans + (t_prop * 0.5), 2),
                        seq_or_ack=pkt_seq,
                        is_ack=True,
                        is_lost=True,
                        label=f"ACK #{pkt_seq} [LOST]"
                    ))
                else:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_start, 2),
                        t_end=round(ack_arr, 2),
                        seq_or_ack=pkt_seq,
                        is_ack=True,
                        is_lost=False,
                        label=f"ACK #{pkt_seq} (Selective)"
                    ))
                    push_event(ack_arr, "ACK_ARRIVE", {"ack_num": pkt_seq})

            elif pkt_seq < recv_base:
                # Already delivered packet, re-send ACK so sender can stop retransmitting
                ack_start = current_time
                ack_arr = ack_start + t_ack_trans + t_prop

                ladder.append(LadderEntry(
                    from_node="Receiver",
                    to_node="Sender",
                    t_start=round(ack_start, 2),
                    t_end=round(ack_arr, 2),
                    seq_or_ack=pkt_seq,
                    is_ack=True,
                    is_lost=False,
                    label=f"ACK #{pkt_seq} (Re-ACK)"
                ))
                push_event(ack_arr, "ACK_ARRIVE", {"ack_num": pkt_seq})

        elif ev_type == "ACK_ARRIVE":
            ack_num = payload["ack_num"]
            if ack_num not in acked_by_sender:
                acked_by_sender.add(ack_num)
                # Cancel individual timer
                packet_timers.pop(ack_num, None)

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="ACK_RECV",
                    ack_num=ack_num,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(window_size),
                    description=f"Sender received selective ACK #{ack_num}."
                ))

                # If this was the base, advance sender_base to lowest unACKed packet
                old_base = sender_base
                while sender_base in acked_by_sender:
                    sender_base += 1

                if sender_base > old_base:
                    events.append(SimulationEvent(
                        time=round(current_time, 2),
                        event_type="WINDOW_SLIDE",
                        sender_base=sender_base,
                        sender_next=sender_next,
                        window_size=float(window_size),
                        description=f"Sender base slid from #{old_base} to #{sender_base}."
                    ))
                    push_event(current_time, "CHECK_SEND", {})

        elif ev_type == "TIMEOUT":
            seq = payload["seq_num"]
            # Check if timer is still active and packet is unacknowledged
            if seq not in acked_by_sender and seq in packet_timers:
                if abs(current_time - payload["expected_expiry"]) < 1e-4:
                    timeouts_count += 1
                    retransmissions += 1
                    total_transmissions += 1

                    events.append(SimulationEvent(
                        time=round(current_time, 2),
                        event_type="TIMEOUT",
                        seq_num=seq,
                        sender_base=sender_base,
                        sender_next=sender_next,
                        window_size=float(window_size),
                        description=f"TIMEOUT on Packet #{seq}! SR retransmitting ONLY Packet #{seq}."
                    ))

                    # Retransmit ONLY this individual packet
                    send_start = max(current_time, sender_free_at)
                    send_end = send_start + t_trans
                    arr_time = send_start + t_trans + t_prop

                    sender_free_at = send_end
                    expiry = send_start + rto
                    packet_timers[seq] = expiry
                    push_event(expiry, "TIMEOUT", {"seq_num": seq, "expected_expiry": expiry})

                    is_lost = rng.random() < config.loss_prob
                    if is_lost:
                        ladder.append(LadderEntry(
                            from_node="Sender",
                            to_node="Receiver",
                            t_start=round(send_start, 2),
                            t_end=round(send_start + t_trans + (t_prop * 0.5), 2),
                            seq_or_ack=seq,
                            is_ack=False,
                            is_lost=True,
                            is_retransmission=True,
                            label=f"Pkt #{seq} [RETRANS-LOST]"
                        ))
                    else:
                        ladder.append(LadderEntry(
                            from_node="Sender",
                            to_node="Receiver",
                            t_start=round(send_start, 2),
                            t_end=round(arr_time, 2),
                            seq_or_ack=seq,
                            is_ack=False,
                            is_lost=False,
                            is_retransmission=True,
                            label=f"Pkt #{seq} [RETRANS]"
                        ))
                        push_event(arr_time, "PKT_ARRIVE", {"seq_num": seq})

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
        protocol_name=f"Selective Repeat ARQ (N={window_size})",
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
        bottleneck_type="Optimal Selective Retransmission (Out-of-order buffered)"
    )

