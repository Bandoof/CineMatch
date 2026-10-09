"""Optional cached CPU encoder for research, never auto-downloads at app startup."""

import json
from pathlib import Path

import numpy as np

from src.research_protocol import digest_json, file_digest

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
WEIGHT_HASH = "98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f"
TOKENIZER_HASH = "2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8"


def mean_pool(hidden, mask):
    hidden, mask = np.asarray(hidden), np.asarray(mask)
    if hidden.ndim != 3 or mask.shape != hidden.shape[:2] or not np.isfinite(hidden).all():
        raise ValueError("Invalid encoder output/mask.")
    if not np.isin(mask, [0, 1]).all() or (mask.sum(axis=1) == 0).any():
        raise ValueError("Attention mask must contain real tokens.")
    expanded = mask[..., None]
    vectors = (hidden * expanded).sum(axis=1) / expanded.sum(axis=1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if (norms < 1e-10).any():
        raise ValueError("Encoder produced an empty vector.")
    return (vectors / norms).astype(np.float32)


class CachedEncoder:
    def __init__(self, directory):
        directory = Path(directory)
        model_path = directory / "onnx/model_quint8_avx2.onnx"
        tokenizer_path = directory / "tokenizer.json"
        # Check integrity before opening a binary model, and never execute Hub code.
        if file_digest(model_path) != WEIGHT_HASH or file_digest(tokenizer_path) != TOKENIZER_HASH:
            raise ValueError("Cached embedding inputs do not match the pinned revision.")
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as error:
            raise ImportError(
                "Install requirements-research.txt for the optional CPU encoder."
            ) from error
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_padding(pad_id=0, pad_token="<pad>")
        self.tokenizer.enable_truncation(max_length=128)

    def encode(self, texts, batch_size=32):
        if (
            batch_size < 1
            or not texts
            or any(not isinstance(text, str) or not text.strip() for text in texts)
        ):
            raise ValueError("Nonempty text batches are required.")
        vectors = []
        for start in range(0, len(texts), batch_size):
            tokens = self.tokenizer.encode_batch(list(texts[start : start + batch_size]))
            inputs = {
                "input_ids": np.array([token.ids for token in tokens], dtype=np.int64),
                "attention_mask": np.array(
                    [token.attention_mask for token in tokens], dtype=np.int64
                ),
                "token_type_ids": np.array([token.type_ids for token in tokens], dtype=np.int64),
            }
            feed = {item.name: inputs[item.name] for item in self.session.get_inputs()}
            hidden = self.session.run(None, feed)[0]
            vectors.append(mean_pool(hidden, inputs["attention_mask"]))
        result = np.concatenate(vectors)
        if result.shape != (len(texts), 384):
            raise ValueError("Unexpected multilingual model dimensions.")
        return result


def save_vectors(path, ids, features, texts):
    path = Path(path)
    # Exclusive creation, numeric data only. Fingerprint all text and ID order.
    with path.open("xb") as stream:
        np.savez_compressed(
            stream,
            schema_version=1,
            ids=ids,
            features=features,
            fingerprint=digest_json({"ids": np.asarray(ids).tolist(), "texts": texts}),
            encoder=MODEL_ID,
            revision=REVISION,
            weights_sha256=WEIGHT_HASH,
        )


def load_vectors(path, ids, texts):
    with np.load(path, allow_pickle=False) as archive:
        fingerprint = digest_json({"ids": np.asarray(ids).tolist(), "texts": texts})
        if (
            int(archive["schema_version"]) != 1
            or str(archive["fingerprint"]) != fingerprint
            or str(archive["encoder"]) != MODEL_ID
            or str(archive["revision"]) != REVISION
            or str(archive["weights_sha256"]) != WEIGHT_HASH
            or not np.array_equal(archive["ids"], ids)
        ):
            raise ValueError("Embedding artifact does not match its inputs/encoder.")
        features = archive["features"].copy()
    if (
        features.shape != (len(ids), 384)
        or not np.isfinite(features).all()
        or not np.allclose(np.linalg.norm(features, axis=1), 1, atol=1e-5)
    ):
        raise ValueError("Invalid cached embedding vectors.")
    return features


def cache_receipt(directory):
    return {
        "model": MODEL_ID,
        "revision": REVISION,
        "license": "Apache-2.0",
        "backend": "ONNX dynamic quint8 AVX2 / CPUExecutionProvider / one thread",
        "weights_sha256": WEIGHT_HASH,
        "tokenizer_sha256": TOKENIZER_HASH,
        "cache_bytes": sum(p.stat().st_size for p in Path(directory).rglob("*") if p.is_file()),
        "source": "https://huggingface.co/" + MODEL_ID,
        "download_receipt": json.loads(
            (Path(directory) / "receipt.json").read_text(encoding="utf-8")
        ),
    }
