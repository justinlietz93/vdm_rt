"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

import os
import json
import numpy as np
from typing import List, Tuple

from vdm_rt.core.sparse_connectome import SparseConnectome

# HDF5 dependency gate for runtime checkpoints.
try:
    import h5py  # type: ignore
    HAVE_H5 = True
except Exception:
    HAVE_H5 = False

from vdm_rt.core.adc import Territory as ADCTerritory, Boundary as ADCBoundary, _EWMA as _ADC_EWMA


def _adj_to_csr(adj: List[np.ndarray], N: int) -> Tuple[np.ndarray, np.ndarray]:
    """Convert neighbor-lists (sparse adjacency) to CSR arrays: row_ptr, col_idx."""
    row_ptr = np.zeros(N + 1, dtype=np.int64)
    total = 0
    for i in range(N):
        deg = int(adj[i].size)
        row_ptr[i] = total
        total += deg
    row_ptr[N] = total
    col_idx = np.zeros(total, dtype=np.int32)
    pos = 0
    for i in range(N):
        nbrs = adj[i]
        if nbrs.size:
            k = nbrs.size
            col_idx[pos : pos + k] = nbrs.astype(np.int32, copy=False)
            pos += k
    return row_ptr, col_idx


def _csr_to_adj(row_ptr: np.ndarray, col_idx: np.ndarray, N: int) -> List[np.ndarray]:
    """Convert CSR arrays to neighbor-lists (sparse adjacency)."""
    adj = []
    for i in range(N):
        start = int(row_ptr[i])
        end = int(row_ptr[i + 1])
        if end > start:
            adj.append(col_idx[start:end].astype(np.int32, copy=False))
        else:
            adj.append(np.zeros(0, dtype=np.int32))
    return adj


# -----------------------
# ADC (de)serialization
# -----------------------
def _ewma_to_dict(w) -> dict:
    try:
        return {
            "alpha": float(getattr(w, "alpha", 0.15)),
            "mean": float(getattr(w, "mean", 0.0)),
            "var": float(getattr(w, "var", 0.0)),
            "init": bool(getattr(w, "init", False)),
        }
    except Exception:
        return {"alpha": 0.15, "mean": 0.0, "var": 0.0, "init": False}


def _ewma_from_dict(d):
    try:
        a = float(d.get("alpha", 0.15))
        m = float(d.get("mean", 0.0))
        v = float(d.get("var", 0.0))
        ini = bool(d.get("init", False))
        if _ADC_EWMA is not None:
            return _ADC_EWMA(alpha=a, mean=m, var=v, init=ini)  # type: ignore
    except Exception:
        pass
    if _ADC_EWMA is not None:
        return _ADC_EWMA(alpha=0.15)  # type: ignore
    return None


