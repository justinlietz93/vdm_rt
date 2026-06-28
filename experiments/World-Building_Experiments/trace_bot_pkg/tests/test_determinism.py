from __future__ import annotations

import json
import os
import tempfile
import unittest

from deterministic_vdm_bot import DeterministicConversationBot
from deterministic_vdm_bot.cli import run


class TestDeterministicConversationBot(unittest.TestCase):
    def test_same_sequence_same_packets(self) -> None:
        seq = [
            {"tick": 1, "phrase": "Do I hold attention here?", "family": "attention"},
            {"tick": 2, "phrase": "I think I keep this contained.", "family": "containment"},
            {"tick": 3, "phrase": "I might sense this is still fighting.", "family": "conflict"},
        ]
        a = DeterministicConversationBot()
        b = DeterministicConversationBot()
        out_a = [a.step(x).to_json() for x in seq]
        out_b = [b.step(x).to_json() for x in seq]
        self.assertEqual(out_a, out_b)

    def test_keyword_family_fallback(self) -> None:
        bot = DeterministicConversationBot()
        packet = bot.step({"tick": 1, "phrase": "I sense I have met this before."})
        self.assertEqual(packet.input_family, "recognition")
        self.assertIn("Preserve continuity", packet.reply_text)

    def test_lag_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inp = os.path.join(td, "in.jsonl")
            out = os.path.join(td, "out.jsonl")
            with open(inp, "w", encoding="utf-8") as f:
                f.write(json.dumps({"tick": 1, "phrase": "I keep this contained.", "family": "containment"}) + "\n")
                f.write(json.dumps({"tick": 2, "phrase": "I sense I have met this before.", "family": "recognition"}) + "\n")
            n = run(inp, out, input_format="jsonl", lag_events=1)
            self.assertEqual(n, 2)
            with open(out, "r", encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual(rows[0]["action"], "steady:lag_warmup")
            self.assertEqual(rows[1]["input_family"], "containment")
            self.assertEqual(rows[1]["shifted_by_events"], 1)


if __name__ == "__main__":
    unittest.main()
