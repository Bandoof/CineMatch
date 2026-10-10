"""Small, explicit CC0 metadata reads; no scraping, artwork or generated translations."""

import re
from dataclasses import replace
from datetime import date, datetime, timezone

from src.modern_catalog import CatalogTitle, clean_text, valid_date

GENRES = {
    "science fiction film": "Sci-Fi",
    "drama film": "Drama",
    "comedy film": "Comedy",
    "action film": "Action",
    "thriller film": "Thriller",
    "horror film": "Horror",
    "romantic comedy film": "Romance",
    "documentary film": "Documentary",
    "animated film": "Animation",
    "adventure film": "Adventure",
    "crime film": "Crime",
}


def claim_values(entity, property_id, limit=30):
    claims = entity.get("claims", {})
    rows = claims.get(property_id, []) if isinstance(claims, dict) else []
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows[:limit]:
        if not isinstance(row, dict) or row.get("rank") == "deprecated":
            continue
        snak = row.get("mainsnak", {})
        data = snak.get("datavalue", {}) if isinstance(snak, dict) else {}
        if isinstance(data, dict) and "value" in data:
            result.append(data["value"])
    return result


def entity_ids(entity, property_id, limit=20):
    return [
        value["id"]
        for value in claim_values(entity, property_id, limit)
        if isinstance(value, dict) and re.fullmatch(r"Q[1-9]\d{0,8}", str(value.get("id", "")))
    ]


def label(entity, language="en", field="labels"):
    labels = entity.get(field, {})
    item = labels.get(language, {}) if isinstance(labels, dict) else {}
    return clean_text(item.get("value")) if isinstance(item, dict) else ""


def read_entities(client, identities, online=False, props="labels|descriptions|claims"):
    identities = list(dict.fromkeys(identities))
    if len(identities) > 80 or any(not re.fullmatch(r"Q[1-9]\d{0,8}", q) for q in identities):
        raise ValueError("Choose at most 80 explicit Wikidata entities.")
    entities, stamps, statuses = {}, {}, []
    for start in range(0, len(identities), 20):
        batch = identities[start : start + 20]
        response = client.fetch(
            "Wikidata",
            "/w/api.php",
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": props,
                "languages": "uk|en",
                "format": "json",
            },
            online,
        )
        statuses.append(response.status)
        payload = response.payload
        records = payload.get("entities", {}) if isinstance(payload, dict) else {}
        if not isinstance(records, dict):
            continue
        for identity in batch:
            entity = records.get(identity)
            if (
                isinstance(entity, dict)
                and entity.get("id") == identity
                and "missing" not in entity
            ):
                entities[identity] = entity
                stamps[identity] = response.fetched_at
    status = next((s for s in statuses if s not in ("cache", "fetched")), None)
    return entities, stamps, status or ("fetched" if "fetched" in statuses else "cache")


def parse_entity(entity, media_type, entities, fetched_at=None):
    identity = entity.get("id", "")
    if not re.fullmatch(r"Q[1-9]\d{0,8}", identity) or media_type not in ("Movie", "Series"):
        raise ValueError("Invalid curated Wikidata identity.")
    english, ukrainian = label(entity), label(entity, "uk")
    originals = claim_values(entity, "P1476")
    original = next((clean_text(v.get("text")) for v in originals if isinstance(v, dict)), "")
    original = original or english or ukrainian
    dates = []
    for prop in ("P577",) if media_type == "Movie" else ("P580", "P577"):
        for value in claim_values(entity, prop):
            if isinstance(value, dict) and value.get("precision", 0) >= 11:
                day = valid_date(str(value.get("time", "")).lstrip("+")[:10])
                if day:
                    dates.append(day)
    genres = [label(entities.get(q, {})) for q in entity_ids(entity, "P136")]
    genres = tuple(dict.fromkeys(GENRES.get(g, g) for g in genres if g))[:30]
    directors = tuple(label(entities.get(q, {})) for q in entity_ids(entity, "P57", 10))
    cast = tuple(label(entities.get(q, {})) for q in entity_ids(entity, "P161", 12))
    imdb_values = {
        v
        for v in claim_values(entity, "P345")
        if isinstance(v, str) and re.fullmatch(r"tt\d{7,10}", v)
    }
    imdb = next(iter(imdb_values)) if len(imdb_values) == 1 else ""
    release_year = int(min(dates)[:4]) if dates else 0
    # Keep a source-provided year while withholding an ambiguous precise date.
    if dates and (date.fromisoformat(max(dates)) - date.fromisoformat(min(dates))).days > 180:
        dates = []
    runtime = None
    for value in claim_values(entity, "P2047"):
        if isinstance(value, dict) and value.get("unit") == "http://www.wikidata.org/entity/Q7727":
            try:
                minutes = float(value.get("amount", ""))
                if minutes.is_integer() and 0 < minutes < 1000:
                    runtime = int(minutes)
            except (ValueError, TypeError):
                pass
    return CatalogTitle(
        "Wikidata",
        int(identity[1:]),
        media_type,
        original,
        title_en=english,
        title_uk=ukrainian,
        release_date=min(dates) if dates else "",
        release_year=release_year,
        genres=genres,
        runtime=runtime,
        imdb_id=imdb,
        cast=tuple(n for n in cast if n),
        creators=tuple(n for n in directors if n),
        short_description_en=label(entity, field="descriptions"),
        short_description_uk=label(entity, "uk", "descriptions"),
        fetched_utc=datetime.fromtimestamp(fetched_at, timezone.utc).isoformat()
        if fetched_at is not None
        else "",
        localization_source=f"https://www.wikidata.org/wiki/{identity}" if ukrainian else "",
    )


def wikidata_titles(client, curated, online=False):
    curated = list(curated)
    entities, stamps, status = read_entities(client, [q for q, _ in curated], online)
    needed = list(
        dict.fromkeys(
            q
            for prop in ("P136", "P57", "P161")
            for entity in entities.values()
            for q in entity_ids(entity, prop, 12)
        )
    )[:80]
    related, _, _ = read_entities(client, needed, online, props="labels")
    titles = []
    for identity, kind in curated:
        if identity in entities:
            try:
                titles.append(parse_entity(entities[identity], kind, related, stamps[identity]))
            except (ValueError, TypeError):
                continue
    return titles, status


def localize_series(series, labels):
    """Unique IMDb + series + premiere year; source/date retained separately."""
    matches = [
        t
        for t in labels
        if t.media_type == "Series"
        and t.imdb_id
        and t.imdb_id == series.imdb_id
        and t.year
        and t.year == series.year
    ]
    if len(matches) != 1 or not matches[0].title_uk:
        return series
    title = matches[0]
    return replace(
        series,
        title_uk=title.title_uk,
        localization_source=title.source_url,
        short_description_uk=title.short_description_uk,
    )
