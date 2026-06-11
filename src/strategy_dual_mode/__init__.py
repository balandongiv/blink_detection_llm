"""Dual-mode epoch blink detector: Module A (pyblinker normal) + Module B (long closure)."""
from src.strategy_dual_mode.runner import LONG_THRESHOLD_S, run_dual_mode_epoch_pipeline

__all__ = ["run_dual_mode_epoch_pipeline", "LONG_THRESHOLD_S"]
