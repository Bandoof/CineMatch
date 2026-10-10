"""Explicit, pinned public research downloads to a separate cache directory."""

import argparse
import ssl
import urllib.request
import zipfile
from pathlib import Path

import certifi

from src.research_embeddings import MODEL_ID, REVISION, TOKENIZER_HASH, WEIGHT_HASH
from src.research_protocol import file_digest, write_new_json

DATA_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
DATA_HASH = "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20"


def fetch(url, destination, maximum, expected_hash=None):
    if destination.exists():
        if expected_hash is not None and file_digest(destination) != expected_hash:
            raise ValueError("Existing research cache checksum mismatch; not replacing it.")
        return
    destination.parent.mkdir(exist_ok=True, parents=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "CineMatch-v12-research"})
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with (
            urllib.request.urlopen(request, timeout=45, context=context) as response,
            temporary.open("wb") as stream,
        ):
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > maximum:
                    raise ValueError("Research download exceeds its explicit size limit.")
                stream.write(chunk)
        if expected_hash is not None and file_digest(temporary) != expected_hash:
            raise ValueError("Downloaded research input checksum mismatch.")
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)


def download(directory, embeddings=False):
    """Only three allowlisted MovieLens members; no generic archive extraction."""
    directory.mkdir(exist_ok=True, parents=True)
    archive_path = directory / "ml-1m.zip"
    fetch(DATA_URL, archive_path, 20_000_000, DATA_HASH)
    data_dir = directory / "ml-1m"
    data_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for name in ("movies.dat", "ratings.dat", "README"):
            member = archive.getinfo("ml-1m/" + name)
            if member.file_size > 40_000_000:
                raise ValueError("Oversized research archive member.")
            content = archive.read(member)
            destination = data_dir / name
            if destination.exists() and destination.read_bytes() != content:
                raise ValueError("Existing research dataset differs; not replacing it.")
            if not destination.exists():
                destination.write_bytes(content)
    if embeddings:
        cache = directory / "minilm"
        files = (
            ("onnx/model_quint8_avx2.onnx", WEIGHT_HASH, 150_000_000),
            ("tokenizer.json", TOKENIZER_HASH, 15_000_000),
            ("README.md", None, 100_000),
        )
        receipt = []
        for name, checksum, limit in files:
            destination = cache / name
            fetch(
                f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}",
                destination,
                limit,
                checksum,
            )
            receipt.append(
                {
                    "file": name,
                    "bytes": destination.stat().st_size,
                    "sha256": file_digest(destination),
                }
            )
        if not (cache / "receipt.json").exists():
            write_new_json(
                cache / "receipt.json",
                {"revision": REVISION, "license": "Apache-2.0", "files": receipt},
            )
    print("Verified public research cache:", directory, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        required=True,
        help="Separate research cache; never point this at a personal profile directory.",
    )
    parser.add_argument("--embeddings", action="store_true")
    args = parser.parse_args()
    download(args.directory, args.embeddings)


if __name__ == "__main__":
    main()
