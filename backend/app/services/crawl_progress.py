crawl_progress_store: dict[int, int] = {}

def set_progress(site_id: int, progress: int):
    crawl_progress_store[site_id] = min(progress, 100)

def get_progress(site_id: int) -> int:
    return crawl_progress_store.get(site_id, 0)

def clear_progress(site_id: int):
    crawl_progress_store.pop(site_id, None)
