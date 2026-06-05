import io
import pytest
from tests.conftest import make_csv_bytes, make_valid_row, VALID_HEADERS

UPLOAD_URL = "/api/v1/movies/upload"

# Assignment-dataset column names
ASSIGNMENT_HEADERS = [
    "budget", "homepage", "original_language", "original_title",
    "overview", "release_date", "revenue", "runtime", "status",
    "title", "vote_average", "vote_count", "production_company_id",
    "genre_id", "languages",
]

def make_assignment_row(overrides=None):
    base = {
        "budget": "30000000.0",
        "homepage": "",
        "original_language": "en",
        "original_title": "Test Movie",
        "overview": "A test movie overview.",
        "release_date": "2020-06-15",
        "revenue": "100000000.0",
        "runtime": "120",
        "status": "Released",
        "title": "Test Movie",
        "vote_average": "7.5",
        "vote_count": "10000.0",
        "production_company_id": "1",
        "genre_id": "28",
        "languages": "['English']",
    }
    if overrides:
        base.update(overrides)
    return base


def _upload(client, data: bytes, filename: str = "movies.csv"):
    return client.post(
        UPLOAD_URL,
        data={"file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


# Test 1: Valid IMDb-format CSV with 3 rows
def test_upload_valid_csv(client):
    rows = [make_valid_row({"tconst": f"tt000000{i}", "primary_title": f"Movie {i}"}) for i in range(3)]
    csv_bytes = make_csv_bytes(rows, VALID_HEADERS)

    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 3
    assert data["skipped"] == 0
    assert "inserted" in data["message"]


# Test 2: Non-CSV file extension rejected
def test_upload_rejects_non_csv(client):
    resp = _upload(client, b"some text content", filename="data.txt")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_FILE_TYPE"


# Test 3: No file in request
def test_upload_missing_file(client):
    resp = client.post(UPLOAD_URL, data={}, content_type="multipart/form-data")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "MISSING_FILE"


# Test 4: Rows with missing primary_title are skipped
def test_upload_skips_invalid_rows(client):
    valid_row = make_valid_row()
    invalid_row = make_valid_row({"primary_title": ""})
    rows = [valid_row, invalid_row, make_valid_row({"tconst": "tt0000099", "primary_title": "Another"})]
    csv_bytes = make_csv_bytes(rows, VALID_HEADERS)

    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 2
    assert data["skipped"] == 1


# Test 5: IMDb \\N sentinel treated as null
def test_upload_handles_imdb_null_sentinel(client):
    row = make_valid_row({"end_year": r"\N", "runtime_minutes": r"\N", "average_rating": r"\N"})
    csv_bytes = make_csv_bytes([row], VALID_HEADERS)

    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 1
    assert data["skipped"] == 0


# Test 6: Batch boundary — 1001 rows all inserted
def test_upload_batch_boundary(client):
    rows = [make_valid_row({"tconst": f"tt{i:07d}", "primary_title": f"Movie {i}"}) for i in range(1001)]
    csv_bytes = make_csv_bytes(rows, VALID_HEADERS)

    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 1001
    assert data["skipped"] == 0


# Test 7: Empty CSV (header only) — not an error
def test_upload_empty_csv(client):
    csv_bytes = (",".join(VALID_HEADERS) + "\n").encode("utf-8")
    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 0
    assert data["skipped"] == 0


# Test 8: All rows skipped returns 422, not 200
def test_upload_all_skipped_returns_422(client):
    # CSV with data rows but no recognisable title column
    csv_bytes = b"foo,bar\nval1,val2\nval3,val4\n"
    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 422
    assert data["code"] == "NO_VALID_ROWS"
    assert data["inserted"] == 0
    assert data["skipped"] == 2


# Test 9: Assignment dataset column format (title, vote_average, etc.)
def test_upload_assignment_format(client):
    rows = [
        make_assignment_row({"title": "Toy Story", "release_date": "1995-10-30"}),
        make_assignment_row({"title": "Jumanji",   "release_date": "1995-12-15"}),
    ]
    csv_bytes = make_csv_bytes(rows, ASSIGNMENT_HEADERS)

    resp = _upload(client, csv_bytes)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["inserted"] == 2
    assert data["skipped"] == 0


# Test 10: release_date parsed to start_year correctly
def test_upload_release_date_parsed_to_year(client, collection):
    row = make_assignment_row({"title": "Year Test", "release_date": "2005-07-04"})
    csv_bytes = make_csv_bytes([row], ASSIGNMENT_HEADERS)

    _upload(client, csv_bytes)

    doc = collection.find_one({"primary_title": "Year Test"})
    assert doc is not None
    assert doc["start_year"] == 2005


# Test 11: languages list string parsed to first language
def test_upload_languages_list_parsed(client, collection):
    row = make_assignment_row({"title": "Lang Test", "languages": "['Korean', 'English']"})
    csv_bytes = make_csv_bytes([row], ASSIGNMENT_HEADERS)

    _upload(client, csv_bytes)

    doc = collection.find_one({"primary_title": "Lang Test"})
    assert doc is not None
    assert doc["language"] == "Korean"


# Test 12: vote_count as float string inserted as integer
def test_upload_vote_count_float_string(client, collection):
    row = make_assignment_row({"title": "Vote Test", "vote_count": "5415.0"})
    csv_bytes = make_csv_bytes([row], ASSIGNMENT_HEADERS)

    _upload(client, csv_bytes)

    doc = collection.find_one({"primary_title": "Vote Test"})
    assert doc is not None
    assert doc["num_votes"] == 5415
    assert isinstance(doc["num_votes"], int)
