"""
Copyright @ 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.

This research is protected under a dual-license to foster open academic
research while ensuring commercial applications are aligned with the project's ethical principles. Commercial use requires written permission from Justin K. Lietz.
See LICENSE file for full terms.
"""

# NOTE: This module acts as a thin façade over the runtime and core layers.
# Behavior is preserved; external imports remain stable. Core loop has moved to [loop.run_loop()](vdm_rt/runtime/loop.py:40).
import time, os, sys

# Deprecation notice (documentation-only):
# - Inline orchestrator logic inside Nexus is deprecated; equivalent functionality lives in runtime/*.
# - External integrations continue to import Nexus and make_parser from this module (no change required).
# - No functional changes: IDF remains composer/telemetry-only; SIE/ADC/connectome unaffected.
# - Event-driven metrics and void cold scouts are controlled by config/*.toml.
from collections import deque
from .config import config_bool, config_float, config_int, config_str
from .utils.logging_setup import get_logger
from .io.ute import UTE
from .io.utd import UTD
# emitters moved to runtime.emitters.initialize_emitters
from .core import text_utils
from .core.metrics import StreamingZEMA
from .core.void_dynamics_adapter import get_domain_modulation
from .core.sie import SelfImprovementEngine
from .core.bus import AnnounceBus
from .core.adc import ADC
# Modularized lexicon/phrase store (behavior-preserving)
from .io.lexicon.store import (
    load_phrase_templates as _lxn_load_phrases,
    load_lexicon as _lxn_load,
    save_lexicon as _lxn_save,
)
from .runtime.telemetry import macro_why_base as _telemetry_why_base
# Event-driven metrics seam (feature-flagged; pure core + adapter)
from .core.proprioception.events import EventDrivenMetrics as _EvtMetrics
from .runtime.emitters import initialize_emitters as _init_emitters
from .runtime.helpers import register_macro_board as _reg_macro_board, maybe_load_engram as _maybe_load_engram, derive_start_step as _derive_start_step
from .runtime.loop import run_loop as _run_loop
# Cognition seams (Phase 3 move-only; behavior-preserving)
from .io.cognition.stimulus import symbols_to_indices as _stim_symbols_to_indices
from .io.cognition.composer import compose_say_text as _compose_say_text_impl
# Core signals seam (B1 detector apply)
try:
    from .core.control_server import ControlServer  # optional UI
except Exception:
    ControlServer = None


def _cfg_int(value, key: str, default: int) -> int:
    return config_int(key, default) if value is None else int(value)


def _cfg_float(value, key: str, default: float) -> float:
    return config_float(key, default) if value is None else float(value)


def _cfg_bool(value, key: str, default: bool) -> bool:
    return config_bool(key, default) if value is None else bool(value)


def _cfg_str(value, key: str, default: str) -> str:
    return config_str(key, default) if value is None else str(value)


def _cfg_optional_str(value, key: str) -> str | None:
    if value is not None:
        return str(value)
    configured = config_str(key, "").strip()
    return configured or None


