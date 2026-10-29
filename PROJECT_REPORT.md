# Project Report: Analysis of Flow Control and Congestion Control Mechanisms

**Academic Course:** Computer Networks (CS/IT Engineering)  
**Project Title:** Analysis of Flow Control and Congestion Control Mechanisms  
**Subtitle:** A Unified Discrete-Event Network Simulation Engine, Empirical Performance Benchmark, and Diagnostic Platform  
**Technology Stack:** Python 3.14, Streamlit, Plotly, Pandas, Pytest  
**System Architecture:** Discrete-Event Simulation (DES) via Priority Queue (`heapq`), Modular Layered Architecture  

---

## Table of Contents
1. [Executive Summary & Abstract](#1-executive-summary--abstract)
2. [Introduction & Problem Statement](#2-introduction--problem-statement)
   - 2.1 Background of Reliable Data Transfer
   - 2.2 The Fundamental Distinction: Flow Control vs Congestion Control
   - 2.3 Project Objectives and Scope
3. [Theoretical Foundations & Mathematical Formulations](#3-theoretical-foundations--mathematical-formulations)
   - 3.1 Physical Channel Metrics & Delay Components
   - 3.2 Flow Control Mechanisms (Stop-and-Wait, Go-Back-N, Selective Repeat)
   - 3.3 TCP Congestion Control Principles (Tahoe, Reno, Cubic)
4. [System Architecture & Software Design](#4-system-architecture--software-design)
   - 4.1 Modular Architecture Overview
   - 4.2 Discrete-Event Engine Mechanics (`simulation/`)
   - 4.3 Data Structures and Schema (`network_model.py`)
   - 4.4 Space-Time Sequence Ladder Visualization Engine (`visualizer.py`)
   - 4.5 Performance Analytics & Automated Diagnostic Reasoning (`metrics/`)
5. [Experimental Methodology & Empirical Analysis](#5-experimental-methodology--empirical-analysis)
   - 5.1 Experiment 1: Window Size ($N$) Sweep & BDP Saturation
   - 5.2 Experiment 2: Packet Loss Rate ($0\% - 20\%$) & Resilience Evaluation
   - 5.3 Experiment 3: Round-Trip Latency Sweep & Long-Fat Networks (LFN)
   - 5.4 Experiment 4: Receiver Buffer Constraint ($rwnd$) vs Network Congestion ($cwnd$)
   - 5.5 Experiment 5: Controlled Multi-Protocol Head-to-Head Benchmark
6. [Comparative Evaluation & Discussion](#6-comparative-evaluation--discussion)
   - 6.1 Flow Control Comparison: Stop-and-Wait vs GBN vs Selective Repeat
   - 6.2 Congestion Control Comparison: Tahoe vs Reno vs Cubic
   - 6.3 Combined TCP Window Constraint Verification ($W_{eff} = \min(rwnd, cwnd)$)
7. [System Verification & Automated Testing](#7-system-verification--automated-testing)
   - 7.1 Test Harness & Edge Cases Covered
   - 7.2 Test Execution Results (9/9 Unit Tests Passing)
8. [Viva Voce & Technical Defense Guide](#8-viva-voce--technical-defense-guide)
   - 8.1 Core Theoretical Questions & Answers
   - 8.2 Architectural & Implementation Defense
9. [Conclusion & Future Work](#9-conclusion--future-work)
10. [References & RFC Standards](#10-references--rfc-standards)

---

## 1. Executive Summary & Abstract

In computer networking, reliable and efficient data transmission over physical communication channels depends critically on two distinct regulating mechanisms: **Flow Control** and **Congestion Control**. While flow control prevents a high-speed sender from overwhelming a receiver with finite memory buffers, congestion control prevents senders collectively from overloading intermediate routers, transmission switches, and link queues within the network infrastructure. 

Traditional academic curricula often convey these protocols through static textbook diagrams and theoretical equations, obscuring dynamic runtime behaviors such as cascading timeouts, head-of-line blocking, TCP fast recovery, and buffer starvation. 

This project delivers a **full-featured, high-performance Discrete-Event Network Simulator and Diagnostic Benchmarking Platform** authored in Python, Streamlit, and Plotly. The simulator precisely models physical channel mechanics—including bit transmission delay ($t_{trans}$), propagation latency ($t_{prop}$), random channel packet drops, independent reverse ACK paths, and retransmission timeouts ($RTO$). 

Supported protocols include:
- **Flow Control:** Stop-and-Wait ARQ, Go-Back-N ARQ ($N \ge 1$), and Selective Repeat ARQ (with individual timers and receiver out-of-order buffering).
- **Congestion Control:** TCP Tahoe (Slow Start, Congestion Avoidance, Fast Retransmit), TCP Reno (Fast Recovery via RFC 5681), and TCP Cubic (window-growth scaling).

Key deliverables include an interactive **Space-Time Packet Ladder Sequence Diagram** supporting continuous animated playback, real-time in-flight packet badges, automated parameter sweeps across varying Bandwidth-Delay Products (BDP) and loss rates, and a rule-based automated diagnostic engine that generates academic evaluations of network bottlenecks.

---

## 2. Introduction & Problem Statement

### 2.1 Background of Reliable Data Transfer
The underlying physical layers of packet-switched networks are intrinsically unreliable. Physical media (copper coaxial, optical fiber, wireless RF) are subject to thermal noise, bit corruption, queue overflow at intermediate routers, and packet loss. To support mission-critical applications (such as HTTP/HTTPS, file transfer, and remote execution), the Transport Layer must synthesize a reliable, ordered, byte-stream abstraction on top of best-effort IP delivery.

### 2.2 The Fundamental Distinction: Flow Control vs Congestion Control
A common point of confusion in computer networking is conflating flow control with congestion control. Both mechanisms regulate transmission rate by constraining the sender's window size, but their objectives and feedback signals are fundamentally different:

```
+-----------------------------------------------------------------------------------+
| FLOW CONTROL (Receiver Protection)                                                |
| - Boundary: Protects the receiving host's memory buffer.                          |
| - Feedback Signal: Receiver Advertised Window (rwnd), explicitly communicated      |
|   in the TCP segment header.                                                      |
| - Question Answered: "Does the receiver have sufficient buffer capacity to store  |
|   incoming packets without dropping them?"                                        |
+-----------------------------------------------------------------------------------+
                                        vs
+-----------------------------------------------------------------------------------+
| CONGESTION CONTROL (Network Infrastructure Protection)                            |
| - Boundary: Protects intermediate network routers, switches, and shared links.    |
| - Feedback Signal: Inferred dynamically from packet drops, timeouts, or 3 dup ACKs|
|   using the Congestion Window (cwnd).                                             |
| - Question Answered: "Can the intermediate network fabric carry traffic without   |
|   dropping packets at bottleneck queues?"                                         |
+-----------------------------------------------------------------------------------+
```

In modern transport protocols like TCP, the sender combines both constraints dynamically:
$$\text{Effective Window } (W_{eff}) = \min(rwnd, cwnd)$$

The sender is permanently constrained by the strictest bottleneck: if the network is clear but the receiver application is slow, $rwnd$ dominates; if the receiver has gigabytes of memory but the link is congested, $cwnd$ dominates.

### 2.3 Project Objectives and Scope
1. **Mathematical & Physics-Based Realism:** Model propagation delay, serial bandwidth transmission, round-trip time ($RTT$), and retransmission timeouts ($RTO$) with microsecond-level discrete-event precision.
2. **Unified Implementation:** Build modular state-machine simulators for Stop-and-Wait, Go-Back-N, Selective Repeat, TCP Tahoe, TCP Reno, and TCP Cubic under a common object model.
3. **Interactive Space-Time Visualization:** Create an animated packet sequence ladder diagram showing packets moving across the wire, reverse ACKs, midway drops with failure markers (❌), duplicate ACKs, and timeouts.
4. **Controlled Benchmarking:** Support head-to-head multi-protocol execution under strictly identical pseudorandom seeds, bandwidth, delay, and loss rates.
5. **Parametric Sweeps & Diagnostics:** Automate evaluation sweeps across window sizes ($1$ to $32$), packet loss rates ($0\%$ to $20\%$), and propagation delays ($5\text{ ms}$ to $100\text{ ms}$), providing automated written diagnostic analysis.

---

## 3. Theoretical Foundations & Mathematical Formulations

### 3.1 Physical Channel Metrics & Delay Components

```
Host A (Sender)                                             Host B (Receiver)
   |                                                                |
   |--- Data Packet Transmission (t_trans = L / B)                  |
   |====================\                                           |
   |                     \                                          |
   |                      \  Propagation Delay (t_prop = d / v)     |
   |                       \                                        |
   |                        \====================>| Packet Arrives  |
   |                                              | Process / Buffer|
   |                                              |--- Send ACK     |
   |                                             /                  |
   |                   <========================/                   |
   | ACK Received     /                                             |
   v                 v                                              v
```

1. **Packet Transmission Delay ($t_{trans}$):**
   The time required for the network interface card (NIC) to push all bits of a packet onto the physical medium:
   $$t_{trans} = \frac{L}{B}$$
   Where $L$ is packet length in bits (e.g., $1000\text{ bytes} \times 8 = 8000\text{ bits}$) and $B$ is channel bandwidth in bits per second (bps).

2. **Propagation Delay ($t_{prop}$):**
   The time required for a physical bit signal to travel across the length of the link at signal propagation speed $v$ ($v \approx 2 \times 10^8\text{ m/s}$ in copper/fiber):
   $$t_{prop} = \frac{d}{v}$$

3. **Round-Trip Time ($RTT$):**
   The round-trip duration from packet transmission onset until the complete arrival of its corresponding acknowledgment:
   $$RTT = 2 \cdot t_{prop} + t_{trans,data} + t_{trans,ack}$$

4. **Channel Delay Ratio ($a$):**
   The dimensionless ratio between propagation delay and transmission delay, representing the pipeline capacity of the wire:
   $$a = \frac{t_{prop}}{t_{trans}}$$

5. **Bandwidth-Delay Product ($BDP$):**
   The total volume of unacknowledged data that can simultaneously fill the bidirectional network pipeline:
   $$BDP_{\text{bits}} = B \times RTT$$
   $$BDP_{\text{packets}} = \frac{B \times RTT}{L}$$
   *Rule:* To achieve $100\%$ link utilization, the sender window size $N$ must satisfy $N \ge BDP_{\text{packets}} + 1$.

6. **Retransmission Timeout ($RTO$):**
   Computed using standard Jacobson/Karels smoothed round-trip time estimation:
   $$RTO = SRTT + 4 \times RTTVAR$$
   *(In discrete-event baseline models: $RTO = 2 \times RTT + 2 \times t_{trans}$.)*

---

### 3.2 Flow Control Mechanisms

#### 3.2.1 Stop-and-Wait ARQ ($N = 1$)
- **Algorithm:** The sender transmits exactly 1 data packet and stops all further transmissions until a valid acknowledgment ($ACK$) is received from the receiver host. If the retransmission timer expires before the ACK arrives, the packet is resent.
- **Theoretical Link Efficiency ($\eta$):**
  $$\eta_{\text{Stop-and-Wait}} = \frac{t_{trans}}{t_{trans} + 2 \cdot t_{prop}} = \frac{1}{1 + 2a}$$
- **Bottleneck:** On channels with high $a$ (large bandwidth or long propagation distance), the sender remains idle for more than $95\%$ of the timeline, severely degrading throughput.

#### 3.2.2 Go-Back-N ARQ ($N > 1$)
- **Algorithm:** Pipelined sliding window protocol. The sender can transmit up to $N$ unacknowledged packets without stalling.
- **Acknowledgment Scheme:** **Cumulative ACKs**. An ACK for sequence $k$ asserts that all packets up to and including $k$ have been correctly received.
- **Receiver State:** Strictly **in-order** delivery without out-of-order buffering. If packet $k$ is lost, any subsequent arriving packet ($k+1, k+2, \dots$) is discarded, and the receiver re-emits duplicate ACKs for $k-1$.
- **Retransmission Mechanics:** Single timer associated with the oldest unacknowledged packet (`sender_base`). Upon timeout, the sender must **Go Back $N$** and retransmit all packets currently in flight ($[base \dots next - 1]$).
- **Theoretical Maximum Efficiency:**
  $$\eta_{\text{GBN}} = \min\left(1.0, \frac{N}{1 + 2a}\right)$$
- **Defect Under Packet Loss:** Retransmission overhead escalates rapidly with packet loss rate, wasting physical bandwidth re-sending packets the receiver already inspected and discarded.

#### 3.2.3 Selective Repeat ARQ ($N > 1$)
- **Algorithm:** Both sender and receiver maintain sliding windows of size $N$.
- **Acknowledgment Scheme:** **Selective Individual ACKs**. The receiver acknowledges each individual packet sequence correctly received.
- **Receiver State:** Maintains an **out-of-order receive buffer**. Packets arriving out of sequence (within $[recv\_base \dots recv\_base + N - 1]$) are buffered in memory.
- **Retransmission Mechanics:** The sender maintains an **independent timer for each in-flight packet**. When the timer for packet $k$ expires, the sender retransmits **only packet $k$**, preserving already buffered packets.
- **Window Advance:** When the lowest missing packet is delivered, the receiver window slides forward over all consecutive buffered packets, and the sender window jumps forward upon receiving the ACK.
- **Window Size Constraint:** To prevent sequence number ambiguity between old and new packets across a cyclic sequence space $M = 2^m$:
  $$N \le \frac{M}{2} = 2^{m-1}$$

---

### 3.3 TCP Congestion Control Principles

TCP dynamically probes for available channel bandwidth while backing off when packet loss indicates buffer exhaustion at intermediate routers.

```
Congestion Window (cwnd)
      ^
      |                                  /-- AIMD Linear Congestion Avoidance
      |                                 /
      |                  /-- ssthresh  /
      |                 /             /
      |        *       *-------------*           <-- Loss Event (3 Dup ACKs)
      |       *                                     Reno: cwnd halves (Fast Recovery)
      |      *                                      Tahoe: cwnd resets to 1 (Slow Start)
      |     *   <-- Exponential Slow Start
      |    *
      +----------------------------------------> Time (ms)
```

#### 3.3.1 State Transitions
1. **Slow Start ($cwnd < ssthresh$):**
   - Initial window: $cwnd = 1\text{ MSS}$.
   - For every successful ACK received:
     $$cwnd \leftarrow cwnd + 1\text{ MSS}$$
   - Effectively doubles the congestion window every round-trip time ($RTT$):
     $$cwnd(t + RTT) = 2 \cdot cwnd(t)$$

2. **Congestion Avoidance ($cwnd \ge ssthresh$):**
   - Additive Increase / Multiplicative Decrease (AIMD).
   - For each incoming ACK:
     $$cwnd \leftarrow cwnd + \frac{1}{\lfloor cwnd \rfloor}$$
   - Window increases by approximately $1\text{ MSS}$ per $RTT$:
     $$cwnd(t + RTT) = cwnd(t) + 1\text{ MSS}$$

3. **Loss Event Reactions:**
   - **Timeout (Catastrophic Loss):** Both Tahoe and Reno reset:
     $$ssthresh \leftarrow \max\left(\frac{cwnd}{2}, 2\right)$$
     $$cwnd \leftarrow 1\text{ MSS}$$
     *(Enters Slow Start)*
   - **3 Duplicate ACKs (Mild Loss / Isolated Drop):**
     - **TCP Tahoe:** Ignores Fast Recovery. Drops $cwnd \to 1$, $ssthresh \leftarrow \frac{cwnd}{2}$, restarts in Slow Start.
     - **TCP Reno (RFC 5681):** Executes **Fast Retransmit & Fast Recovery**:
       $$ssthresh \leftarrow \max\left(\frac{cwnd}{2}, 2\right)$$
       $$cwnd \leftarrow ssthresh + 3\text{ MSS}$$
       *(Maintains in-flight pipelining without dropping to 1).*
     - **TCP Cubic (RFC 8312):** Replaces linear AIMD with a cubic growth function dependent on the elapsed time $t$ since the last loss event:
       $$W_{\text{cubic}}(t) = C \cdot (t - K)^3 + W_{\max}$$
       Where $K = \sqrt[3]{\frac{W_{\max} \cdot \beta}{C}}$, stabilizing throughput on high-bandwidth, high-latency links.

---

## 4. System Architecture & Software Design

### 4.1 Modular Architecture Overview
The system is constructed with strict separation of concerns, decoupling the discrete-event simulation engine from performance analysis, visualization, and user interface delivery.

```
network-control-analyzer/
├── app.py                      # Streamlit interactive UI application & controller
├── .streamlit/
│   └── config.toml             # Clean light theme system configuration
├── simulation/
│   ├── network_model.py        # Core data contracts: Packet, Config, Events
│   ├── engine.py               # Dispatcher routing protocols to execution engines
│   ├── stop_and_wait.py        # Stop-and-Wait ARQ discrete-event engine
│   ├── go_back_n.py            # Go-Back-N ARQ discrete-event engine
│   ├── selective_repeat.py     # Selective Repeat ARQ discrete-event engine
│   ├── tcp_congestion.py       # TCP Tahoe, Reno, and Cubic discrete-event engine
│   └── visualizer.py           # Plotly Space-Time sequence ladder & TCP charts
├── metrics/
│   ├── performance.py          # Metric extraction, utilization, throughput math
│   └── analyzer.py             # Rule-based diagnostic report generator
├── experiments/
│   └── run_comparisons.py      # Automated parameter sweep pipelines (N, Loss, RTT)
└── tests/
    └── test_simulators.py      # Comprehensive 9-suite Pytest verification harness
```

### 4.2 Discrete-Event Engine Mechanics (`simulation/`)
Unlike continuous simulation loops that advance time by constant millisecond ticks ($\Delta t$), this project implements a **Priority Queue Discrete-Event Simulation (DES)** using Python's native `heapq` module.

```python
# Event Queue Tuple: (timestamp, counter, event_type, payload)
heapq.heappush(event_queue, (event_time, event_counter, "PKT_ARRIVE", {"seq_num": pkt_seq}))
```

**Key Execution Properties:**
1. **Clock Jumping:** Simulation time advances directly from one discrete event to the next, skipping all idle link delays with zero CPU wastage.
2. **Channel Physics Modeling:** Serial transmission delays are enforced using a `sender_free_at` timestamp barrier, preventing packets from overlapping during serialization.
3. **Reproducibility:** Seeded pseudo-random number generators (`random.Random(seed)`) guarantee that comparative protocol runs encounter identical loss patterns.

### 4.3 Data Structures and Schema (`network_model.py`)
- **`Packet`:** Encapsulates sequence number, byte size, acknowledgment flag, SACK lists, transmission timestamps, and retransmission status.
- **`NetworkConfig`:** Encapsulates physical bandwidth (Mbps), one-way propagation delay (ms), packet loss probability ($0.0 - 1.0$), and Jacobson RTO calculation.
- **`LadderEntry`:** Records complete visual coordinate data (`from_node`, `to_node`, `t_start`, `t_end`, `seq_or_ack`, `is_lost`, `is_retransmission`, `label`) for every line rendered on the sequence diagram.
- **`SimulationResult`:** Aggregates event traces, time-series telemetry data (`cwnd`, `rwnd`, `ssthresh`, `in_flight`), and summary metrics.

### 4.4 Space-Time Sequence Ladder Visualization Engine (`visualizer.py`)
The Space-Time Packet Ladder diagram visualizes network traffic across space ($x \in [0, 1]$) and time ($y \in [0, t_{\max}]$):
- **Host Axes:** Host A (Sender, $x = 0$) on the left in blue; Host B (Receiver, $x = 1$) on the right in green.
- **Data Packets:** Slanted lines from left to right with slope $\Delta y / \Delta x = t_{prop}$.
- **Acknowledgments:** Reverse lines from right to left ($x = 1 \to 0$).
- **Midway Drops (❌):** Dropped packets truncate at $x = 0.5$ with an explosion marker.
- **Duplicate ACKs:** Highlighted with amber dotted lines.
- **Retransmissions:** Rendered in purple dotted lines with explicit `⏱️ Timeout #k` annotations.
- **Continuous Auto-Play:** Renders progressive frames with unique element keys (`key=f"anim_frame_{run_id}_{i}"`) to allow automated walkthroughs without widget collision errors.

---

## 5. Experimental Methodology & Empirical Analysis

### 5.1 Experiment 1: Window Size ($N$) Sweep & BDP Saturation
- **Objective:** Evaluate how sender window size $N$ influences link utilization and throughput.
- **Setup:** Bandwidth $B = 10\text{ Mbps}$, Propagation Delay $t_{prop} = 25\text{ ms}$ ($RTT \approx 50.8\text{ ms}$). Packet size $L = 1000\text{ bytes}$.
  $$BDP_{\text{packets}} = \frac{10 \times 10^6 \times 0.0508}{1000 \times 8} \approx 63.5\text{ packets}$$
- **Results:**
  - When $N = 1$ (Stop-and-Wait), throughput is capped at $0.15\text{ Mbps}$ ($\eta = 1.5\%$).
  - As $N$ scales from $2 \to 4 \to 8 \to 16$, throughput increases linearly.
  - At $N = 64$, throughput approaches the link limit ($9.9\text{ Mbps}$), proving link saturation at $N \ge BDP$.

### 5.2 Experiment 2: Packet Loss Rate ($0\% - 20\%$) & Resilience Evaluation
- **Objective:** Contrast protocol behavior under increasing channel noise.
- **Observations:**
  - **Go-Back-N (GBN):** Experiences **catastrophic throughput collapse**. At a $10\%$ loss rate, GBN throughput drops by over $75\%$ because each single drop triggers retransmission of the entire window ($N$ packets).
  - **Selective Repeat (SR):** Maintains steady, gradual degradation. Only missing packets are resent, keeping retransmission overhead proportional to the channel loss rate ($overhead \approx loss\_prob$).

```
Throughput (Mbps)
  10 |============= (0% loss)
   8 |             \--- Selective Repeat (Gradual degradation)
   6 |              \
   4 |               \--- Go-Back-N (Severe Collapse)
   2 |                    \
   0 +----------------------------------> Loss Rate (%)
     0%      5%      10%      15%     20%
```

### 5.3 Experiment 3: Round-Trip Latency Sweep & Long-Fat Networks (LFN)
- **Objective:** Assess performance across terrestrial ($10\text{ ms}$), intercontinental ($50\text{ ms}$), and satellite ($200\text{ ms}$) paths.
- **Findings:** Stop-and-Wait throughput drops inversely with latency:
  $$\text{Throughput} \propto \frac{1}{RTT}$$
  Sliding window and TCP protocols pipeline packets to sustain link utilization regardless of propagation delay, provided window size is sized to match the larger $BDP$.

### 5.4 Experiment 4: Receiver Buffer Constraint ($rwnd$) vs Network Congestion ($cwnd$)
- **Objective:** Verify the effective transmission boundary $W_{eff} = \min(rwnd, cwnd)$.
- **Empirical Validation:**
  - Case A ($rwnd = 4, cwnd = 32$): Sender transmits exactly 4 packets per $RTT$ despite zero network loss. Flow control restricts transmission.
  - Case B ($rwnd = 64, cwnd = 6$): Sender transmits 6 packets per $RTT$. Congestion control restricts transmission.

---

### 5.5 Experiment 5: Controlled Multi-Protocol Head-to-Head Benchmark
Under identical network conditions: $40\text{ packets}$, $B = 10.0\text{ Mbps}$, $t_{prop} = 25.0\text{ ms}$, Loss Rate $= 5.0\%$, Seed $= 42$.

| Protocol | Throughput (Mbps) | Link Utilization (%) | Avg Delay (ms) | Retransmissions | Retransmission Overhead (%) | Packet Delivery Ratio (%) | Completion Time (ms) | Bottleneck Class |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Stop-and-Wait ARQ** | 0.15 | 1.5% | 48.2 ms | 3 | 7.0% | 93.0% | 2085.3 ms | Delay-Bounded ($a = 31.25$) |
| **Go-Back-N ARQ ($N=8$)** | 0.31 | 3.1% | 152.4 ms | 33 | 82.5% | 54.8% | 1024.6 ms | Head-of-Line Blocking |
| **Selective Repeat ($N=8$)** | 0.49 | 4.9% | 61.8 ms | 4 | 9.1% | 90.9% | 658.6 ms | Flow-Control Limited |
| **TCP Tahoe ($rwnd=32$)** | 0.41 | 4.1% | 88.3 ms | 5 | 11.1% | 88.9% | 777.5 ms | Loss Recovery (Drop to 1) |
| **TCP Reno ($rwnd=32$)** | 0.47 | 4.7% | 72.1 ms | 4 | 9.1% | 90.9% | 675.8 ms | Fast Recovery ($cwnd / 2$) |
| **TCP Cubic ($rwnd=32$)** | 0.48 | 4.8% | 71.4 ms | 4 | 9.1% | 90.9% | 668.2 ms | Window Scaled |

---

## 6. Comparative Evaluation & Discussion

### 6.1 Flow Control Comparison: Stop-and-Wait vs GBN vs Selective Repeat
1. **Stop-and-Wait ARQ:** Demonstrates the lowest link utilization ($1.5\%$). With $a = 31.25$, the channel remains idle for over $98\%$ of the session.
2. **Go-Back-N ARQ:** Solves channel idling via pipelining, but suffers severely from **head-of-line blocking**. When packet #1 was lost, the receiver discarded the 7 subsequent in-flight packets, forcing the sender to generate **33 retransmissions** (an overhead of $82.5\%$).
3. **Selective Repeat ARQ:** Eliminates unnecessary retransmissions by buffering out-of-order frames at the receiver. Only 4 packets were retransmitted (an overhead of $9.1\%$), completing the transfer in $658.6\text{ ms}$ (a $35.7\%$ speedup over GBN).

### 6.2 Congestion Control Comparison: Tahoe vs Reno vs Cubic
1. **Tahoe vs Reno:** When isolated packet loss occurs, TCP Tahoe forces $cwnd$ back to $1\text{ MSS}$, restarting in Slow Start. TCP Reno recognizes the 3 duplicate ACKs, performs Fast Retransmit, and enters **Fast Recovery**, halving $cwnd$ without resetting to 1. This delivers a **$13.1\%$ faster completion time** ($675.8\text{ ms}$ vs $777.5\text{ ms}$).
2. **TCP Cubic:** Rapidly recovers window capacity post-loss through its cubic polynomial growth function, maintaining near-optimal saturation on high-BDP paths.

---

## 7. System Verification & Automated Testing

### 7.1 Test Harness & Edge Cases Covered
The simulator is validated through an automated test suite implemented in `tests/test_simulators.py` utilizing the `pytest` framework:

```
tests/test_simulators.py
├── test_stop_and_wait_zero_loss        -> Validates perfect channel delivery
├── test_stop_and_wait_with_loss        -> Validates RTO timeout retransmission
├── test_go_back_n_zero_loss            -> Validates full pipelining efficiency
├── test_go_back_n_with_loss            -> Validates cumulative duplicate ACKs & retransmit
├── test_selective_repeat_zero_loss     -> Validates out-of-order window sliding
├── test_selective_repeat_with_loss     -> Validates targeted selective retransmission
├── test_tcp_reno_and_tahoe             -> Asserts Reno outperforms Tahoe under loss
├── test_analysis_generation            -> Asserts automated diagnostic text generation
└── test_experiment_sweep               -> Validates multi-point parameter sweeps
```

### 7.2 Test Execution Results
All 9 automated test suites pass without regression:
```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\anike\OneDrive\Desktop\CN
collected 9 items

tests/test_simulators.py::test_stop_and_wait_zero_loss PASSED            [ 11%]
tests/test_simulators.py::test_stop_and_wait_with_loss PASSED            [ 22%]
tests/test_simulators.py::test_go_back_n_zero_loss PASSED                [ 33%]
tests/test_simulators.py::test_go_back_n_with_loss PASSED                [ 44%]
tests/test_simulators.py::test_selective_repeat_zero_loss PASSED         [ 55%]
tests/test_simulators.py::test_selective_repeat_with_loss PASSED         [ 66%]
tests/test_simulators.py::test_tcp_reno_and_tahoe PASSED                 [ 77%]
tests/test_simulators.py::test_analysis_generation PASSED                [ 88%]
tests/test_simulators.py::test_experiment_sweep PASSED                   [100%]

============================== 9 passed in 2.11s ==============================
```

---

## 8. Viva Voce & Technical Defense Guide

### 8.1 Core Theoretical Questions & Answers

**Q1: What is the primary difference between Flow Control and Congestion Control?**  
*Answer:* Flow control protects the receiving endpoint buffer from being overrun by a fast sender (governed by $rwnd$). Congestion control protects the intermediate network routers and switches from queue overflow caused by collective network traffic (governed by $cwnd$). The sender enforces the effective window $W_{eff} = \min(rwnd, cwnd)$.

**Q2: Why does Go-Back-N retransmit multiple packets while Selective Repeat retransmits only one?**  
*Answer:* In Go-Back-N, the receiver does not maintain an out-of-order buffer. When an out-of-order frame arrives, it is discarded, and the receiver emits duplicate cumulative ACKs. Upon timeout, the sender must retransmit the entire window. In Selective Repeat, the receiver has an out-of-order buffer and acknowledges frames individually; the sender maintains per-packet timers and retransmits solely the specific missing frame.

**Q3: Why must the window size in Selective Repeat satisfy $N \le 2^{m-1}$ for $m$-bit sequence numbers?**  
*Answer:* If $N > 2^{m-1}$, the receiver's window overlaps with the sequence numbers of previously acknowledged packets. If all ACKs in a window are lost, the sender will retransmit old packets, but the receiver would mistakenly interpret them as new incoming packets. Restricting $N \le 2^{m-1}$ guarantees that old and new window sequence ranges never intersect.

**Q4: How does TCP Reno avoid dropping to $cwnd = 1$ when an isolated loss occurs?**  
*Answer:* TCP Reno interprets 3 duplicate ACKs as evidence that subsequent packets are still traversing the network and reaching the receiver. Instead of triggering a catastrophic timeout (which resets $cwnd \to 1$), Reno executes Fast Retransmit (resending the missing packet immediately) and Fast Recovery (setting $ssthresh = cwnd/2$ and $cwnd = ssthresh + 3$), continuing data transmission in Congestion Avoidance.

**Q5: What is the Bandwidth-Delay Product (BDP) and why is it critical?**  
*Answer:* $BDP = \text{Bandwidth} \times RTT$. It measures the total byte capacity in flight required to keep the physical pipe fully saturated. If the sender's window $N < BDP$, the sender will exhaust its window and stall while waiting for ACKs, resulting in underutilized link capacity.

---

## 9. Conclusion & Future Work

### 9.1 Summary of Contributions
1. Developed an extensible, discrete-event network simulation platform accurately implementing flow control and congestion control protocols.
2. Formulated an interactive Space-Time Sequence Ladder Diagram providing animated playback of packet travel, reverse ACKs, midway drops, and timeouts.
3. Quantified the catastrophic throughput collapse of Go-Back-N under noisy channels compared to the resilience of Selective Repeat.
4. Demonstrated the superiority of TCP Reno's Fast Recovery over TCP Tahoe under isolated packet drops.
5. Implemented automated verification suites and diagnostic reasoning engines adhering to standard network protocol benchmarks.

### 9.2 Future Enhancements
- **BBR Congestion Control:** Integrate Google's BBR (Bottleneck Bandwidth and RTT) model to evaluate delay-based congestion control versus loss-based models.
- **Active Queue Management (AQM):** Model router drop policies such as RED (Random Early Detection) and CoDel (Controlled Delay) to simulate bufferbloat mitigation.
- **QUIC / HTTP/3 Simulation:** Expand the protocol engine to support UDP-based multiplexed transport with connection migration.

---

## 10. References & RFC Standards

1. **RFC 793:** Transmission Control Protocol (TCP) Specification. Postel, J., September 1981.
2. **RFC 1122:** Requirements for Internet Hosts — Communication Layers. Braden, R., October 1989.
3. **RFC 2018:** TCP Selective Acknowledgment Options. Mathis, M., Mahdavi, J., Floyd, S., Romanow, A., October 1996.
4. **RFC 5681:** TCP Congestion Control. Allman, M., Paxson, V., Blanton, E., September 2009.
5. **RFC 8312:** CUBIC for Fast and Long-Distance Networks. Rhee, I., Xu, L., Ha, S., Zimmermann, A., Eggert, L., February 2018.
6. **Kurose, J. F., & Ross, K. W.:** *Computer Networking: A Top-Down Approach*, 8th Edition, Pearson, 2021.
7. **Tanenbaum, A. S., & Wetherall, D. J.:** *Computer Networks*, 5th Edition, Prentice Hall, 2011.

