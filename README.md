# IMDb Content Upload & Review System

A Flask + MongoDB API for ingesting and querying IMDb-style movie/show data. Handles CSV uploads up to **1 GB** using streaming + batch inserts so memory usage stays flat regardless of file size.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.x

No Python, pip, or MongoDB installation needed on your machine.

---

## Run the Project

```bash
git clone <repo-url>
cd imdb-content-system

cp .env.example .env

docker-compose up --build
```

The API will be available at **http://localhost:5000**.

MongoDB data is persisted in a named Docker volume and survives container restarts.

---

## Run Tests

```bash
# Inside Docker
docker-compose exec app pytest -v

# Or locally
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -v
```

---

## API Documentation

### `GET /health`

Checks that the app and MongoDB are reachable.

**Response `200`:**
```json
{ "status": "ok", "database": "connected" }
```

**Response `503`:**
```json
{ "status": "degraded", "database": "unreachable" }
```

---

### `POST /api/v1/movies/upload`

Upload a CSV file of movies. Streams the file in 1000-row batches — safe for files up to 1 GB.

**Request:** `multipart/form-data` with a `file` field containing a `.csv` file.

Both IMDb TSV-style columns and the provided sample CSV columns are detected automatically. IMDb's `\N` null sentinel is accepted for any optional field. Rows with no recognisable title field are skipped and counted.

**Response `200`:**
```json
{
  "inserted": 45428,
  "skipped": 0,
  "message": "Upload complete. 45428 inserted, 0 skipped."
}
```

**Response `422`:**
```json
{
  "error": "No rows could be inserted. Check that your CSV uses recognised column names...",
  "code": "NO_VALID_ROWS",
  "inserted": 0,
  "skipped": 150
}
```

**curl example:**
```bash
curl -X POST http://localhost:5000/api/v1/movies/upload \
  -F "file=@sample_movies.csv"
```

---

### `GET /api/v1/movies`

List movies with filtering, sorting, and pagination.

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `page` | int | `1` | ≥ 1 | Page number |
| `page_size` | int | `20` | 1–100 | Results per page |
| `year` | int | — | 1888–2100 | Filter by release year |
| `language` | string | — | max 100 chars | Filter by language (case-insensitive) |
| `sort_by` | string | `release_date` | `release_date` or `ratings` | Sort field |
| `order` | string | `desc` | `asc` or `desc` | Sort direction |

**Response `200`:**
```json
{
  "data": [
    {
      "primary_title": "Interstellar",
      "start_year": 2014,
      "language": "English",
      "average_rating": 8.6,
      "genres": ["Sci-Fi", "Drama"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45428,
  "total_pages": 2272
}
```

**curl examples:**
```bash
curl http://localhost:5000/api/v1/movies

curl "http://localhost:5000/api/v1/movies?year=2020&language=English"

curl "http://localhost:5000/api/v1/movies?sort_by=ratings&order=desc&page_size=10"

curl "http://localhost:5000/api/v1/movies?sort_by=release_date&order=asc"
```

---

## Error Response Format

```json
{
  "error": "Human-readable description",
  "code": "MACHINE_READABLE_CODE"
}
```

| HTTP Status | Code | When |
|-------------|------|------|
| 400 | `MISSING_FILE` | No `file` field in upload request |
| 400 | `INVALID_PARAMS` | Bad query parameter value |
| 413 | `FILE_TOO_LARGE` | File exceeds 2 GB limit |
| 422 | `NO_VALID_ROWS` | CSV had rows but every row was rejected |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## Design Decisions

### Streaming CSV for large files

Loading a 1 GB file with `file.read()` would crash the server. Instead, the endpoint reads one line at a time and accumulates rows until a batch of 1000 is ready, flushes to MongoDB, then discards the batch. Peak memory usage stays constant regardless of file size.

### Batch inserts

One `insertOne` call per row would mean tens of thousands of round-trips to MongoDB for a large file. Batching 1000 rows into a single `insert_many(ordered=False)` call cuts that overhead significantly. `ordered=False` ensures a bad row doesn't abort the rest of the batch.

### Input validation with Pydantic

Query parameters are validated by a Pydantic model — type coercion, range checks, and allowed values are declared once and enforced automatically. Keeps the route handler clean.

### MongoDB indexes

Four indexes are created at startup so the evaluator doesn't need to set anything up manually:

| Index | Purpose |
|-------|---------|
| `start_year` | Filter by year |
| `language` | Filter by language |
| `average_rating` | Sort by ratings |
| `(start_year, language)` | Combined filter in one lookup |

---

## Known Limitations

Upload is synchronous — for files close to 1 GB the HTTP request stays open for the full duration. In a production system this would be handled by a background task queue (Celery + SQS) that returns a job ID immediately and processes the file async.

---

## Project Structure

```
imdb-content-system/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── routes/
│   │   ├── movies.py
│   │   └── health.py
│   ├── schemas/
│   │   └── movie_schemas.py
│   ├── services/
│   │   └── movie_service.py
│   ├── repositories/
│   │   └── movie_repository.py
│   ├── models/
│   │   └── movie.py
│   └── utils/
│       └── csv_parser.py
├── tests/
│   ├── conftest.py
│   ├── test_upload.py
│   └── test_movies.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── sample_movies.csv
├── postman_collection.json
├── IMPLEMENTATION_NOTES.md
└── README.md
```