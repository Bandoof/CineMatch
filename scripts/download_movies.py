"""Download the official development catalog; keep its fingerprint and license."""

import hashlib
import io
import json
import ssl
import urllib.request
import zipfile

import certifi

from src.data import ROOT

URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


def download(directory=None):
    directory = directory or ROOT / "data" / "ml-latest-small"
    directory.mkdir(parents=True, exist_ok=True)
    names = ("movies.csv", "ratings.csv", "links.csv", "README.txt")
    if all((directory / name).is_file() for name in names):
        print("Extended movie catalog is already installed.")
        return
    context = ssl.create_default_context(cafile=certifi.where())
    request = urllib.request.Request(URL, headers={"User-Agent": "CineMatch/4.0"})
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        blob = response.read(10_000_001)
    if len(blob) > 10_000_000:
        raise ValueError("Movie catalog archive is too large.")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        contents = {}
        for name in names:
            member = archive.getinfo("ml-latest-small/" + name)
            if member.file_size > 20_000_000:
                raise ValueError("Movie catalog file is too large.")
            contents[name] = archive.read(member)
    for name, contents in contents.items():
        (directory / name).write_bytes(contents)
    (directory / "source.json").write_text(json.dumps({"source": URL,
        "archive_sha256": hashlib.sha256(blob).hexdigest(),
        "scope": "Development snapshot; not a stable research benchmark."}, indent=2), encoding="utf-8")
    print("Installed extended catalog with official ratings and IMDb identities.")


if __name__ == "__main__":
    download()
