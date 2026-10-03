"""Publication deadline, source binding and immutable-file checks."""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "memo_publisher", Path(__file__).resolve().parents[1] / "scripts" / "publish_event_memo.py"
)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = "docs/event-memos/sealed/"
        self.memo_path = self.prefix + "2026-10-04-test.md"
        self.manifest_path = self.prefix + "2026-10-04-test.json"
        self.forecast_path = self.prefix + "evidence/2026-10-04/forecast.json"
        self.evidence_path = self.prefix + "evidence/2026-10-04/weather-and-references.json"
        self.forecast = json.dumps({
            "delivery_date_local": "2026-10-04", "bidding_zone": "DE-LU",
            "sealed_at_utc": "2026-10-03T08:00:00Z", "auction_closes_utc": "2026-10-03T10:00:00Z"
        }).encode()
        self.write(self.memo_path, b"# Test fixture\nBullish price-view fixture; not a live event.\n")
        self.write(self.forecast_path, self.forecast)
        evidence = b'{"weather":"synthetic test fixture","reference":100}\n'
        self.write(self.evidence_path, evidence)
        self.manifest = {
            "schema_version": 1, "kind": "event", "memo_path": self.memo_path,
            "delivery_date_local": "2026-10-04", "memo_written_at_utc": "2026-10-03T08:15:00Z",
            "forecast": {
                "repository": publisher.FORECAST_REPO, "commit_sha": "a" * 40,
                "path": "predictions/2026-10-04.json", "snapshot_path": self.forecast_path,
                "sha256": hashlib.sha256(self.forecast).hexdigest()
            },
            "evidence_files": [{"path": self.evidence_path, "sha256": hashlib.sha256(evidence).hexdigest()}]
        }
        self.context = {"commit_sha": "b" * 40, "run_created_at_utc": "2026-10-03T08:30:00Z"}

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def receipt(self):
        self.write(self.manifest_path, json.dumps(self.manifest).encode())
        return publisher.build_receipt(self.root, self.manifest_path, self.context, lambda _: self.forecast)

    def test_server_time_binds_text_and_hash(self):
        result = self.receipt()
        self.assertEqual(result["publication_status"], "PROSPECTIVE")
        self.assertEqual(result["publication_deadline_utc"], "2026-10-03T09:30:00+00:00")
        self.assertIn("Bullish price-view fixture", result["memo_text"])
        self.assertEqual(result["file_sha256"][self.memo_path], hashlib.sha256((self.root / self.memo_path).read_bytes()).hexdigest())

    def test_deadline_is_strict_and_dst_aware(self):
        self.context["run_created_at_utc"] = "2026-10-03T09:30:00Z"
        with self.assertRaises(ValueError):
            self.receipt()
        # D-1 after the autumn clock change uses 10:30 UTC for 11:30 Berlin.
        day = publisher.date(2026, 10, 26)
        cutoff = publisher.datetime.combine(day - publisher.timedelta(days=1), publisher.time(11, 30), publisher.BERLIN)
        self.assertEqual(cutoff.astimezone(timezone.utc).hour, 10)

    def test_later_forecast_is_rejected(self):
        self.manifest["memo_written_at_utc"] = "2026-10-03T07:59:00Z"
        with self.assertRaises(ValueError):
            self.receipt()

    def test_changed_evidence_and_upstream_mismatch_are_rejected(self):
        self.write(self.evidence_path, b"changed")
        with self.assertRaises(ValueError):
            self.receipt()
        self.write(self.manifest_path, json.dumps(self.manifest).encode())
        with self.assertRaises(ValueError):
            publisher.build_receipt(self.root, self.manifest_path, self.context, lambda _: b"different upstream bytes")

    def test_real_publication_cannot_use_local_dry_run(self):
        self.write(self.manifest_path, json.dumps(self.manifest).encode())
        with self.assertRaises(ValueError):
            publisher.build_receipt(self.root, self.manifest_path, None)

    def test_path_escape_and_mislabelled_dummy_are_rejected(self):
        self.manifest["memo_path"] = self.prefix + "../../README.md"
        with self.assertRaises(ValueError):
            self.receipt()
        self.manifest["memo_path"] = self.memo_path
        self.manifest["kind"] = "dry_run"
        with self.assertRaises(ValueError):
            self.receipt()

    def test_dummy_receipt_is_visibly_separate(self):
        memo = "docs/event-memos/dry-runs/test.md"
        manifest = "docs/event-memos/dry-runs/test.json"
        self.write(memo, b"# DRY RUN\nNo event or trading call.\n")
        self.write(manifest, json.dumps({"schema_version": 1, "kind": "dry_run", "memo_path": memo}).encode())
        result = publisher.build_receipt(self.root, manifest, None)
        self.assertEqual(result["publication_status"], "LOCAL_DRY_RUN_NO_GITHUB_PROOF")
        self.assertIsNone(result["github"])

    def test_editing_a_sealed_file_fails_push_check(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        git = lambda *args: subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.invalid")
        git("add", ".")
        git("commit", "-qm", "synthetic fixture")
        before = git("rev-parse", "HEAD")
        self.write(self.memo_path, b"changed sealed memo")
        git("add", ".")
        git("commit", "-qm", "synthetic edit")
        after = git("rev-parse", "HEAD")
        with self.assertRaises(ValueError):
            publisher.changed_manifests({"before": before, "after": after}, self.root)


if __name__ == "__main__":
    unittest.main()
