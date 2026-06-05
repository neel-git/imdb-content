import io
import csv
import pytest
import mongomock
from datetime import datetime, timezone
import app.db as db_module
from app.config import Config

class TestConfig(Config):
    TESTING = True
    MONGO_URI = "mongomock://localhost"
    DB_NAME = "test_imdb_db"


@pytest.fixture(scope="function")
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture(scope="function")
def app(mongo_client, monkeypatch):
    test_collection = mongo_client[TestConfig.DB_NAME][TestConfig.COLLECTION_NAME]

    test_db = mongo_client[TestConfig.DB_NAME]

    monkeypatch.setattr(db_module, "_client", mongo_client)
    monkeypatch.setattr(db_module, "get_db", lambda: test_db)
    monkeypatch.setattr(db_module, "get_collection", lambda: test_collection)

    import app.services.movie_service as svc
    import app.routes.health as health_mod
    monkeypatch.setattr(svc, "get_collection", lambda: test_collection)
    monkeypatch.setattr(health_mod, "get_db", lambda: test_db)

    from app import create_app
    flask_app = create_app(TestConfig)
    flask_app.config["TESTING"] = True

    yield flask_app

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture(scope="function")
def collection(app, mongo_client):
    return mongo_client[TestConfig.DB_NAME][TestConfig.COLLECTION_NAME]

@pytest.fixture(scope="function")
def seeded_collection(collection):
    now = datetime.now(timezone.utc)
    docs = [
        {
            "tconst": "tt0000001",
            "primary_title": "The Matrix",
            "title_type": "movie",
            "start_year": 1999,
            "language": "English",
            "average_rating": 8.7,
            "num_votes": 1800000,
            "genres": ["Action", "Sci-Fi"],
            "created_at": now,
        },
        {
            "tconst": "tt0000002",
            "primary_title": "Inception",
            "title_type": "movie",
            "start_year": 2010,
            "language": "English",
            "average_rating": 8.8,
            "num_votes": 2200000,
            "genres": ["Action", "Thriller"],
            "created_at": now,
        },
        {
            "tconst": "tt0000003",
            "primary_title": "Parasite",
            "title_type": "movie",
            "start_year": 2019,
            "language": "Korean",
            "average_rating": 8.5,
            "num_votes": 700000,
            "genres": ["Drama", "Thriller"],
            "created_at": now,
        },
        {
            "tconst": "tt0000004",
            "primary_title": "Interstellar",
            "title_type": "movie",
            "start_year": 2014,
            "language": "English",
            "average_rating": 8.6,
            "num_votes": 1600000,
            "genres": ["Sci-Fi", "Drama"],
            "created_at": now,
        },
        {
            "tconst": "tt0000005",
            "primary_title": "RRR",
            "title_type": "movie",
            "start_year": 2022,
            "language": "Telugu",
            "average_rating": 7.8,
            "num_votes": 300000,
            "genres": ["Action", "Drama"],
            "created_at": now,
        },
    ]
    collection.insert_many(docs)
    return collection

def make_csv_bytes(rows: list[dict], headers: list[str] | None = None) -> bytes:
    """Build a properly-quoted CSV as bytes from a list of dicts."""
    if not rows:
        return b""
    if headers is None:
        headers = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(h, "") for h in headers])
    return buf.getvalue().encode("utf-8")


VALID_HEADERS = [
    "tconst", "title_type", "primary_title", "original_title",
    "is_adult", "start_year", "end_year", "runtime_minutes",
    "genres", "average_rating", "num_votes", "language",
]

def make_valid_row(overrides=None):
    base = {
        "tconst": "tt9999999",
        "title_type": "movie",
        "primary_title": "Test Movie",
        "original_title": "Test Movie",
        "is_adult": "0",
        "start_year": "2020",
        "end_year": r"\N",
        "runtime_minutes": "120",
        "genres": "Action,Drama",
        "average_rating": "7.5",
        "num_votes": "10000",
        "language": "English",
    }
    if overrides:
        base.update(overrides)
    return base
