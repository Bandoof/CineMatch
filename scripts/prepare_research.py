"""Freeze disjoint v1.2 cohorts and inputs before validation/model selection."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scripts.download_benchmark import load
from src.catalog import canonical_catalog
from src.data import ROOT, temporal_split
from src.research_protocol import (digest_json, file_digest, targets,
                                   verify_boundaries, write_new_json)


def prepare(directory, archive, output, config_path):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if file_digest(archive) != config["archive_sha256"]:
        raise ValueError("The official archive checksum does not match.")
    historical = ROOT / config["historical_report"]
    old = json.loads(historical.read_text(encoding="utf-8"))
    old_ids = set(old["validation_user_ids"]) | set(old["test_user_ids"])
    movies, events = load(directory)
    movies, events, _ = canonical_catalog(movies, events)
    train, validation, test = temporal_split(events)
    val_users = targets(train, validation, old_ids, config["maximum_validation_users"],
                        config["minimum_history"])
    val_ids = [user.user_id for user in val_users]
    test_users = targets(pd.concat([train, validation], ignore_index=True), test,
                         old_ids | set(val_ids), config["maximum_test_users"],
                         config["minimum_history"])
    test_ids = [user.user_id for user in test_users]
    verify_boundaries(train, validation, test, val_ids, test_ids, old_ids)
    output.mkdir(exist_ok=True, parents=True)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "config": config,
        "config_sha256": digest_json(config),
        "input_sha256": {name: file_digest(directory / name)
                         for name in ("movies.dat", "ratings.dat", "README")},
        "historical_report_sha256": file_digest(historical),
        "old_target_user_count": len(old_ids),
        "old_validation_test_overlap": len(set(old["validation_user_ids"]) & set(old["test_user_ids"])),
        "events": len(events), "catalog": len(movies), "source_users": int(events.user_id.nunique()),
        "validation_user_ids": val_ids, "test_user_ids": test_ids,
        "split": {"train": len(train), "validation": len(validation), "test": len(test),
                  "train_cutoff": int(train.timestamp.max()),
                  "validation_cutoff": int(validation.timestamp.max())},
        "scope": "New target-user cohorts disjoint from each other and v3 evaluation targets. "
                 "Same publicly known historical dataset, not an external replication. "
                 "Eligibility uses future positives; cohort preparation exposes IDs/counts, "
                 "never model outcomes. All reserved users excluded from both background fits. "
                 "Titles/genres are archive metadata, not guaranteed as-of-rating snapshots."
    }
    write_new_json(output / "manifest.json", manifest)
    print(json.dumps({"validation_users": len(val_ids), "test_users": len(test_ids),
                      "config_sha256": manifest["config_sha256"]}), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/ml-v12-2026-10-09.json")
    args = parser.parse_args()
    prepare(args.data_dir, args.archive, args.output, args.config)


if __name__ == "__main__":
    main()
