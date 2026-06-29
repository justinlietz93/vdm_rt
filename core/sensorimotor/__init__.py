"""
Hardware-agnostic sensorimotor structures.

Device translation belongs in ``vdm_rt.io``. This package only records sparse
fixed-basis activity, trace pressure, release state, and pairing handles.
"""

from vdm_rt.core.sensorimotor.efference.trace import EfferenceTraceController

__all__ = ["EfferenceTraceController"]
