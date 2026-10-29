"""
tcp_congestion.py
Discrete-event simulation of TCP Congestion Control algorithms:
- TCP Tahoe (Slow Start, Congestion Avoidance, cwnd=1 on 3 Dup ACKs or Timeout)
- TCP Reno (Slow Start, Congestion Avoidance, Fast Retransmit & Fast Recovery)
- TCP Cubic (Modern cubic window growth function)

Models the joint constraint: Effective Window = min(rwnd, cwnd),
allowing direct observation of Flow Control Bottlenecks vs Congestion Control Bottlenecks.
"""

import heapq
import random
import math
from typing import List, Dict, Any, Optional, Set
from simulation.network_model import (
    NetworkConfig, SimulationResult, SimulationEvent, LadderEntry
)


def simulate_tcp(
    total_packets: int,
    variant: str = "Reno",               # "Tahoe", "Reno", or "Cubic"
    initial_ssthresh: float = 32.0,
    rwnd: int = 64,                      # Receiver Advertised Window (Flow Control limit)
    config: Optional[NetworkConfig] = None,
    max_simulation_time_ms: float = 300_000.0
) -> SimulationResult:
    """
    Simulates TCP Congestion Control with receiver flow control constraint (rwnd).
    """
    if config is None:
        config = NetworkConfig()

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

    # TCP State Variables
    cwnd: float = 1.0                    # In MSS (packets)
    ssthresh: float = float(initial_ssthresh)
    state: str = "SLOW_START"            # "SLOW_START", "CONGESTION_AVOIDANCE", "FAST_RECOVERY"

    sender_base = 0
    sender_next = 0
    recv_expected = 0
    recv_buffered: Set[int] = set()
    current_time = 0.0
    sender_free_at = 0.0

    # RTO timer for sender_base
    timer_expiry: Optional[float] = None
    timer_base_seq: Optional[int] = None

    # Duplicate ACK counter
    dup_ack_count = 0
    last_ack_num = -1

    packets_delivered = 0
    total_transmissions = 0
    retransmissions = 0
    timeouts_count = 0
    fast_retransmits_count = 0

    # For Cubic
    cubic_wmax = ssthresh
    cubic_epoch_start = 0.0
    cubic_c = 0.4
    cubic_beta = 0.7

    event_queue: List[tuple] = []
    event_counter = 0

    def push_event(ev_time: float, ev_type: str, payload: dict):
        nonlocal event_counter
        event_counter += 1
        heapq.heappush(event_queue, (ev_time, event_counter, ev_type, payload))

    def effective_window() -> int:
        """Effective sending window = min(rwnd, int(cwnd))"""
        return max(1, min(rwnd, int(math.floor(cwnd))))

    # Track how often we were bound by rwnd vs cwnd
    rwnd_limited_ticks = 0
    cwnd_limited_ticks = 0

    push_event(0.0, "CHECK_SEND", {})

    time_series.append({
        "time": 0.0,
        "sender_base": 0,
        "sender_next": 0,
        "window_size": float(effective_window()),
        "cwnd": round(cwnd, 2),
        "rwnd": rwnd,
        "ssthresh": round(ssthresh, 2),
        "in_flight": 0,
        "bytes_delivered": 0,
        "packets_delivered": 0,
        "state": state
    })

    last_ts_record = 0.0

    while event_queue and current_time < max_simulation_time_ms:
        ev_time, _, ev_type, payload = heapq.heappop(event_queue)
        current_time = ev_time

        if packets_delivered >= total_packets and sender_base >= total_packets:
            break

        eff_win = effective_window()
        in_flight = max(0, sender_next - sender_base)

        if int(cwnd) >= rwnd:
            rwnd_limited_ticks += 1
        else:
            cwnd_limited_ticks += 1

        if current_time - last_ts_record >= 5.0 or ev_type in ("TIMEOUT", "FAST_RETRANSMIT", "STATE_CHANGE"):
            last_ts_record = current_time
            time_series.append({
                "time": round(current_time, 2),
                "sender_base": sender_base,
                "sender_next": sender_next,
                "window_size": float(eff_win),
                "cwnd": round(cwnd, 2),
                "rwnd": rwnd,
                "ssthresh": round(ssthresh, 2),
                "in_flight": in_flight,
                "bytes_delivered": packets_delivered * config.packet_size_bytes,
                "packets_delivered": packets_delivered,
                "state": state
            })

        if ev_type == "CHECK_SEND":
            # Send packets while in_flight < effective_window
            eff_win = effective_window()
            while (sender_next - sender_base < eff_win) and (sender_next < total_packets):
                pkt_seq = sender_next
                send_start = max(current_time, sender_free_at)
                send_end = send_start + t_trans
                arr_time = send_start + t_trans + t_prop

                sender_free_at = send_end
                sender_next += 1
                total_transmissions += 1

                if timer_expiry is None:
                    timer_expiry = send_start + rto
                    timer_base_seq = sender_base
                    push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                is_lost = rng.random() < config.loss_prob

                events.append(SimulationEvent(
                    time=round(send_start, 2),
                    event_type="PKT_SEND",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(eff_win),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    in_flight=sender_next - sender_base,
                    description=f"TCP {variant} sent Packet #{pkt_seq} (cwnd={round(cwnd, 2)}, rwnd={rwnd}, W_eff={eff_win})"
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
            if pkt_seq == recv_expected:
                recv_expected += 1
                while recv_expected in recv_buffered:
                    recv_buffered.remove(recv_expected)
                    recv_expected += 1
                ack_num = recv_expected - 1

                ack_start = current_time
                ack_arr = ack_start + t_ack_trans + t_prop

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="PKT_RECV",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(effective_window()),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    in_flight=max(0, sender_next - sender_base),
                    description=f"Receiver accepted in-order Packet #{pkt_seq} (Buffer advanced to #{ack_num}). Generating cumulative ACK #{ack_num}."
                ))

                ack_lost = rng.random() < config.ack_loss_prob
                if ack_lost:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_start, 2),
                        t_end=round(ack_start + t_ack_trans + (t_prop * 0.5), 2),
                        seq_or_ack=ack_num,
                        is_ack=True,
                        is_lost=True,
                        label=f"ACK #{ack_num} [LOST]"
                    ))
                else:
                    ladder.append(LadderEntry(
                        from_node="Receiver",
                        to_node="Sender",
                        t_start=round(ack_start, 2),
                        t_end=round(ack_arr, 2),
                        seq_or_ack=ack_num,
                        is_ack=True,
                        is_lost=False,
                        label=f"ACK #{ack_num}"
                    ))
                    push_event(ack_arr, "ACK_ARRIVE", {"ack_num": ack_num})

            elif pkt_seq > recv_expected:
                # Out-of-order packet: Buffer at receiver, send duplicate cumulative ACK for last received in-order packet
                recv_buffered.add(pkt_seq)
                dup_ack = max(0, recv_expected - 1)
                ack_start = current_time
                ack_arr = ack_start + t_ack_trans + t_prop

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="PKT_OUT_OF_ORDER",
                    seq_num=pkt_seq,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(effective_window()),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    description=f"Receiver buffered out-of-order Packet #{pkt_seq}. Sending duplicate cumulative ACK #{dup_ack}."
                ))

                ladder.append(LadderEntry(
                    from_node="Receiver",
                    to_node="Sender",
                    t_start=round(ack_start, 2),
                    t_end=round(ack_arr, 2),
                    seq_or_ack=dup_ack,
                    is_ack=True,
                    is_lost=False,
                    label=f"ACK #{dup_ack} (dup)"
                ))
                push_event(ack_arr, "ACK_ARRIVE", {"ack_num": dup_ack, "is_dup": True})

            else:
                # Already received in-order packet (retransmission or late)
                dup_ack = max(0, recv_expected - 1)
                ack_start = current_time
                ack_arr = ack_start + t_ack_trans + t_prop
                ladder.append(LadderEntry(
                    from_node="Receiver",
                    to_node="Sender",
                    t_start=round(ack_start, 2),
                    t_end=round(ack_arr, 2),
                    seq_or_ack=dup_ack,
                    is_ack=True,
                    is_lost=False,
                    label=f"ACK #{dup_ack} (dup)"
                ))
                push_event(ack_arr, "ACK_ARRIVE", {"ack_num": dup_ack, "is_dup": True})

        elif ev_type == "ACK_ARRIVE":
            ack_num = payload["ack_num"]

            if ack_num >= sender_base:
                # New ACK arrived!
                new_delivered = (ack_num + 1) - sender_base
                packets_delivered += new_delivered
                sender_base = ack_num + 1
                dup_ack_count = 0
                last_ack_num = ack_num

                # If in Fast Recovery (Reno)
                if state == "FAST_RECOVERY":
                    # Deflate cwnd upon receiving new ACK acknowledging unACKed data
                    cwnd = ssthresh
                    state = "CONGESTION_AVOIDANCE"
                    events.append(SimulationEvent(
                        time=round(current_time, 2),
                        event_type="STATE_CHANGE",
                        ack_num=ack_num,
                        sender_base=sender_base,
                        sender_next=sender_next,
                        window_size=float(effective_window()),
                        cwnd=round(cwnd, 2),
                        rwnd=rwnd,
                        ssthresh=round(ssthresh, 2),
                        description=f"TCP Reno exit Fast Recovery -> Congestion Avoidance (cwnd deflated to ssthresh={round(ssthresh, 2)})."
                    ))
                else:
                    # Update cwnd based on state
                    if variant == "Cubic":
                        # Cubic window adjustment
                        t_sec = max(0.001, (current_time - cubic_epoch_start) / 1000.0)
                        k = (cubic_wmax * (1.0 - cubic_beta) / cubic_c) ** (1.0 / 3.0)
                        w_cubic = cubic_c * ((t_sec - k) ** 3) + cubic_wmax
                        if cwnd < ssthresh:
                            cwnd += 1.0  # Slow start
                        else:
                            cwnd = max(1.0, w_cubic)
                    else:
                        # Tahoe / Reno standard AIMD
                        if cwnd < ssthresh:
                            # Slow Start: cwnd += 1 MSS per ACK (doubles per RTT)
                            cwnd += 1.0
                            state = "SLOW_START"
                        else:
                            # Congestion Avoidance: cwnd += 1/cwnd MSS per ACK (+1 MSS per RTT)
                            cwnd += 1.0 / max(cwnd, 1.0)
                            state = "CONGESTION_AVOIDANCE"

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="ACK_RECV",
                    ack_num=ack_num,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(effective_window()),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    description=f"ACK #{ack_num} acknowledged data. Phase={state}, cwnd={round(cwnd, 2)}, ssthresh={round(ssthresh, 2)}."
                ))

                # Restart or cancel timer
                if sender_base == sender_next:
                    timer_expiry = None
                    timer_base_seq = None
                else:
                    timer_expiry = current_time + rto
                    timer_base_seq = sender_base
                    push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                push_event(current_time, "CHECK_SEND", {})

            else:
                # Duplicate ACK received
                dup_ack_count += 1
                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="DUP_ACK",
                    ack_num=ack_num,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(effective_window()),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    description=f"Duplicate ACK #{ack_num} received (Count={dup_ack_count})."
                ))

                if state == "FAST_RECOVERY":
                    # While in Fast Recovery (Reno), inflate cwnd for each additional dup ACK
                    if variant == "Reno":
                        cwnd += 1.0
                        push_event(current_time, "CHECK_SEND", {})

                elif dup_ack_count == 3:
                    # 3 Duplicate ACKs detected!
                    fast_retransmits_count += 1
                    retransmissions += 1
                    total_transmissions += 1

                    if variant == "Tahoe":
                        # TCP Tahoe: Drops to cwnd = 1, enters Slow Start
                        ssthresh = max(2.0, cwnd / 2.0)
                        cwnd = 1.0
                        state = "SLOW_START"

                        events.append(SimulationEvent(
                            time=round(current_time, 2),
                            event_type="FAST_RETRANSMIT",
                            seq_num=sender_base,
                            sender_base=sender_base,
                            sender_next=sender_next,
                            window_size=float(effective_window()),
                            cwnd=round(cwnd, 2),
                            rwnd=rwnd,
                            ssthresh=round(ssthresh, 2),
                            description=f"3 Dup ACKs! TCP Tahoe Fast Retransmit #{sender_base}. Drops cwnd=1.0, ssthresh={round(ssthresh, 2)}."
                        ))

                    elif variant in ("Reno", "Cubic"):
                        # TCP Reno / Cubic: Fast Retransmit + Fast Recovery
                        ssthresh = max(2.0, cwnd / 2.0)
                        cwnd = ssthresh + 3.0  # Inflate by 3 packets
                        state = "FAST_RECOVERY"

                        if variant == "Cubic":
                            cubic_wmax = cwnd
                            cubic_epoch_start = current_time

                        events.append(SimulationEvent(
                            time=round(current_time, 2),
                            event_type="FAST_RETRANSMIT",
                            seq_num=sender_base,
                            sender_base=sender_base,
                            sender_next=sender_next,
                            window_size=float(effective_window()),
                            cwnd=round(cwnd, 2),
                            rwnd=rwnd,
                            ssthresh=round(ssthresh, 2),
                            description=f"3 Dup ACKs! TCP Reno Fast Retransmit #{sender_base} & Fast Recovery (ssthresh={round(ssthresh, 2)}, cwnd={round(cwnd, 2)})."
                        ))

                    # Retransmit the missing packet immediately!
                    retrans_seq = sender_base
                    send_start = max(current_time, sender_free_at)
                    send_end = send_start + t_trans
                    arr_time = send_start + t_trans + t_prop

                    sender_free_at = send_end
                    timer_expiry = send_start + rto
                    timer_base_seq = sender_base
                    push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                    is_lost = rng.random() < config.loss_prob
                    if is_lost:
                        ladder.append(LadderEntry(
                            from_node="Sender",
                            to_node="Receiver",
                            t_start=round(send_start, 2),
                            t_end=round(send_start + t_trans + (t_prop * 0.5), 2),
                            seq_or_ack=retrans_seq,
                            is_ack=False,
                            is_lost=True,
                            is_retransmission=True,
                            label=f"Pkt #{retrans_seq} [FAST-RETRANS-LOST]"
                        ))
                    else:
                        ladder.append(LadderEntry(
                            from_node="Sender",
                            to_node="Receiver",
                            t_start=round(send_start, 2),
                            t_end=round(arr_time, 2),
                            seq_or_ack=retrans_seq,
                            is_ack=False,
                            is_lost=False,
                            is_retransmission=True,
                            label=f"Pkt #{retrans_seq} [FAST-RETRANS]"
                        ))
                        push_event(arr_time, "PKT_ARRIVE", {"seq_num": retrans_seq})

                    push_event(current_time, "CHECK_SEND", {})

        elif ev_type == "TIMEOUT":
            # Timeout indicates severe congestion
            if (timer_expiry is not None and
                abs(current_time - timer_expiry) < 1e-4 and
                sender_base == payload["timer_seq"] and
                sender_base < total_packets):

                timeouts_count += 1
                retransmissions += 1
                total_transmissions += 1

                # On Timeout: Both Tahoe and Reno set ssthresh=cwnd/2, cwnd=1, Slow Start
                ssthresh = max(2.0, cwnd / 2.0)
                cwnd = 1.0
                state = "SLOW_START"
                dup_ack_count = 0

                if variant == "Cubic":
                    cubic_wmax = cwnd
                    cubic_epoch_start = current_time

                events.append(SimulationEvent(
                    time=round(current_time, 2),
                    event_type="TIMEOUT",
                    seq_num=sender_base,
                    sender_base=sender_base,
                    sender_next=sender_next,
                    window_size=float(effective_window()),
                    cwnd=round(cwnd, 2),
                    rwnd=rwnd,
                    ssthresh=round(ssthresh, 2),
                    description=f"TIMEOUT on Packet #{sender_base}! TCP drops cwnd to 1.0, ssthresh={round(ssthresh, 2)}. Enter Slow Start."
                ))

                # Retransmit the unACKed base packet
                retrans_seq = sender_base
                send_start = max(current_time, sender_free_at)
                send_end = send_start + t_trans
                arr_time = send_start + t_trans + t_prop

                sender_free_at = send_end
                timer_expiry = current_time + rto
                timer_base_seq = sender_base
                push_event(timer_expiry, "TIMEOUT", {"timer_seq": sender_base, "expected_expiry": timer_expiry})

                is_lost = rng.random() < config.loss_prob
                if is_lost:
                    ladder.append(LadderEntry(
                        from_node="Sender",
                        to_node="Receiver",
                        t_start=round(send_start, 2),
                        t_end=round(send_start + t_trans + (t_prop * 0.5), 2),
                        seq_or_ack=retrans_seq,
                        is_ack=False,
                        is_lost=True,
                        is_retransmission=True,
                        label=f"Pkt #{retrans_seq} [TIMEOUT-RETRANS-LOST]"
                    ))
                else:
                    ladder.append(LadderEntry(
                        from_node="Sender",
                        to_node="Receiver",
                        t_start=round(send_start, 2),
                        t_end=round(arr_time, 2),
                        seq_or_ack=retrans_seq,
                        is_ack=False,
                        is_lost=False,
                        is_retransmission=True,
                        label=f"Pkt #{retrans_seq} [TIMEOUT-RETRANS]"
                    ))
                    push_event(arr_time, "PKT_ARRIVE", {"seq_num": retrans_seq})

                push_event(current_time, "CHECK_SEND", {})

    completion_time = round(current_time, 2)
    total_time_sec = max(completion_time / 1000.0, 1e-6)
    bytes_delivered = packets_delivered * config.packet_size_bytes
    throughput_mbps = (bytes_delivered * 8.0) / (total_time_sec * 1_000_000.0)

    bottleneck_diagnosis = (
        "Flow Control Limited (rwnd < cwnd)" if rwnd_limited_ticks > cwnd_limited_ticks
        else "Congestion Control Limited (cwnd <= rwnd)"
    )

    metrics = {
        "throughput_mbps": round(throughput_mbps, 3),
        "packets_delivered": packets_delivered,
        "total_transmissions": total_transmissions,
        "retransmissions": retransmissions,
        "retransmission_overhead_pct": round((retransmissions / max(packets_delivered, 1)) * 100.0, 1),
        "packet_delivery_ratio_pct": round((packets_delivered / max(total_transmissions, 1)) * 100.0, 1),
        "avg_packet_delay_ms": round(completion_time / max(packets_delivered, 1), 2),
        "link_utilization_pct": round((throughput_mbps / max(config.bandwidth_mbps, 1e-6)) * 100.0, 2),
        "completion_time_ms": completion_time,
        "timeouts": timeouts_count,
        "fast_retransmits": fast_retransmits_count,
        "final_cwnd": round(cwnd, 2),
        "final_ssthresh": round(ssthresh, 2),
        "rwnd_limit": rwnd,
        "bottleneck_diagnosis": bottleneck_diagnosis
    }

    return SimulationResult(
        protocol_name=f"TCP {variant} (rwnd={rwnd})",
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
        fast_retransmits=fast_retransmits_count,
        bottleneck_type=bottleneck_diagnosis
    )

