import json
import shutil

import pytest

from scripts.verify_v12_evidence import verify
from src.data import ROOT
from src.research_protocol import digest_json, file_digest, write_new_json


@pytest.fixture
def evidence(tmp_path):
    for name in (
        "configs/ml-v12-2026-10-09.json",
        "reports/ml_v12_manifest.json",
        "reports/ml_v12_baseline.json",
    ):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    baseline = json.loads((ROOT / "reports/ml_v12_baseline.json").read_text(encoding="utf-8"))
    for name in baseline["historical_evidence_sha256"]:
        shutil.copyfile(ROOT / name, tmp_path / name)
    return tmp_path


def change_json(root, name, change):
    path = root / name
    document = json.loads(path.read_text(encoding="utf-8"))
    change(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_committed_survivors_do_not_establish_final_metrics(evidence):
    before = {path: path.read_bytes() for path in evidence.rglob("*") if path.is_file()}
    result = verify(evidence)
    assert result["cohorts"]["validation_users"] == 171
    assert result["cohorts"]["test_users"] == 326
    assert len(result["historical_evidence_sha256"]) == 11
    assert result["dataset"]["status"] == "not_checked"
    assert result["final_metrics_verified"] is False
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("corruption", ["duplicate", "overlap", "historical"])
def test_invalid_cohort_evidence_is_rejected(evidence, corruption):
    def corrupt(manifest):
        if corruption == "duplicate":
            manifest["test_user_ids"][0] = manifest["test_user_ids"][1]
        elif corruption == "overlap":
            manifest["test_user_ids"][0] = manifest["validation_user_ids"][0]
        else:
            old = json.loads((evidence / "reports/ml_v3.json").read_text(encoding="utf-8"))
            manifest["test_user_ids"][0] = old["test_user_ids"][0]

    change_json(evidence, "reports/ml_v12_manifest.json", corrupt)
    with pytest.raises(ValueError, match="Duplicate|overlap|reused"):
        verify(evidence)


def test_changed_config_and_historical_evidence_are_rejected(evidence):
    config_path = evidence / "configs/ml-v12-2026-10-09.json"
    original = config_path.read_bytes()
    change_json(evidence, "configs/ml-v12-2026-10-09.json", lambda d: d.update(epochs=99))
    with pytest.raises(ValueError, match="Configuration differs"):
        verify(evidence)
    config_path.write_bytes(original)
    (evidence / "reports/ml_v3.csv").write_text("changed historical evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="Historical evidence checksum"):
        verify(evidence)


def test_data_is_only_hashed_and_existing_output_is_preserved(evidence, tmp_path):
    data = tmp_path / "public-inputs"
    data.mkdir()
    archive = data / "archive.zip"
    archive.write_bytes(b"synthetic checksum fixture, not a real dataset")
    for name in ("movies.dat", "ratings.dat", "README"):
        (data / name).write_bytes(b"not parseable interactions")
    config_path = evidence / "configs/ml-v12-2026-10-09.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["archive_sha256"] = file_digest(archive)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    change_json(
        evidence,
        "reports/ml_v12_manifest.json",
        lambda d: d.update(
            config=config,
            config_sha256=digest_json(config),
            input_sha256={
                name: file_digest(data / name) for name in ("movies.dat", "ratings.dat", "README")
            },
        ),
    )
    result = verify(evidence, data, archive)
    assert result["dataset"]["status"] == "verified"
    output = tmp_path / "recovered.json"
    write_new_json(output, result)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_new_json(output, result)
    assert output.read_bytes() == original
    (data / "ratings.dat").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Dataset input checksum"):
        verify(evidence, data, archive)
    with pytest.raises(ValueError, match="Supply both"):
        verify(evidence, data)
