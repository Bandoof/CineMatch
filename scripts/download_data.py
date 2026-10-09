"""Download directly from GroupLens; never redistribute the dataset in the repo."""

import hashlib
import io
import json
import urllib.request
import ssl
import certifi
import zipfile

from src.data import ROOT

URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"


def download(directory=None):
    directory = directory or ROOT / "data" / "ml-100k"
    directory.mkdir(parents=True, exist_ok=True)
    if all((directory / name).exists() for name in ("u.data", "u.item", "README")):
        print(f"MovieLens is already present in {directory}")
        return
    request = urllib.request.Request(URL, headers={"User-Agent": "CineMatch-Research/1.0"})
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        payload = response.read(20_000_001)
    expected = "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229"
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("MovieLens archive checksum mismatch; refusing changed data.")
    if len(payload) > 20_000_000:
        raise ValueError("Unexpectedly large MovieLens archive.")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        # Explicit allowlist; no arbitrary ZIP path extraction or demographics.
        for name in ("u.data", "u.item", "README"):
            member = archive.getinfo(f"ml-100k/{name}")
            if member.file_size > 20_000_000:
                raise ValueError("Unexpected archive member size.")
        for name in ("u.data", "u.item", "README"):
            (directory / name).write_bytes(archive.read(f"ml-100k/{name}"))
    (directory / "source.json").write_text(json.dumps({
        "source": URL, "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "files": ["u.data", "u.item", "README"],
    }, indent=2), encoding="utf-8")
    print(f"Downloaded MovieLens 100K to {directory}")


if __name__ == "__main__":
    download()
