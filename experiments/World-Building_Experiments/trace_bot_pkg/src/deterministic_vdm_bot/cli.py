from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import deque
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

from .bot import DeterministicConversationBot


def _read_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                yield obj


def _read_csv(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row)


def _detect_format(path: str, requested: str) -> str:
    if requested != "auto":
        return requested
    lower = path.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return "jsonl"
    return "jsonl"


def read_records(path: str, fmt: str) -> Iterator[Dict[str, Any]]:
    fmt = _detect_format(path, fmt)
    if fmt == "csv":
        yield from _read_csv(path)
    elif fmt == "jsonl":
        yield from _read_jsonl(path)
    else:
        raise ValueError(f"unsupported input format: {fmt}")


def write_jsonl(path: str, rows: Iterable[Mapping[str, Any]]) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n")
            n += 1
    return n


def run(input_path: str, output_path: str, input_format: str = "auto", lag_events: int = 0) -> int:
    bot = DeterministicConversationBot()
    lag_events = max(0, int(lag_events))
    queue: deque[Dict[str, Any]] = deque()

    def packet_stream() -> Iterator[Dict[str, Any]]:
        for record in read_records(input_path, input_format):
            packet = bot.step(record).to_dict()
            if lag_events <= 0:
                yield packet
                continue
            queue.append(packet)
            if len(queue) <= lag_events:
                tick = record.get("tick", record.get("t"))
                try:
                    tick = int(tick)
                except Exception:
                    tick = None
                yield bot.neutral_packet(tick=tick, reason="lag_warmup").to_dict()
            else:
                shifted = queue.popleft()
                shifted = dict(shifted)
                shifted["shifted_by_events"] = lag_events
                shifted["emitted_at_tick"] = record.get("tick", record.get("t"))
                yield shifted

    return write_jsonl(output_path, packet_stream())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic VDM conversation bot over translation logs.")
    parser.add_argument("--input", required=True, help="Input CSV or JSONL translation log.")
    parser.add_argument("--output", required=True, help="Output JSONL bot packet log.")
    parser.add_argument("--input-format", default="auto", choices=("auto", "csv", "jsonl"), help="Input format.")
    parser.add_argument("--lag-events", type=int, default=0, help="Emit replies delayed by this many input events.")
    args = parser.parse_args(argv)

    count = run(args.input, args.output, args.input_format, args.lag_events)
    print(f"wrote {count} bot packets to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
