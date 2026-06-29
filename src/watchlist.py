from .database import add_watch_item, delete_by_id, fetch_df


def list_watch_items():
    """读取自选池。"""
    return fetch_df("SELECT * FROM watchlist ORDER BY id DESC")


def create_watch_item(record: dict) -> None:
    """新增自选标的。"""
    add_watch_item(record)


def remove_watch_item(row_id: int) -> None:
    """删除自选标的。"""
    delete_by_id("watchlist", row_id)