def _adc_to_dict(adc) -> dict:
    """Serialize ADC internals into a JSON-friendly dict."""
    try:
        terr = []
        for key, t in getattr(adc, "_territories", {}).items():
            try:
                dom, cov = key
            except Exception:
                dom, cov = "", 0
            terr.append({
                "key": [str(dom), int(cov)],
                "id": int(getattr(t, "id", 0)),
                "mass": float(getattr(t, "mass", 0.0)),
                "conf": float(getattr(t, "conf", 0.0)),
                "ttl": int(getattr(t, "ttl", 0)),
                "w_stats": _ewma_to_dict(getattr(t, "w_stats", None)),
                "s_stats": _ewma_to_dict(getattr(t, "s_stats", None)),
            })
        bounds = []
        for key, b in getattr(adc, "_boundaries", {}).items():
            try:
                a, c = key
            except Exception:
                a, c = 0, 0
            bounds.append({
                "a": int(a),
                "b": int(c),
                "ttl": int(getattr(b, "ttl", 0)),
                "cut_stats": _ewma_to_dict(getattr(b, "cut_stats", None)),
                "churn": _ewma_to_dict(getattr(b, "churn", None)),
            })
        fcnt = []
        for key, cnt in getattr(adc, "_frontier_counter", {}).items():
            try:
                dom, cov = key
            except Exception:
                dom, cov = "", 0
            fcnt.append({
                "key": [str(dom), int(cov)],
                "count": int(cnt),
            })
        return {
            "id_seq": int(getattr(adc, "_id_seq", 1)),
            "territories": terr,
            "boundaries": bounds,
            "frontier_counter": fcnt,
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to serialize required ADC checkpoint state: {exc}") from exc


def _adc_load_from_dict(adc, state: dict) -> None:
    """Populate ADC internals from a previously serialized dict."""
    if adc is None:
        raise RuntimeError("ADC is required when loading runtime checkpoints")
    if not isinstance(state, dict):
        raise ValueError("Checkpoint ADC state must be a JSON object")
    try:
        terr_d = {}
        max_id = 0
        for t in state.get("territories", []):
            try:
                dom, cov = t.get("key", ["", 0])
                tid = int(t.get("id", 0))
                max_id = max(max_id, tid)
                wj = t.get("w_stats", {})
                sj = t.get("s_stats", {})
                w_stats = _ewma_from_dict(wj)
                s_stats = _ewma_from_dict(sj)
                terr = ADCTerritory(
                    key=(str(dom), int(cov)),
                    id=tid,
                    mass=float(t.get("mass", 0.0)),
                    conf=float(t.get("conf", 0.0)),
                    ttl=int(t.get("ttl", 0)),
                    w_stats=w_stats if w_stats is not None else _ADC_EWMA(alpha=0.15),
                    s_stats=s_stats if s_stats is not None else _ADC_EWMA(alpha=0.15),
                )
                terr_d[(str(dom), int(cov))] = terr
            except Exception:
                continue
        bnd_d = {}
        for b in state.get("boundaries", []):
            try:
                a = int(b.get("a", 0))
                c = int(b.get("b", 0))
                cut = _ewma_from_dict(b.get("cut_stats", {}))
                chrn = _ewma_from_dict(b.get("churn", {}))
                bnd = ADCBoundary(
                    a=min(a, c),
                    b=max(a, c),
                    cut_stats=cut if cut is not None else _ADC_EWMA(alpha=0.2),
                    churn=chrn if chrn is not None else _ADC_EWMA(alpha=0.2),
                    ttl=int(b.get("ttl", 0)),
                )
                bnd_d[(min(a, c), max(a, c))] = bnd
            except Exception:
                continue
        fcnt = {}
        for fc in state.get("frontier_counter", []):
            try:
                dom, cov = fc.get("key", ["", 0])
                fcnt[(str(dom), int(cov))] = int(fc.get("count", 0))
            except Exception:
                continue
        setattr(adc, "_territories", terr_d)
        setattr(adc, "_boundaries", bnd_d)
        setattr(adc, "_frontier_counter", fcnt)
        try:
            id_seq = int(state.get("id_seq", max_id + 1))
        except Exception:
            id_seq = max_id + 1
        setattr(adc, "_id_seq", max(1, id_seq))
    except Exception as exc:
        raise RuntimeError(f"Failed to load required ADC checkpoint state: {exc}") from exc


def _require_adc(adc):
    if adc is None:
        raise RuntimeError("ADC is required for runtime checkpoint save/load")
    return adc


def _require_sparse_connectome(connectome):
    if not isinstance(connectome, SparseConnectome):
        raise TypeError("Runtime checkpoints require SparseConnectome")
    return connectome


def save_checkpoint(run_dir: str, step: int, connectome, fmt: str = "h5", *, adc) -> str:
    """
    Save sparse runtime state (engram).

    Args:
        run_dir: run directory
        step: tick index
        connectome: SparseConnectome
        fmt: "h5"
        adc: ADC instance to persist alongside the connectome; required
    """
    fmt = str(fmt or "h5").lower()
    if fmt != "h5":
        raise ValueError(f"Unsupported checkpoint format {fmt!r}; runtime checkpoints must be h5")
    adc = _require_adc(adc)

    if not HAVE_H5:
        raise RuntimeError(
            "h5py is required for H5 checkpoints. Install runtime requirements with "
            "`pip install -r requirements.txt`."
        )

    connectome = _require_sparse_connectome(connectome)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, f"state_{step}.h5")
    _save_h5(path, connectome, adc)
    return path


