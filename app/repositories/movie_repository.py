from pymongo import ASCENDING, DESCENDING

def create_indexes(collection):
    collection.create_index([("start_year", ASCENDING)], background=True)
    collection.create_index([("language", ASCENDING)], background=True)
    collection.create_index([("average_rating", ASCENDING)], background=True)
    collection.create_index(
        [("start_year", ASCENDING), ("language", ASCENDING)], background=True
    )

def bulk_insert(collection, documents: list) -> int:
    """Insert a batch; ordered=False lets MongoDB skip duplicates and continue."""
    if not documents:
        return 0
    result = collection.insert_many(documents, ordered=False)
    return len(result.inserted_ids)

def find_movies(collection, query: dict, sort_field: str, sort_order: int, skip: int, limit: int):
    """
    Return (list_of_docs, total_count).
    Docs have _id serialised to string so they're JSON-safe.
    """
    total = collection.count_documents(query)
    cursor = (
        collection.find(query, {"_id": 0})
        .sort(sort_field, sort_order)
        .skip(skip)
        .limit(limit)
    )
    docs = list(cursor)
    return docs, total
