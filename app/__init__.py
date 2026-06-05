import time
import logging
from flask import Flask, jsonify, g, request
from flask_cors import CORS
from app.config import Config
from app.routes.movies import movies_bp
from app.routes.health import health_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)
    else:
        app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    CORS(app)

    app.register_blueprint(movies_bp, url_prefix="/api/v1")
    app.register_blueprint(health_bp)

    _register_middleware(app)
    _register_error_handlers(app)
    _init_db(app)

    return app


def _register_middleware(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        duration_ms = (time.time() - g.get("start_time", time.time())) * 1000
        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response


def _register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": str(e.description), "code": "BAD_REQUEST"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"error": "File too large", "code": "FILE_TOO_LARGE"}), 413

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": str(e.description), "code": "UNPROCESSABLE"}), 422

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500


def _init_db(app):
    if app.config.get("TESTING"):
        return
    with app.app_context():
        try:
            from app.db import get_collection
            from app.repositories.movie_repository import create_indexes
            create_indexes(get_collection())
            logger.info("MongoDB indexes ensured")
        except Exception as exc:
            logger.warning("Could not create indexes at startup: %s", exc)
