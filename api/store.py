from api.json_store import JsonFileStore
from api.paths import SQLITE_PATH, STORE_BACKEND
from api.sqlite_store import SqliteStore


def create_store():
    if STORE_BACKEND == "json":
        return JsonFileStore()
    return SqliteStore(SQLITE_PATH)
