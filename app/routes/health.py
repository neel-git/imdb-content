import logging
from flask import Blueprint, jsonify
from app.db import get_db

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health():
    """
    Liveness + readiness probe.
    Returns 200 when the app and MongoDB are reachable, 503 otherwise.
    """
    try:
        get_db().list_collection_names()
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as exc:
        logger.warning("Health check failed: %s", exc)
        return jsonify({"status": "degraded", "database": "unreachable"}), 503
