"""
Metrics package initialization.
"""

from metrics.performance import extract_metrics_dataframe, calculate_speedup_ratio
from metrics.analyzer import generate_single_protocol_analysis, generate_comparative_analysis

__all__ = [
    "extract_metrics_dataframe",
    "calculate_speedup_ratio",
    "generate_single_protocol_analysis",
    "generate_comparative_analysis"
]

