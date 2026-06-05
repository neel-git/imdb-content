from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from app.services.movie_service import upload_csv, list_movies
from app.schemas.movie_schemas import ListMoviesQuery

movies_bp = Blueprint("movies", __name__)

@movies_bp.route("/movies/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file field in request", "code": "MISSING_FILE"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected", "code": "EMPTY_FILENAME"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files are accepted", "code": "INVALID_FILE_TYPE"}), 400

    result = upload_csv(file)

    # inserted=0 with skipped>0 means the file format was not recognised at all.
    if result["inserted"] == 0 and result["skipped"] > 0:
        return jsonify({
            "error": (
                "No rows could be inserted. Check that your CSV uses recognised column names: "
                "primary_title (or title), start_year (or release_date), "
                "average_rating (or vote_average), num_votes (or vote_count), "
                "language (or languages), runtime_minutes (or runtime)."
            ),
            "code": "NO_VALID_ROWS",
            "inserted": result["inserted"],
            "skipped": result["skipped"],
        }), 422

    return jsonify(result), 200


@movies_bp.route("/movies", methods=["GET"])
def list_movies_route():
    try:
        params = ListMoviesQuery(**request.args.to_dict())
    except ValidationError as exc:
        first = exc.errors()[0]
        return jsonify({
            "error": first["msg"],
            "code": "INVALID_PARAMS",
            "details": exc.errors(),
        }), 400

    result = list_movies(
        params.page,
        params.page_size,
        params.year,
        params.language,
        params.sort_by,
        params.order,
    )
    return jsonify(result), 200