def _save_h5(path: str, connectome, adc):
    adc = _require_adc(adc)
    connectome = _require_sparse_connectome(connectome)
    with h5py.File(path, "w") as f:
        # Metadata as attributes
        f.attrs["backend"] = "sparse"
        f.attrs["N"] = int(connectome.N)
        f.attrs["k"] = int(getattr(connectome, "k", 0))
        f.attrs["threshold"] = float(getattr(connectome, "threshold", 0.0))
        f.attrs["lambda_omega"] = float(getattr(connectome, "lambda_omega", 0.0))
        f.attrs["dtype"] = "float32"

        row_ptr, col_idx = _adj_to_csr(connectome.adj, int(connectome.N))
        g = f.create_group("sparse")
        g.create_dataset("W", data=connectome.W.astype(np.float32, copy=False), compression="gzip")
        g.create_dataset("row_ptr", data=row_ptr, compression="gzip")
        g.create_dataset("col_idx", data=col_idx, compression="gzip")

        state_json = json.dumps(_adc_to_dict(adc))
        f.create_dataset("adc_json", data=state_json, dtype=h5py.string_dtype(encoding="utf-8"))


def load_engram(path: str, connectome, *, adc) -> None:
    """
    Load an engram from an H5 checkpoint and populate the provided connectome instance.
    ADC state is required and is populated alongside the connectome.

    - Sparse: sets W, adj (neighbor lists), threshold
    - ADC: territories, boundaries, counters
    """
    p = str(path)
    if not p.lower().endswith(".h5"):
        raise ValueError("Engram checkpoints must be H5 files ending in .h5")
    adc = _require_adc(adc)
    if not HAVE_H5:
        raise RuntimeError("h5py not installed but .h5 requested")
    _load_h5(p, connectome, adc)


def _apply_common_attrs(meta: dict, connectome):
    # Resize N if needed (safe for our numpy arrays here)
    N = int(meta.get("N", connectome.N))
    connectome.N = N
    # threshold, lambda_omega if present
    if "threshold" in meta:
        connectome.threshold = float(meta["threshold"])
    if "lambda_omega" in meta:
        connectome.lambda_omega = float(meta["lambda_omega"])


def _load_h5(path: str, connectome, adc):
    adc = _require_adc(adc)
    connectome = _require_sparse_connectome(connectome)
    with h5py.File(path, "r") as f:
        ds = f.get("adc_json", None)
        if ds is None:
            raise ValueError("Checkpoint is missing required ADC state dataset 'adc_json'")
        raw = ds[()]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        adc_state = json.loads(raw)

        backend = f.attrs.get("backend", "")
        if isinstance(backend, bytes):
            backend = backend.decode("utf-8", errors="ignore")
        if str(backend) != "sparse":
            raise ValueError(f"Unsupported checkpoint backend {backend!r}; runtime checkpoints must be sparse")
        meta = {
            "N": int(f.attrs.get("N", connectome.N)),
            "threshold": float(f.attrs.get("threshold", getattr(connectome, "threshold", 0.0))),
            "lambda_omega": float(f.attrs.get("lambda_omega", getattr(connectome, "lambda_omega", 0.0))),
        }
        _apply_common_attrs(meta, connectome)

        g = f["sparse"]
        connectome.W = g["W"][...].astype(np.float32, copy=False)
        row_ptr = g["row_ptr"][...]
        col_idx = g["col_idx"][...]
        connectome.adj = _csr_to_adj(row_ptr, col_idx, int(connectome.N))

        _adc_load_from_dict(adc, adc_state)
