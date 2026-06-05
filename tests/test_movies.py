import pytest

LIST_URL = "/api/v1/movies"
HEALTH_URL = "/health"

# Test 1: Empty DB returns empty list
def test_list_empty_db(client):
    resp = client.get(LIST_URL)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["data"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0


# Test 2: Filter by year
def test_list_filter_by_year(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?year=2019")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["total"] == 1
    assert data["data"][0]["primary_title"] == "Parasite"


# Test 3: Filter by language
def test_list_filter_by_language(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?language=English")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["total"] == 3
    titles = {m["primary_title"] for m in data["data"]}
    assert "Parasite" not in titles
    assert "RRR" not in titles


# Test 4: Sort by ratings descending
def test_list_sort_by_ratings_desc(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?sort_by=ratings&order=desc")
    data = resp.get_json()

    assert resp.status_code == 200
    ratings = [m["average_rating"] for m in data["data"]]
    assert ratings == sorted(ratings, reverse=True)


# Test 5: Sort by release_date ascending
def test_list_sort_by_release_date_asc(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?sort_by=release_date&order=asc")
    data = resp.get_json()

    assert resp.status_code == 200
    years = [m["start_year"] for m in data["data"]]
    assert years == sorted(years)
    assert years[0] == 1999  # The Matrix


# Test 6: Pagination — page 2 with page_size=2
def test_list_pagination(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?page=2&page_size=2&sort_by=release_date&order=asc")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total"] == 5
    assert data["total_pages"] == 3
    assert len(data["data"]) == 2


# Test 7: Invalid sort_by param 
def test_list_invalid_sort_by(client):
    resp = client.get(f"{LIST_URL}?sort_by=invalid_field")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_PARAMS"


# Test 8: Invalid order param
def test_list_invalid_order(client):
    resp = client.get(f"{LIST_URL}?order=sideways")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_PARAMS"


# Test 9: page_size exceeds max
def test_list_page_size_exceeds_max(client):
    resp = client.get(f"{LIST_URL}?page_size=200")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_PARAMS"


# Test 10: Combined year + language filter
def test_list_combined_filters(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?year=2010&language=English")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["total"] == 1
    assert data["data"][0]["primary_title"] == "Inception"


# Test 11: Default pagination values
def test_list_default_pagination(client, seeded_collection):
    resp = client.get(LIST_URL)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 5


# Test 12: Sort by ratings ascending
def test_list_sort_by_ratings_asc(client, seeded_collection):
    resp = client.get(f"{LIST_URL}?sort_by=ratings&order=asc")
    data = resp.get_json()

    assert resp.status_code == 200
    ratings = [m["average_rating"] for m in data["data"]]
    assert ratings == sorted(ratings)
    assert ratings[0] == 7.8  # RRR


# Test 13: Health check — DB reachable via mongomock
def test_health_check_ok(client):
    resp = client.get(HEALTH_URL)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["status"] == "ok"
    assert data["database"] == "connected"


# Test 14: Health check — DB unreachable returns 503
def test_health_check_degraded(client, monkeypatch):
    import app.routes.health as health_mod

    monkeypatch.setattr(health_mod, "get_db", lambda: (_ for _ in ()).throw(Exception("unreachable")))

    resp = client.get(HEALTH_URL)
    data = resp.get_json()

    assert resp.status_code == 503
    assert data["status"] == "degraded"