class Nexus:
    def __init__(self, run_dir: str, N: int | None = None, k: int | None = None, hz: int | None = None,
                 domain: str | None = None, use_time_dynamics: bool | None = None,
                 log_every: int | None = None, checkpoint_every: int | None = None, seed: int | None = None,
                 threshold: float | None = None, lambda_omega: float | None = None,
                 candidates: int | None = None, walkers: int | None = None, hops: int | None = None,
                 status_interval: int | None = None, bundle_size: int | None = None,
                 prune_factor: float | None = None, speak_auto: bool | None = None,
                 speak_z: float | None = None, speak_hysteresis: float | None = None,
                 speak_cooldown_ticks: int | None = None, speak_valence_thresh: float | None = None,
                 b1_half_life_ticks: int | None = None, bus_capacity: int | None = None,
                 bus_drain: int | None = None, r_attach: float | None = None,
                 ttl_init: int | None = None, split_patience: int | None = None,
                 stim_group_size: int | None = None, stim_amp: float | None = None,
                 stim_decay: float | None = None, stim_max_symbols: int | None = None,
                 checkpoint_format: str | None = None, checkpoint_keep: int | None = None,
                 load_engram_path: str | None = None, start_control_server: bool | None = None,
                 emergent_macros: bool | None = None):
        self.run_dir = run_dir
        self.N = _cfg_int(N, "launch.neurons", 1000)
        self.k = _cfg_int(k, "launch.k", 12)
        self.hz = _cfg_int(hz, "launch.hz", 10)
        self.dt = 1.0 / max(1, self.hz)
        self.domain = _cfg_str(domain, "launch.domain", "biology_consciousness")
        self.use_time_dynamics = _cfg_bool(use_time_dynamics, "launch.use_time_dynamics", True)
        self.log_every = _cfg_int(log_every, "launch.log_every", 1)
        self.checkpoint_every = _cfg_int(checkpoint_every, "persistence.checkpoint_every", 0)
        self.seed = _cfg_int(seed, "launch.seed", 0)
        self.emergent_macros = _cfg_bool(emergent_macros, "runtime.emergent_macros", False)
        threshold = _cfg_float(threshold, "sparse_connectome.threshold", 0.15)
        lambda_omega = _cfg_float(lambda_omega, "sparse_connectome.lambda_omega", 0.1)
        candidates = _cfg_int(candidates, "sparse_connectome.candidates", 64)
        walkers = _cfg_int(walkers, "sparse_connectome.traversal_walkers", 256)
        hops = _cfg_int(hops, "sparse_connectome.traversal_hops", 3)
        status_interval = _cfg_int(status_interval, "launch.status_interval", 1)
        bundle_size = _cfg_int(bundle_size, "sparse_connectome.bundle_size", 3)
        prune_factor = _cfg_float(prune_factor, "sparse_connectome.prune_factor", 0.10)
        speak_auto = _cfg_bool(speak_auto, "speech.auto", True)
        speak_z = _cfg_float(speak_z, "speech.z", 1.0)
        speak_hysteresis = _cfg_float(speak_hysteresis, "speech.hysteresis", 1.0)
        speak_cooldown_ticks = _cfg_int(speak_cooldown_ticks, "speech.cooldown_ticks", 10)
        speak_valence_thresh = _cfg_float(speak_valence_thresh, "speech.valence_threshold", 0.01)
        b1_half_life_ticks = _cfg_int(b1_half_life_ticks, "speech.b1.half_life_ticks", 50)
        bus_capacity = _cfg_int(bus_capacity, "bus.capacity", 65536)
        bus_drain = _cfg_int(bus_drain, "bus.drain", 2048)
        r_attach = _cfg_float(r_attach, "adc.r_attach", 0.25)
        ttl_init = _cfg_int(ttl_init, "adc.ttl_init", 120)
        split_patience = _cfg_int(split_patience, "adc.split_patience", 6)
        stim_group_size = _cfg_int(stim_group_size, "stimulus.group_size", 4)
        stim_amp = _cfg_float(stim_amp, "stimulus.amp", 0.05)
        stim_decay = _cfg_float(stim_decay, "stimulus.decay", 0.90)
        stim_max_symbols = _cfg_int(stim_max_symbols, "stimulus.max_symbols", 64)
        checkpoint_format = _cfg_str(checkpoint_format, "persistence.checkpoint_format", "h5")
        checkpoint_keep = _cfg_int(checkpoint_keep, "persistence.checkpoint_keep", 5)
        load_engram_path = _cfg_optional_str(load_engram_path, "persistence.load_engram")
        start_control_server = _cfg_bool(start_control_server, "control.server_enabled", False)
        self.cold_head_k = config_int("maps.head_k", 256)
        self.cold_half_life_ticks = config_int("maps.half_life_ticks", 200)
        self.trail_half_life_ticks = config_int("maps.trail_half_life_ticks", 50)
        self.sie_target_var = config_float("sie.target_var", 0.15)

        os.makedirs(self.run_dir, exist_ok=True)
        self.logger = get_logger("nexus", os.path.join(self.run_dir, "events.jsonl"))
        inbox_path = os.path.join(self.run_dir, "chat_inbox.jsonl")
        self.ute = UTE(inbox_path=inbox_path)
        self.utd = UTD(self.run_dir)
        # Macro/Thought emitters (delegated)
        self.emitter, self.thoughts = _init_emitters(self.utd, self.run_dir, why_provider=lambda: self._emit_why())
        # Start local control server only when requested (default: off)
        self._control_server = None
        if bool(start_control_server) and ControlServer is not None:
            try:
                self._control_server = ControlServer(self.run_dir)
                try:
                    self.logger.info("control_server_started", extra={"extra": {"url": getattr(self._control_server, "url", "")}})
                except Exception:
                    pass
            except Exception:
                self._control_server = None
        # Macro board: minimal defaults + optional JSON registry (delegated)
        try:
            _reg_macro_board(self.utd, self.run_dir)
        except Exception:
            pass

        # Phrase templates for 'say' macro and persistent lexicon (for richer sentences)
        self._phrase_templates = []
        try:
            self._phrase_templates = list(_lxn_load_phrases(self.run_dir) or [])
        except Exception:
            # Fail-soft: keep empty; store mirrors legacy behavior
            pass
        # 3) Persistent lexicon (word -> count), learned from inbound text and emissions
        try:
            self._lexicon_path = os.path.join(self.run_dir, 'lexicon.json')
            lx, dc = _lxn_load(self.run_dir)
            self._lexicon = dict(lx or {})
            self._doc_count = int(dc or 0)
        except Exception:
            # Fail-soft: empty lexicon
            self._lexicon = {}
            self._doc_count = 0
            pass

        # N-gram stores for emergent sentence composition (learned from inputs/outputs)
        self._ng2 = {}  # bigram: w1 -> {w2: count}
        self._ng3 = {}  # trigram: (w1,w2) -> {w3: count}

        from vdm_rt.core.sparse_connectome import SparseConnectome

        self.connectome = SparseConnectome(
            N=self.N, k=self.k, seed=self.seed,
            threshold=threshold, lambda_omega=lambda_omega,
            candidates=candidates, traversal_walkers=walkers, traversal_hops=hops,
            bundle_size=bundle_size, prune_factor=prune_factor
        )
        # Load engram if provided (after backend selection)
        # Defer engram loading until after ADC is initialized to avoid spurious errors/logs.
        # The actual load (with logging) happens below after ADC is constructed.
        # Status emission cadence for UTD
        self.status_every = max(1, int(status_interval))
        # Self-Improvement Engine (Rule 3): produces signed total_reward and legacy valence_01
        self.sie = SelfImprovementEngine(self.N)
        # Engram persistence config
        self.checkpoint_every = int(checkpoint_every)
        self.checkpoint_format = str(checkpoint_format).lower()
        self.checkpoint_keep = int(max(0, checkpoint_keep))
        # Text stimulus wiring for symbol→group activation
        self.stim_group_size = int(max(1, stim_group_size))
        self.stim_amp = float(stim_amp)
        self.stim_max_symbols = int(max(1, stim_max_symbols))
        try:
            if hasattr(self.connectome, "_stim_decay"):
                self.connectome._stim_decay = float(stim_decay)
        except Exception:
            pass

        # Self-speak configuration and topology spike detector (tick-based)
        self.speak_auto = bool(speak_auto)
        self.speak_valence_thresh = float(speak_valence_thresh)
        # Persist half-life for void_b1 meter to keep UX consistent with detector.
        # CLI defaults come from config; explicit caller arguments win here.
        self.b1_half_life_ticks = int(max(1, b1_half_life_ticks))
        self.b1_detector = StreamingZEMA(
            half_life_ticks=self.b1_half_life_ticks,
            z_spike=float(speak_z),
            hysteresis=float(speak_hysteresis),
            min_interval_ticks=int(max(1, speak_cooldown_ticks)),
        )
        # Optional event-driven metrics aggregator, controlled by config events.event_metrics.
        self._evt_metrics = None
        if config_bool("events.event_metrics", True):
            try:
                self._evt_metrics = _EvtMetrics(
                    z_half_life_ticks=self.b1_half_life_ticks,
                    z_spike=float(speak_z),
                    hysteresis=float(speak_hysteresis),
                    seed=int(self.seed),
                )
            except Exception:
                self._evt_metrics = None
        # External control plane: phase file and cache (void-faithful: gates only)
        self.phase_file = os.path.join(self.run_dir, "phase.json")
        self._phase = {"phase": 0}
        self._phase_mtime = None
        # Novelty rarity gain (tunable via phase.json under "sie": {"novelty_idf_gain": ...})
        self.novelty_idf_gain = 1.0

        # Announcement bus + ADC (void-walker observations -> incremental map)
        self.bus = AnnounceBus(capacity=int(max(1, bus_capacity)))
        self.bus_drain = int(max(1, bus_drain))
        self.adc = ADC(r_attach=float(r_attach), ttl_init=int(ttl_init), split_patience=int(split_patience))
        # Attach bus to connectome so walkers can publish Observation events
        try:
            self.connectome.bus = self.bus
        except Exception:
            pass

        # If an engram path was provided earlier and ADC is now available, reload including ADC
        try:
            _maybe_load_engram(self, load_engram_path)
        except Exception:
            pass
        # Derive starting step to continue numbering after resume and avoid retention deleting new snapshots
        try:
            self.start_step = int(_derive_start_step(self, load_engram_path))
            try:
                self.logger.info("resume_step", extra={"extra": {"start_step": int(self.start_step)}})
            except Exception:
                pass
        except Exception:
            self.start_step = 0
        self.dom_mod = float(get_domain_modulation(self.domain))
        self.history = []
        # Emitter context (read-only snapshot for why providers)
        self._emit_step = 0
        self._emit_last_metrics = {}
        self._macros_smoke_done = False
        self._thoughts_smoke_done = False
        # Rolling buffer of recent inbound text for composing human-friendly “say” content
        self.recent_text = deque(maxlen=config_int("runtime.buffers.recent_text_maxlen", 256))
        # Track vt_entropy over time for SIE TD proxy (void-native signal)
        self._prev_vt_entropy = None
        self._last_vt_entropy = None

    def _symbols_to_indices(self, text, reverse_map=None):
        """
        Deterministic, stateless symbol→group mapping.

        Delegates to io.cognition.stimulus.symbols_to_indices (behavior-preserving).
        """
        try:
            return _stim_symbols_to_indices(
                str(text),
                int(getattr(self, "stim_group_size", 4)),
                int(getattr(self, "stim_max_symbols", 64)),
                int(self.N),
                reverse_map=reverse_map,
            )
        except Exception:
            return []

    def _update_lexicon_and_ngrams(self, text: str):
        try:
            if not hasattr(self, "_lexicon"): self._lexicon = {}
            toks = text_utils.tokenize_text(text)
            # Document-frequency semantics: increment once per message per token
            for w in set(toks):
                self._lexicon[w] = int(self._lexicon.get(w, 0)) + 1
            # Update streaming n-grams for emergent composition
            text_utils.update_ngrams(toks, self._ng2, self._ng3)
        except Exception: pass

    def _save_lexicon(self):
        try:
            _lxn_save(self.run_dir, getattr(self, "_lexicon", {}) or {}, int(getattr(self, "_doc_count", 0)))
        except Exception:
            pass

    def _compose_say_text(self, metrics: dict, step: int, seed_tokens: set = None) -> str:
        """
        Compose a short sentence using emergent language or templates.

        Delegates to io.cognition.composer.compose_say_text (behavior-preserving).
        """
        try:
            return _compose_say_text_impl(
                metrics or {},
                int(step),
                getattr(self, "_lexicon", {}) or {},
                getattr(self, "_ng2", {}) or {},
                getattr(self, "_ng3", {}) or {},
                self.recent_text,
                templates=list(getattr(self, "_phrase_templates", []) or []),
                seed_tokens=seed_tokens,
            ) or ""
        except Exception:
            return ""

    def _emit_why(self):
        """
        Provide context for MacroEmitter / ThoughtEmitter from the last computed metrics.
        Read-only; never mutates model state.
        """
        try:
            m = getattr(self, "_emit_last_metrics", {}) or {}
            step = int(getattr(self, "_emit_step", 0))
            return _telemetry_why_base(self, m, step)
        except Exception:
            try:
                return {"t": int(getattr(self, "_emit_step", 0)), "phase": int(getattr(self, "_phase", {}).get("phase", 0))}
            except Exception:
                return {"t": 0, "phase": 0}

        # --- Phase control plane (file-driven) ---------------------------------
    def _default_phase_profiles(self):
        from .runtime.phase import default_phase_profiles as _default_phase_profiles
        return _default_phase_profiles()

    def _apply_phase_profile(self, prof: dict):
        from .runtime.phase import apply_phase_profile as _apply_phase_profile_impl
        return _apply_phase_profile_impl(self, prof)
    def _poll_control(self):
        from .runtime.phase import poll_control as _poll_control_impl
        return _poll_control_impl(self)
    
    def run(self, duration_s:int=None):
        self.ute.start()
        self.logger.info("nexus_started", extra={"extra": {"N": self.N, "k": self.k, "hz": self.hz, "domain": self.domain, "dom_mod": self.dom_mod}})
        try:
            self.logger.info("checkpoint_config", extra={"extra": {"every": int(getattr(self, "checkpoint_every", 0)), "keep": int(getattr(self, "checkpoint_keep", 0)), "format": str(getattr(self, "checkpoint_format", ""))}})
        except Exception:
            pass
        t0 = time.time()
        step0 = int(getattr(self, "start_step", 0))
        try:
            _ = _run_loop(self, t0, step0, duration_s)
        except Exception as e:
            try:
                self.logger.info("nexus_fatal", extra={"extra": {"err": str(e)}})
            except Exception:
                try:
                    print("[nexus] fatal", str(e), file=sys.stderr, flush=True)
                except Exception:
                    pass
        finally:
            self.utd.close()
            try:
                if getattr(self, "_control_server", None):
                    self._control_server.stop()
            except Exception:
                pass

def make_parser():
    from .cli.args import make_parser as _mp
    return _mp()

__all__ = ["Nexus", "make_parser"]
