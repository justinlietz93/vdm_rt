"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import numpy as np

def compute_metrics(connectome):
   """
   Rule Ref: Blueprint Rule 4.1 (Pathology Detection Mechanisms)
   - Adds connectome_entropy to support Active Domain Cartography (Rule 7) scheduling.
   - Prefers connectome.connectome_entropy() when available, falling back to local function.
   """
   # TODO: replace scan-derived metric calls with SparseConnectome.metrics_snapshot()
   # and event-spine reducer outputs after parity tests pass.
   # Prefer a connectome-native entropy calculator when available.
   try:
       h = float(connectome.connectome_entropy())
   except Exception:
       h = float(connectome_entropy(connectome))
   return {
       "avg_weight": float(connectome.W.mean()),
       "active_synapses": int(connectome.active_edge_count()),
       "cohesion_components": int(connectome.connected_components()),
       "complexity_cycles": int(connectome.cyclomatic_complexity()),
       "connectome_entropy": h,
   }

def connectome_entropy(connectome) -> float:
   """
   Rule Ref: Blueprint Rule 4.1 - Global Pathological Structure (Connectome Entropy)
   Formula: H = -Σ p_i log(p_i), where p is degree distribution of the active subgraph.
   Returns 0.0 when no active edges are present.
   """
   # Active, undirected mask
   mask = (connectome.E > connectome.threshold) & (connectome.A == 1)
   # Degree per node (count upper+lower symmetrically from full mask)
   deg = mask.sum(axis=1).astype(np.float64)
   total = deg.sum()
   if total <= 0:
       return 0.0
   p = deg / total
   # Numerical stability
   p = np.clip(p, 1e-12, 1.0)
   return float(-(p * np.log(p)).sum())
