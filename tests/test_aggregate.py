"""Tests for skills/hill-climb/scripts/aggregate.py (standard library only).

Run from the repo root:  python -m unittest discover -s tests -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "hill-climb" / "scripts" / "aggregate.py"
EXAMPLE = ROOT / "examples" / "landing-page"


def run(folder, *args):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(folder), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


def write_round(base, n, labels, judges):
    """judges: {judge_name: {real_item_name: {category: score}}}"""
    folder = Path(base) / f"round-{n}"
    folder.mkdir(parents=True)
    (folder / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    by_name = {v: k for k, v in labels.items()}
    for judge, items in judges.items():
        payload = {"judge": judge, "items": {by_name[name]: {"scores": s} for name, s in items.items()}}
        (folder / f"{judge.replace(' ', '-').lower()}.json").write_text(json.dumps(payload), encoding="utf-8")


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_example_passes(self):
        code, out = run(EXAMPLE, "--target", "9")
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: PASS", out)
        self.assertIn("| Gemini Pro | not run | not run | 9.3 |", out)

    def test_shuffled_labels_map_to_real_items(self):
        write_round(self.dir, 0, {"A": "ours", "B": "ref"},
                    {"J1": {"ours": {"X": 9.5}, "ref": {"X": 8.0}}, "J2": {"ours": {"X": 9.4}, "ref": {"X": 8.0}}})
        write_round(self.dir, 1, {"A": "ref", "B": "ours"},
                    {"J1": {"ours": {"X": 9.6}, "ref": {"X": 8.0}}, "J2": {"ours": {"X": 9.5}, "ref": {"X": 8.0}}})
        code, out = run(self.dir)
        self.assertEqual(code, 0, out)
        self.assertIn("| J1 | 9.5 | 9.6 |", out)

    def test_below_target_fails(self):
        write_round(self.dir, 0, {"A": "ours"}, {"J1": {"ours": {"X": 9.5}}, "J2": {"ours": {"X": 8.9}}})
        code, out = run(self.dir, "--target", "9")
        self.assertEqual(code, 1, out)
        self.assertIn("J2: X = 8.9 < 9.0", out)

    def test_below_best_reference_fails(self):
        write_round(self.dir, 0, {"A": "ours", "B": "ref"},
                    {"J1": {"ours": {"X": 9.2}, "ref": {"X": 9.4}}, "J2": {"ours": {"X": 9.3}, "ref": {"X": 9.0}}})
        code, out = run(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn("below the best reference", out)

    def test_judge_missing_from_final_round_fails(self):
        write_round(self.dir, 0, {"A": "ours"}, {"J1": {"ours": {"X": 9.5}}, "J2": {"ours": {"X": 9.5}}})
        write_round(self.dir, 1, {"A": "ours"}, {"J1": {"ours": {"X": 9.6}}})
        code, out = run(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn("J2: not run in the final round", out)

    def test_advisory_judge_does_not_gate(self):
        write_round(self.dir, 0, {"A": "ours"},
                    {"J1": {"ours": {"X": 9.5}}, "J2": {"ours": {"X": 9.3}}, "Jester": {"ours": {"X": 4.0}}})
        code, out = run(self.dir, "--advisory", "Jester")
        self.assertEqual(code, 0, out)
        self.assertIn("Jester (advisory)", out)

    def test_plateau_warning(self):
        for n, score in enumerate([8.0, 8.1, 8.2]):
            write_round(self.dir, n, {"A": "ours"}, {"J1": {"ours": {"X": score}}, "J2": {"ours": {"X": score}}})
        code, out = run(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn("WARNING: plateau", out)

    def test_no_reference_warning(self):
        write_round(self.dir, 0, {"A": "ours"}, {"J1": {"ours": {"X": 9.5}}, "J2": {"ours": {"X": 9.5}}})
        code, out = run(self.dir)
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING: no references", out)

    def test_unknown_label_is_a_data_error(self):
        folder = self.dir / "round-0"
        folder.mkdir()
        (folder / "labels.json").write_text('{"A": "ours"}', encoding="utf-8")
        (folder / "j1.json").write_text('{"judge": "J1", "items": {"Z": {"scores": {"X": 9}}}}', encoding="utf-8")
        code, out = run(self.dir)
        self.assertEqual(code, 2, out)
        self.assertIn("label Z not in labels.json", out)

    def test_empty_folder_is_a_data_error(self):
        code, _ = run(self.dir)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
