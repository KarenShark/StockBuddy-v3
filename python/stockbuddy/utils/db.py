import os

from .path import get_repo_root_path


def resolve_db_path() -> str:
    return os.environ.get("STOCKBUDDY_SQLITE_DB") or os.path.join(
        get_repo_root_path(), "stockbuddy.db"
    )


def resolve_lancedb_uri() -> str:
    return os.environ.get("STOCKBUDDY_LANCEDB_URI") or os.path.join(
        get_repo_root_path(), "lancedb"
    )
