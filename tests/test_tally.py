"""Tests for skills/blind-refine/scripts/tally.py (standard library only).

Run from the repo root:  python -m unittest discover -s tests -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "blind-refine" / "scripts" / "tally.py"

MAJOR = {"severity": "major", "where": "hero", "problem": "unclear offer", "fix": "say what it is"}
NIT = {"severity": "nit", "where": "footer", "problem": "spacing", "fix": "8px"}


def run(folder, *args):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(folder), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


def write(base, name, labels, reviewers):
    """reviewers: {name: (preferred_version, {version: ready}, {version: [findings]})}"""
    folder = Path(base) / name
    folder.mkdir(parents=True)
    (folder / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    label_of = {v: k for k, v in labels.items()}
    for reviewer, (pref, ready, findings) in reviewers.items():
        payload = {
            "reviewer": reviewer,
            "preferred": label_of[pref] if pref else None,
            "ready_to_ship": {label_of[v]: r for v, r in ready.items()},
            "findings": {label_of[v]: f for v, f in findings.items()},
        }
        (folder / f"{reviewer.lower()}.json").write_text(json.dumps(payload), encoding="utf-8")


class TallyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_zero_with_majors_continues(self):
        write(self.dir, "round-0", {"X": "current"},
              {"R1": (None, {"current": False}, {"current": [MAJOR]}),
               "R2": (None, {"current": False}, {"current": [NIT]})})
        code, out = run(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn("R1: 1 major finding(s)", out)

    def test_candidate_kept_by_majority_and_done(self):
        write(self.dir, "round-0", {"X": "current"},
              {"R1": (None, {"current": False}, {"current": [MAJOR]}),
               "R2": (None, {"current": False}, {"current": [MAJOR]})})
        write(self.dir, "round-1", {"X": "candidate", "Y": "current"},
              {"R1": ("candidate", {"candidate": True, "current": False}, {"candidate": [NIT], "current": [MAJOR]}),
               "R2": ("candidate", {"candidate": True, "current": False}, {"candidate": [], "current": [MAJOR]})})
        code, out = run(self.dir)
        self.assertEqual(code, 0, out)
        self.assertIn("KEEP the candidate", out)
        self.assertIn("RESULT: DONE", out)

    def test_tie_keeps_current(self):
        write(self.dir, "round-0", {"X": "current"}, {"R1": (None, {}, {}), "R2": (None, {}, {})})
        write(self.dir, "round-1", {"Y": "candidate", "X": "current"},
              {"R1": ("candidate", {}, {}), "R2": ("current", {}, {"current": [MAJOR]})})
        code, out = run(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn("REVERT to the current version (1 of 2", out)

    def test_two_lost_rounds_is_a_plateau(self):
        write(self.dir, "round-0", {"X": "current"}, {"R1": (None, {}, {}), "R2": (None, {}, {})})
        for n in (1, 2):
            write(self.dir, f"round-{n}", {"X": "current", "Y": "candidate"},
                  {"R1": ("current", {}, {}), "R2": ("current", {}, {})})
        code, out = run(self.dir)
        self.assertEqual(code, 3, out)
        self.assertIn("RESULT: PLATEAU", out)

    def test_advisory_reviewer_does_not_gate(self):
        write(self.dir, "round-0", {"X": "current"},
              {"R1": (None, {"current": True}, {}), "R2": (None, {"current": True}, {}),
               "Noisy": (None, {"current": False}, {"current": [MAJOR]})})
        code, out = run(self.dir, "--advisory", "Noisy")
        self.assertEqual(code, 0, out)
        self.assertIn("Noisy (advisory)", out)

    def test_final_check_warns_when_original_wins(self):
        write(self.dir, "round-0", {"X": "current"},
              {"R1": (None, {"current": True}, {}), "R2": (None, {"current": True}, {})})
        write(self.dir, "final-check", {"X": "original", "Y": "final"},
              {"R1": ("original", {}, {}), "R2": ("final", {}, {})})
        code, out = run(self.dir)
        self.assertEqual(code, 0, out)
        self.assertIn("preferred over the original by 1 of 2", out)
        self.assertIn("WARNING: the reviewers do not prefer the final version", out)

    def test_bad_severity_is_a_data_error(self):
        write(self.dir, "round-0", {"X": "current"},
              {"R1": (None, {}, {"current": [{"severity": "critical"}]})})
        code, out = run(self.dir)
        self.assertEqual(code, 2, out)
        self.assertIn("severity must be one of", out)

    def test_unknown_version_name_is_a_data_error(self):
        folder = self.dir / "round-0"
        folder.mkdir()
        (folder / "labels.json").write_text('{"X": "ours"}', encoding="utf-8")
        (folder / "r1.json").write_text('{"reviewer": "R1"}', encoding="utf-8")
        code, out = run(self.dir)
        self.assertEqual(code, 2, out)
        self.assertIn("unknown version names ours", out)

    def test_duplicate_reviewer_is_a_data_error(self):
        write(self.dir, "round-0", {"X": "current"}, {"R1": (None, {}, {})})
        (self.dir / "round-0" / "copy.json").write_text('{"reviewer": "R1"}', encoding="utf-8")
        code, out = run(self.dir)
        self.assertEqual(code, 2, out)
        self.assertIn("reviewer 'R1' already has a file", out)

    def test_empty_folder_is_a_data_error(self):
        code, _ = run(self.dir)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
