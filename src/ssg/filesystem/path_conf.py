from src.config import STORAGE_ROOT


def get_user_storage_root(email: str) -> str:
    return f"{STORAGE_ROOT}/{email}/storage"


def get_user_meta_root(email: str) -> str:
    return f"{STORAGE_ROOT}/{email}/meta"


def get_share_mark_filepath(email: str, file: str) -> str:
    meta = get_user_meta_root(email)
    return f"{meta}/{file.lstrip('/')}/share"
