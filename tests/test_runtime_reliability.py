import numpy as np

from app.runtime import artifact_signature, load_runtime
from src.data import fingerprint, load_app_movies


def test_corrupt_artifacts_fall_back_then_repaired_files_invalidate_cache(dataset_dir):
    model = dataset_dir / "models" / "full.npz"
    report = dataset_dir / "reports" / "metrics.json"
    series = dataset_dir / "series.json"
    metadata = dataset_dir / "metadata.json"
    content = dataset_dir / "content.json"
    for path in (model, report, series, metadata, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic invalid artifact")
    paths = [
        dataset_dir / "u.data",
        dataset_dir / "u.item",
        model,
        report,
        series,
        metadata,
        content,
    ]
    args = (str(dataset_dir), str(series), str(dataset_dir))
    load_runtime.clear()
    try:
        broken_signature = artifact_signature(paths)
        engine, loaded_report, _, warnings = load_runtime(
            *args, broken_signature, str(metadata), str(content)
        )
        assert loaded_report is None
        assert {"model_rebuilt", "benchmark_invalid", "series_invalid", "metadata_invalid"} <= set(
            warnings
        )
        assert all(
            path.read_bytes() == b"synthetic invalid artifact"
            for path in (model, report, series, metadata, content)
        )
        expected = engine.score_components({1: 5})
        movies, ratings = load_app_movies(dataset_dir)
        engine.collaborative.save(model, fingerprint(movies, ratings))
        metadata.write_text('{"schema_version":1,"items":{}}', encoding="utf-8")
        for path in (report, series, content):
            path.unlink()
        repaired_signature = artifact_signature(paths)
        assert repaired_signature != broken_signature
        repaired, _, _, repaired_warnings = load_runtime(
            *args, repaired_signature, str(metadata), str(content)
        )
        assert repaired is not engine and not repaired_warnings
        for name, scores in repaired.score_components({1: 5}).items():
            np.testing.assert_array_equal(scores, expected[name])
        assert model.is_file() and not report.exists()
    finally:
        load_runtime.clear()
