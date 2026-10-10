"""Verify surviving v1.2 evidence without fitting models or evaluating holdout labels.

Optional dataset inputs are only hashed, never parsed. Output is exclusively
created, so an existing report or historical benchmark cannot be overwritten.
"""

import argparse
import json
from pathlib import Path

from src.data import ROOT
from src.research_protocol import digest_json, file_digest, write_new_json


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root=ROOT, data_dir=None, archive=None):
    root = Path(root)
    require((data_dir is None) == (archive is None), "Supply both data directory and archive.")
    config_path = root / "configs/ml-v12-2026-10-09.json"
    manifest_path = root / "reports/ml_v12_manifest.json"
    baseline_path = root / "reports/ml_v12_baseline.json"
    config, manifest, baseline = map(read_json, (config_path, manifest_path, baseline_path))
    require(config == manifest["config"], "Configuration differs from the saved manifest.")
    require(digest_json(config) == manifest["config_sha256"], "Configuration checksum mismatch.")
    historical_path = root / config["historical_report"]
    historical = read_json(historical_path)
    require(
        file_digest(historical_path) == manifest["historical_report_sha256"],
        "Historical cohort evidence changed.",
    )
    validation, test = manifest["validation_user_ids"], manifest["test_user_ids"]
    old_validation, old_test = historical["validation_user_ids"], historical["test_user_ids"]
    old_ids = set(old_validation) | set(old_test)
    for name, ids in (("validation", validation), ("test", test)):
        require(bool(ids), f"Empty {name} cohort.")
        require(all(type(uid) is int and uid > 0 for uid in ids), f"Invalid {name} user IDs.")
        require(len(ids) == len(set(ids)), f"Duplicate {name} user IDs.")
        require(not set(ids) & old_ids, f"Historical users reused in {name} cohort.")
        require(len(ids) <= config[f"maximum_{name}_users"], f"Oversized {name} cohort.")
    require(not set(validation) & set(test), "Validation/test cohort overlap.")
    require(len(old_ids) == manifest["old_target_user_count"], "Historical count mismatch.")
    require(
        len(set(old_validation) & set(old_test)) == manifest["old_validation_test_overlap"],
        "Historical overlap count mismatch.",
    )
    split = manifest["split"]
    require(
        all(split[name] > 0 for name in ("train", "validation", "test"))
        and sum(split[name] for name in ("train", "validation", "test")) == manifest["events"],
        "Invalid saved temporal partition counts.",
    )
    require(split["train_cutoff"] < split["validation_cutoff"], "Invalid temporal cutoffs.")
    hashes = {}
    for name, expected in baseline["historical_evidence_sha256"].items():
        actual = file_digest(root / name)
        require(actual == expected, f"Historical evidence checksum mismatch: {name}")
        hashes[name] = actual
    dataset = {"status": "not_checked", "reason": "No public dataset paths supplied."}
    if data_dir is not None:
        actual_archive = file_digest(archive)
        require(actual_archive == config["archive_sha256"], "Archive checksum mismatch.")
        inputs = {}
        for name, expected in manifest["input_sha256"].items():
            actual = file_digest(Path(data_dir) / name)
            require(actual == expected, f"Dataset input checksum mismatch: {name}")
            inputs[name] = actual
        dataset = {
            "status": "verified",
            "archive_sha256": actual_archive,
            "input_sha256": inputs,
            "operation": "Byte hashing only; no interaction parsing, training or scoring.",
        }
    return {
        "schema_version": 1,
        "status": "surviving_evidence_verified",
        "evidence_sha256": {
            "config": file_digest(config_path),
            "manifest": file_digest(manifest_path),
            "baseline": file_digest(baseline_path),
        },
        "config_sha256": manifest["config_sha256"],
        "cohorts": {
            "validation_users": len(validation),
            "test_users": len(test),
            "historical_target_users": len(old_ids),
            "historical_validation_test_overlap": manifest["old_validation_test_overlap"],
            "validation_test_overlap": 0,
            "historical_reuse": 0,
            "scope": "Saved IDs/counts verified; eligibility and model outcomes not reevaluated.",
        },
        "historical_evidence_sha256": hashes,
        "dataset": dataset,
        "final_metrics_verified": False,
        "scope": "Integrity of surviving protocol evidence only. This does not verify "
        "missing validation, frozen selection, final outcomes or confidence intervals.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, help="New JSON file; refuses an existing path.")
    args = parser.parse_args()
    result = verify(data_dir=args.data_dir, archive=args.archive)
    if args.output:
        write_new_json(args.output, result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
