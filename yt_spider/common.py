import httpx
import time


def fetch_page_source(url: str, timeout: int = 30, max_retries: int = 3) -> str:
    """Fetch page source with retry logic and timeout."""
    for attempt in range(max_retries):
        try:
            response = httpx.get(
                url,
                timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            response.raise_for_status()
            return response.text
        except (httpx.TimeoutException, httpx.ReadTimeout):
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                print(
                    f"  ⚠ Timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(
                        f"  ⚠ Rate limited, waiting {wait_time}s before retry..."
                    )
                    time.sleep(wait_time)
                else:
                    raise
            else:
                raise
