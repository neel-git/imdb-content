import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "imdb_db")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "movies")
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 1000))


