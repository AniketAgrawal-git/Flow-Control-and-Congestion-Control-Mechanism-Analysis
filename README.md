# Analysis of Flow Control and Congestion Control Mechanisms
### A Unified Discrete-Event Network Simulator, Performance Benchmark, and Educational Platform

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.64.0-FF4B4B.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75.svg)](https://plotly.com/)
[![Tests](https://img.shields.io/badge/Pytest-9%2F9%20Passing-brightgreen.svg)](https://pytest.org/)

---

## 📖 Overview

This repository contains the complete implementation of the Computer Networks project **"Analysis of Flow Control and Congestion Control Mechanisms"**.

Rather than relying purely on static textbook equations, this project implements a production-grade **Discrete-Event Simulation (DES)** engine in Python that simulates the physical laws of network communication: bit serialization delay ($t_{trans}$), physical medium propagation delay ($t_{prop}$), channel packet loss, independent reverse acknowledgment paths, out-of-order buffering, and retransmission timeouts ($RTO$).

### Supported Protocols:
- **Flow Control (Protecting the Receiver):**
  - **Stop-and-Wait ARQ** ($N=1$)
  - **Go-Back-N ARQ** ($N > 1$, Cumulative ACKs, Window Retransmission)
  - **Selective Repeat ARQ** ($N > 1$, Individual Timers, Out-of-Order Receiver Buffer, Selective ACKs)
- **Congestion Control (Protecting the Network Link):**
  - **TCP Tahoe** (Slow Start, AIMD Congestion Avoidance, Fast Retransmit with Drop to $cwnd=1$)
  - **TCP Reno** (Fast Recovery via RFC 5681: Halves $cwnd$ without dropping to 1)
  - **TCP Cubic** (Cubic window scaling function via RFC 8312)

---

## 🚀 Key Features

1. **📡 Live Animated Space-Time Packet Ladder Diagram:**
   - Visual sequence diagram tracing packet departures, arrivals, midway channel drops (❌), duplicate ACKs, and timeouts.
   - Continuous **`▶️ Auto-Play`** playback with adjustable speed (`1x`, `2x`, `0.5x`).
   - Granular step controls: `⏮️ Start`, `◀️ Prev`, `▶️ Next`, `⚡ Loss` (quick-jump to drops/timeouts), `⏩ End`.
   - `Show Complete Trace (All Packets)` instant view option.

2. **⚖️ Multi-Protocol Head-to-Head Benchmarking:**
   - Execute multiple protocols under strictly identical physical channel conditions (same bandwidth, RTT, loss rate, and pseudo-random seed).
   - Generates consolidated comparative metrics: Throughput (Mbps), Link Utilization (%), Average Delay (ms), Retransmissions, Retransmission Overhead (%), and Completion Time (ms).

3. **🔬 Automated Parameter Sweeps:**
   - **Experiment 1:** Window Size ($N$) Sweep & Link Saturation ($BDP$).
   - **Experiment 2:** Packet Loss Rate ($0\% - 20\%$) Sweep & Resilience Analysis.
   - **Experiment 3:** Round-Trip Latency Sweep ($10\text{ ms} - 200\text{ ms}$) across terrestrial and satellite links.
   - **Experiment 4:** Receiver Flow Control Constraint ($rwnd$) vs Network Congestion ($cwnd$).

4. **🧠 Rule-Based Diagnostic Reasoning Engine:**
   - Automatically generates written academic evaluations explaining why one algorithm outperformed another based on measured metrics.

---

## 🛠️ Project Structure

```
CN/
├── app.py                      # Streamlit interactive UI application & controller
├── .streamlit/
│   └── config.toml             # System light theme configuration
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
│   └── run_comparisons.py      # Automated parameter sweep pipelines
├── tests/
│   └── test_simulators.py      # Pytest verification test suite
├── PROJECT_REPORT.md           # Full academic project report & viva guide
└── README.md                   # Repository documentation
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Or manually:
pip install streamlit plotly pandas pytest
```

### 2. Launch the Web Application
```bash
streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

### 3. Run Automated Unit Tests
```bash
python -m pytest tests -v
```
All 9 unit tests test edge cases, out-of-order buffering, and verify that Reno outperforms Tahoe under loss.

---

## 📄 Complete Project Report
For the complete academic submission report, theory, mathematical proofs, experimental results, and viva defense questions, refer to [PROJECT_REPORT.md](file:///c:/Users/anike/OneDrive/Desktop/CN/PROJECT_REPORT.md).

