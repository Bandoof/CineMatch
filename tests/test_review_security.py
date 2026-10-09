import io
import json
import zipfile

import pytest

from app.recommender import Recommender
from scripts import download_content, download_metadata
from src.metadata import CatalogMetadata, trusted_url
from src.profiles import import_library_profile
from src.semantic import SemanticContent
from src.series import parse_show
from tests.test_library import make_app


def metadata_fixture(tmp_path):
    directory = tmp_path / "data" / "metadata"
    directory.mkdir(parents=True)
    return directory


def test_changed_identity_requeries_instead_of_relabeling_old_metadata(sample, tmp_path, monkeypatch):
    directory = metadata_fixture(tmp_path)
    movies, ratings = sample
    movies = movies.copy()
    movies["imdb_id"] = [f"tt{mid:07}" for mid in movies.movie_id]
    records = {str(row.movie_id): {"original_title": row.title, "imdb_id": row.imdb_id,
               "queried": True, "image_queried": True} for row in movies.itertuples()}
    records["1"].update(original_title="Wrong film (1990)", imdb_id="tt9999999",
                        title_uk="Чужий фільм", page="https://en.wikipedia.org/wiki/Wrong",
                        poster_url="https://upload.wikimedia.org/wrong.jpg")
    path = directory / "catalog.json"
    path.write_text(json.dumps({"items": records}))
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        archive.writestr("ml-latest-small/movies.csv", "movieId,title,genres\n1,Test,Drama\n")
        archive.writestr("ml-latest-small/links.csv", "movieId,imdbId,tmdbId\n1,1,1\n")
    calls = []

    def fetch(url, raw=False):
        calls.append(url)
        if raw:
            return blob.getvalue()
        return {"results": {"bindings": [{"imdb": {"value": "tt0000001"},
                "item": {"value": "http://www.wikidata.org/entity/Q1"},
                "uk": {"value": "Правильний фільм"}}]}}

    monkeypatch.setattr(download_metadata, "ROOT", tmp_path)
    monkeypatch.setattr(download_metadata, "load_app_movies", lambda _: (movies, ratings))
    monkeypatch.setattr(download_metadata, "fetch", fetch)
    monkeypatch.setattr(download_metadata.time, "sleep", lambda _: None)
    download_metadata.download()
    changed = json.loads(path.read_text(encoding="utf-8"))["items"]["1"]
    assert len(calls) == 2
    assert changed["title_uk"] == "Правильний фільм"
    assert "page" not in changed and "poster_url" not in changed
    assert CatalogMetadata(movies, {"schema_version": 1, "items": {"1": changed}}).translated(1)


def test_wikipedia_soft_error_is_retried_and_normalized_title_is_matched(tmp_path, monkeypatch):
    directory = metadata_fixture(tmp_path)
    (directory / "catalog.json").write_text(json.dumps({"items": {"1": {
        "original_title": "Test (2000)", "page": "https://en.wikipedia.org/wiki/test"}}}))
    monkeypatch.setattr(download_content, "ROOT", tmp_path)
    monkeypatch.setattr(download_content.time, "sleep", lambda _: None)
    monkeypatch.setattr(download_content, "fetch", lambda _: {"error": {"code": "maxlag"}})
    with pytest.raises(ValueError, match="retry"):
        download_content.download()
    assert not (directory / "content.json").exists()
    (directory / "content.json").write_text(json.dumps({"schema_version": 1, "items": {"1": {
        "original_title": "Test (2000)", "source_url": "https://en.wikipedia.org/wiki/Wrong",
        "summary_en": "Description from a stale page"}}}))
    calls = []

    def fetch(url):
        calls.append(url)
        return {"query": {"normalized": [{"from": "test", "to": "Test"}],
                "pages": {"1": {"title": "Test", "extract": "Actual source description"}}}}

    monkeypatch.setattr(download_content, "fetch", fetch)
    download_content.download()
    download_content.download()
    assert len(calls) == 1
    assert json.loads((directory / "content.json").read_text(encoding="utf-8"))["items"]["1"]["summary_en"] == "Actual source description"


