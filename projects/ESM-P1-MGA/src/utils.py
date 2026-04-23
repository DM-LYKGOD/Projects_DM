import time
import requests
from typing import Any

def download_with_retry(url: str, task_name: str = "HTTP", timeout: int = 120, retries: int = 3) -> bytes | None:
    """Attempt to download a URL, retrying on transient failures."""
    for attempt in range(1, retries + 1):
        try:
            print(f"[{task_name}]   Attempt {attempt}/{retries}: GET {url}")
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.exceptions.RequestException as exc:
            print(f"[{task_name}]   WARNING: {exc}")
            if attempt < retries:
                time.sleep(5 * attempt)
    return None
