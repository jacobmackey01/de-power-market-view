"""Record a memo's committed bytes against a GitHub Actions server timestamp."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
from zoneinfo import ZoneInfo

UTC = timezone.utc
BERLIN = ZoneInfo("Europe/Berlin")
SEALED = "docs/event-memos/sealed/"
DRY_RUNS = "docs/event-memos/dry-runs/"
FORECAST_REPO = "jacobmackey01/de-power-live-forecast"


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("timestamps require an explicit UTC offset")
    return result.astimezone(UTC)


def read_file(root: Path, name: str, prefix: str) -> bytes:
    if not isinstance(name, str) or not name.startswith(prefix):
        raise ValueError(f"file must be inside {prefix}")
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to((root / prefix).resolve()):
        raise ValueError("file path leaves its permitted directory")
    return path.read_bytes()


def fetch_bytes(url: str, token: str | None = None) -> bytes:
    headers = {"User-Agent": "de-power-market-view-publication"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read()


def github_context() -> dict:
    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    sha = os.environ["GITHUB_SHA"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not run_id.isdigit():
        raise ValueError("invalid GitHub run identity")
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    run = json.loads(fetch_bytes(url, os.environ.get("GITHUB_TOKEN")))
    if run["head_sha"] != sha:
        raise ValueError("GitHub's run commit differs from the checked-out event commit")
    actual_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual_sha != sha:
        raise ValueError("checkout does not match the GitHub event commit")
    return {
        "repository": repo, "commit_sha": sha, "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "run_url": run["html_url"], "run_created_at_utc": run["created_at"],
        "server_record_url": url,
    }


def changed_manifests(event: dict, root: Path | None = None) -> list[str]:
    before, after = event["before"], event["after"]
    if not re.fullmatch(r"[0-9a-f]{40}", before) or not re.fullmatch(r"[0-9a-f]{40}", after):
        raise ValueError("invalid push commits")
    if before == "0" * 40:
        command = ["git", "diff-tree", "--root", "--no-commit-id", "--no-renames", "--name-status", "-r", after]
    else:
        subprocess.run(["git", "merge-base", "--is-ancestor", before, after], check=True, cwd=root)
        command = ["git", "diff", "--no-renames", "--name-status", before, after]
    changes = subprocess.check_output(command, text=True, cwd=root).splitlines()
    manifests = []
    for row in changes:
        status, name = row.split("\t", 1)
        if name.startswith(SEALED) and status != "A":
            raise ValueError(f"sealed files cannot be edited or deleted: {name}")
        if name.endswith(".json") and name.startswith((SEALED, DRY_RUNS)):
            # Evidence JSON belongs below evidence/, not at the manifest level.
            if "/evidence/" not in name and status == "A":
                manifests.append(name)
    return sorted(manifests)


def build_receipt(root: Path, manifest_path: str, context: dict | None, remote_reader=fetch_bytes) -> dict:
    prefix = DRY_RUNS if manifest_path.startswith(DRY_RUNS) else SEALED
    raw = read_file(root, manifest_path, prefix)
    manifest = json.loads(raw)
    dry_run = manifest.get("kind") == "dry_run"
    if manifest.get("schema_version") != 1 or manifest.get("kind") not in ("event", "dry_run"):
        raise ValueError("expected schema 1 and event/dry_run kind")
    if dry_run != (prefix == DRY_RUNS):
        raise ValueError("dry runs and real events must use separate directories")
    if context is None and not dry_run:
        raise ValueError("real publication requires a GitHub server-time record")
    memo_path = manifest["memo_path"]
    memo = read_file(root, memo_path, prefix)
    if not memo_path.endswith(".md") or not memo.strip():
        raise ValueError("memo must be a nonempty Markdown file")
    files = {manifest_path: hashlib.sha256(raw).hexdigest(), memo_path: hashlib.sha256(memo).hexdigest()}
    receipt = {
        "schema_version": 1,
        "publication_status": "DRY_RUN_NOT_AN_EVENT" if dry_run else "PROSPECTIVE",
        "github": context,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "manifest_path": manifest_path,
        "memo_text": memo.decode("utf-8"),
        "file_sha256": files,
    }
    if dry_run:
        if "DRY RUN" not in receipt["memo_text"]:
            raise ValueError("dummy memo must visibly say DRY RUN")
        if context is None:
            receipt["publication_status"] = "LOCAL_DRY_RUN_NO_GITHUB_PROOF"
        return receipt
    delivery = date.fromisoformat(manifest["delivery_date_local"])
    if not date(2026, 10, 4) <= delivery <= date(2026, 10, 31):
        raise ValueError("this companion study is limited to October 2026 deliveries")
    cutoff = datetime.combine(delivery - timedelta(days=1), time(11, 30), BERLIN).astimezone(UTC)
    written = timestamp(manifest["memo_written_at_utc"])
    published = timestamp(context["run_created_at_utc"])
    if not written <= published < cutoff:
        raise ValueError("memo and GitHub run must precede the 11:30 Europe/Berlin publication deadline")
    forecast = manifest["forecast"]
    if forecast["repository"] != FORECAST_REPO or not re.fullmatch(r"[0-9a-f]{40}", forecast["commit_sha"]):
        raise ValueError("forecast must cite the existing live repository at an immutable commit")
    if forecast["path"] != f"predictions/{delivery.isoformat()}.json":
        raise ValueError("forecast delivery date differs from the memo")
    snapshot = read_file(root, forecast["snapshot_path"], SEALED)
    snapshot_hash = hashlib.sha256(snapshot).hexdigest()
    if snapshot_hash != forecast["sha256"]:
        raise ValueError("saved forecast hash differs from the manifest")
    forecast_url = f"https://raw.githubusercontent.com/{FORECAST_REPO}/{forecast['commit_sha']}/{forecast['path']}"
    if hashlib.sha256(remote_reader(forecast_url)).hexdigest() != snapshot_hash:
        raise ValueError("saved forecast differs from the cited upstream commit")
    payload = json.loads(snapshot)
    if payload["delivery_date_local"] != delivery.isoformat() or timestamp(payload["sealed_at_utc"]) > written:
        raise ValueError("live forecast must have been sealed before the memo was written")
    if payload.get("bidding_zone") != "DE-LU":
        raise ValueError("forecast bidding zone must be DE-LU")
    if timestamp(payload["sealed_at_utc"]) >= timestamp(payload["auction_closes_utc"]):
        raise ValueError("upstream prediction was sealed after its auction cutoff")
    files[forecast["snapshot_path"]] = snapshot_hash
    evidence = manifest.get("evidence_files", [])
    if not evidence:
        raise ValueError("record the weather and reference evidence files before publication")
    for item in evidence:
        body = read_file(root, item["path"], SEALED)
        digest = hashlib.sha256(body).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"evidence hash differs: {item['path']}")
        files[item["path"]] = digest
    receipt["publication_deadline_utc"] = cutoff.isoformat()
    receipt["forecast_url"] = forecast_url
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest")
    parser.add_argument("--local-dry-run", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = Path.cwd()
        context = None if args.local_dry_run else github_context()
        if args.local_dry_run and not args.manifest:
            raise ValueError("local dry run needs an explicit dummy manifest")
        if args.manifest:
            if context is not None:
                parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], text=True).strip()
                changed_manifests({"before": parent, "after": context["commit_sha"]})
            manifests = [args.manifest]
        else:
            event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
            if event["after"] != context["commit_sha"]:
                raise ValueError("push event does not match the run commit")
            manifests = changed_manifests(event)
        receipts = [build_receipt(root, name, context) for name in manifests]
        rendered = json.dumps(receipts, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
        print(rendered, end="")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write("# Event memo publication receipts\n\n```json\n" + rendered + "```\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"publication failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
