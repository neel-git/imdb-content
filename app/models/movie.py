import ast
from datetime import datetime, timezone

IMDB_NULL = r"\N"

COLUMN_MAP = {

    "tconst": "tconst",
    "titletype": "title_type",        "title_type": "title_type",
    "primarytitle": "primary_title",  "primary_title": "primary_title",
    "originaltitle": "original_title","original_title": "original_title",
    "isadult": "is_adult",            "is_adult": "is_adult",
    "startyear": "start_year",        "start_year": "start_year",
    "endyear": "end_year",            "end_year": "end_year",
    "runtimeminutes": "runtime_minutes","runtime_minutes": "runtime_minutes",
    "genres": "genres",
    "averagerating": "average_rating","average_rating": "average_rating",
    "numvotes": "num_votes",          "num_votes": "num_votes",
    "language": "language",

    "title": "primary_title",
    "vote_average": "average_rating", 
    "vote_count": "num_votes",
    "runtime": "runtime_minutes",
    "languages": "languages",
    "release_date": "release_date",
    "original_language": "original_language",
    "budget": "budget",
    "revenue": "revenue",
    "status": "status",
    "overview": "overview",
    "homepage": "homepage",
    "genre_id": "genre_id",
    "production_company_id": "production_company_id",
}


def _null(value):
    """Return None for IMDb's \\N sentinel, empty strings, and Python None."""
    if value is None:
        return None
    v = str(value).strip()
    return None if v == IMDB_NULL or v == "" else v


def _parse_language(raw: str | None) -> str | None:
    """
    Handle two formats:
      - plain string:          "English"
      - Python list literal:   "['English', 'Français']"
    Returns the first language, or None if the list is empty / unparseable.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw.startswith("["):
        try:
            langs = ast.literal_eval(raw)
            return langs[0].strip() if langs else None
        except (ValueError, SyntaxError):
            return None
    return raw or None


def _extract_year(row: dict) -> int | None:
    """
    Return start_year from either the direct 'start_year' field
    or by parsing the 'release_date' field (YYYY-MM-DD).
    """
    raw = _null(row.get("start_year"))
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            pass

    date_raw = _null(row.get("release_date"))
    if date_raw:
        try:
            return datetime.strptime(date_raw, "%Y-%m-%d").year
        except ValueError:
            pass
    return None


def _safe_int(value: str | None) -> int | None:
    """int() that also accepts float strings like '5415.0'."""
    v = _null(value)
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _safe_float(value: str | None) -> float | None:
    v = _null(value)
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _clean_key(k: str) -> str:
    """Strip whitespace, UTF-8 BOM (﻿), and lowercase a CSV header."""
    return k.strip().lstrip("﻿").lower()


def validate_and_transform(raw_row: dict):
    """
    Map a raw CSV row to a MongoDB document.
    Handles both IMDb TSV column names and the assignment dataset column names.

    Returns (document, None) on success or (None, reason_string) on failure.
    """
    # Normalise all incoming column names via COLUMN_MAP.
    # _clean_key strips BOM so Windows-generated CSVs work correctly.
    row = {
        COLUMN_MAP.get(_clean_key(k), _clean_key(k)): v
        for k, v in raw_row.items()
        if k is not None
    }

    # ── Required field ────────────────────────────────────────────────────────
    primary_title = _null(row.get("primary_title"))
    if not primary_title:
        return None, "missing primary_title"

    # ── Type coercions ────────────────────────────────────────────────────────
    try:
        start_year      = _extract_year(row)
        end_year        = _safe_int(row.get("end_year"))
        runtime_minutes = _safe_int(row.get("runtime_minutes"))
        average_rating  = _safe_float(row.get("average_rating"))
        num_votes       = _safe_int(row.get("num_votes"))   # handles "5415.0"
        budget          = _safe_float(row.get("budget"))
        revenue         = _safe_float(row.get("revenue"))

        is_adult_raw = _null(row.get("is_adult"))
        is_adult = bool(int(is_adult_raw)) if is_adult_raw is not None else False

        # genres: comma-separated string (IMDb) or absent (assignment dataset)
        genres_raw = _null(row.get("genres"))
        genres = [g.strip() for g in genres_raw.split(",")] if genres_raw else []

        # language: plain string OR Python list literal "['English', 'Français']"
        language = _parse_language(_null(row.get("language")) or _null(row.get("languages")))

    except (ValueError, TypeError) as exc:
        return None, f"type coercion failed: {exc}"

    document = {
        "tconst":           _null(row.get("tconst")),
        "title_type":       _null(row.get("title_type")),
        "primary_title":    primary_title,
        "original_title":   _null(row.get("original_title")),
        "is_adult":         is_adult,
        "start_year":       start_year,
        "end_year":         end_year,
        "runtime_minutes":  runtime_minutes,
        "genres":           genres,
        "average_rating":   average_rating,
        "num_votes":        num_votes,
        "language":         language,
        # Extra fields from the assignment dataset (stored, ignored if absent)
        "budget":           budget,
        "revenue":          revenue,
        "status":           _null(row.get("status")),
        "overview":         _null(row.get("overview")),
        "original_language":_null(row.get("original_language")),
        "created_at":       datetime.now(timezone.utc),
    }
    return document, None
