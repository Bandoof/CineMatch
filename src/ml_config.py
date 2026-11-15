"""Read ALS hyperparameters from configs/ml.json, the single source of truth."""

import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "ml.json"
PARAMETERS = ("factors", "epochs", "regularization", "bias_regularization", "random_state")


def model_parameters(section, path=CONFIG):
    """BiasedMF keyword arguments for one named section, e.g. "benchmark_1m"."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or section not in document:
        raise ValueError(f"Unknown ML configuration section: {section}")
    values = document[section]
    missing = [name for name in PARAMETERS if name not in values]
    if missing:
        raise ValueError(f"ML configuration {section} lacks {', '.join(missing)}")
    return {name: values[name] for name in PARAMETERS}