def test_image_soft_error_does_not_set_completion_flag(sample, tmp_path, monkeypatch):
    directory = metadata_fixture(tmp_path)
    movies, ratings = sample
    movies = movies.copy()
    movies["imdb_id"] = [f"tt{mid:07}" for mid in movies.movie_id]
    records = {str(row.movie_id): {"original_title": row.title, "imdb_id": row.imdb_id,
               "queried": True, "image_queried": True} for row in movies.itertuples()}
    records["1"].update(page="https://en.wikipedia.org/wiki/test", image_queried=False)
    path = directory / "catalog.json"
    path.write_text(json.dumps({"items": records}))
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        archive.writestr("ml-latest-small/movies.csv", "movieId,title,genres\n1,Test,Drama\n")
        archive.writestr("ml-latest-small/links.csv", "movieId,imdbId,tmdbId\n1,1,1\n")
    monkeypatch.setattr(download_metadata, "ROOT", tmp_path)
    monkeypatch.setattr(download_metadata, "load_app_movies", lambda _: (movies, ratings))
    monkeypatch.setattr(download_metadata.time, "sleep", lambda _: None)
    monkeypatch.setattr(download_metadata, "fetch", lambda _, raw=False:
                        blob.getvalue() if raw else {"error": {"code": "maxlag"}})
    with pytest.raises(ValueError, match="retry"):
        download_metadata.download()
    assert not json.loads(path.read_text(encoding="utf-8"))["items"]["1"]["image_queried"]
    monkeypatch.setattr(download_metadata, "fetch", lambda _, raw=False:
                        blob.getvalue() if raw else {"query": {
                            "normalized": [{"from": "test", "to": "Test"}],
                            "pages": {"1": {"title": "Test", "pageimage": "Test.jpg",
                                      "thumbnail": {"source": "https://upload.wikimedia.org/Test.jpg"}}}}})
    download_metadata.download()
    saved = json.loads(path.read_text(encoding="utf-8"))["items"]["1"]
    assert saved["image_queried"] and saved["poster_url"].endswith("Test.jpg")


def test_rating_edit_delete_and_watched_restore_capture_previous_state(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    app.button(key="guide_rate_4").click().run()
    mid = next(iter(app.session_state["ratings"]))
    app.number_input(key=f"edit_{mid}").set_value(1).run()
    assert app.session_state["recommendation_change"]["profile"] == {mid: 4}
    app.button(key=f"remove_{mid}").click().run()
    assert app.session_state["recommendation_change"]["profile"] == {mid: 1}
    app.button(key=f"restore_seen_{mid}").click().run()
    assert mid in app.session_state["recommendation_change"]["watched"]
    assert mid not in app.session_state["watched"]
    assert not app.exception


@pytest.mark.parametrize("payload", [
    '{"1":5,"1":1}', '{"1":NaN}', '{"1":Infinity}',
    '{"nested":' + '[' * 2000 + '0' + ']' * 2000 + '}',
])
def test_malicious_profile_is_rejected(sample, payload):
    engine = Recommender(*sample)
    with pytest.raises(ValueError):
        import_library_profile(engine, payload)


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "https://en.wikipedia.org.evil.example/wiki/Test",
    "https://user:password@en.wikipedia.org/wiki/Test",
    "https://en.wikipedia.org:8080/wiki/Test", "https://[bad/wiki/Test",
    "https://en.wikipedia.org/\\evil", "https://en.wikipedia.org/\nTest",
])
def test_untrusted_description_links_are_rejected(sample, url):
    movies, _ = sample
    source = {"schema_version": 1, "items": {"1": {
        "original_title": movies.iloc[0].title, "source_url": url}}}
    assert trusted_url(url, {"en.wikipedia.org"}) == ""
    assert SemanticContent(movies, source).items[1]["source_url"] == ""


def test_tvmaze_credentials_and_non_https_sources_are_rejected():
    show = {"id": 1, "type": "Scripted", "name": "Test", "genres": [],
            "url": "https://user:password@www.tvmaze.com/shows/1"}
    with pytest.raises(ValueError):
        parse_show(show)
    show["url"] = "https://www.tvmaze.com/shows/1"
    show["image"] = {"medium": "https://user@static.tvmaze.com/image.jpg"}
    assert not parse_show(show)["poster_url"]
