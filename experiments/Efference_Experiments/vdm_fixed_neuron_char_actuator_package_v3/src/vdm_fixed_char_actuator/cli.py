from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .channel import FixedNeuronCharMap, FixedNeuronWritingActuator


def _load_scores(row: Dict[str, Any]) -> Dict[int, float]:
    raw = row.get("neuron_scores", {})
    if isinstance(raw, dict):
        return {int(k): float(v) for k, v in raw.items()}
    if isinstance(raw, list):
        return {int(i): float(v) for i, v in enumerate(raw)}
    raise ValueError("row must contain neuron_scores as object or list")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run fixed-neuron written-message actuator on JSONL ticks")
    p.add_argument("--input", required=True, help="Input JSONL with tick, neuron_scores, optional intent_text/witness_event")
    p.add_argument("--output", required=True, help="Output JSONL tick results")
    p.add_argument("--mapping-csv", default=None, help="Optional path to write fixed neuron mapping CSV")
    args = p.parse_args(argv)

    mapping = FixedNeuronCharMap()
    actuator = FixedNeuronWritingActuator(mapping=mapping)

    if args.mapping_csv:
        path = Path(args.mapping_csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write("label,neuron_id,type\n")
            for label, nid, kind in mapping.as_rows():
                safe = label.replace("\n", "NEWLINE")
                f.write(f"{json.dumps(safe)[1:-1]},{nid},{kind}\n")

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            row = json.loads(line)
            out = actuator.step(
                tick=int(row.get("tick", 0)),
                neuron_scores=_load_scores(row),
                intent_text=row.get("intent_text"),
                witness_event=bool(row.get("witness_event", False)),
            )
            fout.write(json.dumps(out.__dict__, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
