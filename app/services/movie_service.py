import math
import re
from pymongo import ASCENDING, DESCENDING
from app.db import get_collection
from app.models.movie import validate_and_transform
from app.utils.csv_parser import stream_csv_batches
from app.repositories.movie_repository import bulk_insert, find_movies
from app.config import Config

SORT_FIELD_MAP = {
    "ratings": "average_rating",
    "release_date": "start_year",
}

ORDER_MAP = {
    "asc": ASCENDING,
    "desc": DESCENDING,
}

def upload_csv(file_storage) -> dict:
    """
    Stream-parse the uploaded CSV and insert valid documents in batches.
    Memory usage is O(batch_size) regardless of file size.
    """
    collection = get_collection()
    batch_size = Config.BATCH_SIZE

    inserted_total = 0
    skipped_total = 0
    valid_batch = []

    file_storage.stream.seek(0)
    for raw_batch in stream_csv_batches(file_storage.stream, batch_size):
        for raw_row in raw_batch:
            doc, error = validate_and_transform(raw_row)
            if error:
                skipped_total += 1
                continue
            valid_batch.append(doc)

            if len(valid_batch) >= batch_size:
                inserted_total += bulk_insert(collection, valid_batch)
                valid_batch = []

    if valid_batch:
        inserted_total += bulk_insert(collection, valid_batch)

    return {
        "inserted": inserted_total,
        "skipped": skipped_total,
        "message": f"Upload complete. {inserted_total} inserted, {skipped_total} skipped.",
    }


def list_movies(page: int, page_size: int, year: int | None, language: str | None,
                sort_by: str, order: str) -> dict:
    collection = get_collection()

    query = {}
    if year is not None:
        query["start_year"] = year
    if language is not None:
        query["language"] = {"$regex": f"^{re.escape(language)}$", "$options": "i"}

    sort_field = SORT_FIELD_MAP.get(sort_by, "start_year")
    sort_order = ORDER_MAP.get(order, DESCENDING)

    skip = (page - 1) * page_size
    docs, total = find_movies(collection, query, sort_field, sort_order, skip, page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "data": docs,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
