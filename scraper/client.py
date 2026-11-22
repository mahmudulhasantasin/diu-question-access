"""HTTP Client and React Router / Turbo-Stream parser for OurDIU."""

import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
from config import BASE_URL, USER_AGENT, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, RATE_LIMIT_DELAY

logger = logging.getLogger("diu_mcp.scraper.client")


def decode_turbo_stream_array(stream: List[Any]) -> Any:
    """Decode React Router v7 / Remix turbo-stream serialized format into Python structures."""
    if not stream or not isinstance(stream, list):
        return None

    def decode_node(idx: Any, visited: Optional[set] = None) -> Any:
        if visited is None:
            visited = set()

        if isinstance(idx, (int, float)):
            # Negative numbers are special values in turbo-stream
            if idx < 0:
                if idx == -1:  # undefined
                    return None
                if idx == -2:  # null
                    return None
                if idx == -3:  # true
                    return True
                if idx == -4:  # false
                    return False
                if idx == -5:  # null/void
                    return None
                return None
            if idx >= len(stream):
                return None
            val = stream[idx]
        else:
            val = idx

        if isinstance(val, (str, int, float, bool)) or val is None:
            return val

        if isinstance(val, list):
            return [decode_node(item_idx, visited) for item_idx in val]

        if isinstance(val, dict):
            result = {}
            for k, v_idx in val.items():
                if k.startswith("_"):
                    try:
                        prop_key_idx = int(k[1:])
                        prop_key = stream[prop_key_idx] if 0 <= prop_key_idx < len(stream) else k
                    except ValueError:
                        prop_key = k
                else:
                    prop_key = k
                result[str(prop_key)] = decode_node(v_idx, visited)
            return result

        return val

    return decode_node(0)


class OurDIUClient:
    """Polite, resilient async HTTP client for ourdiu.com."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = REQUEST_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        rate_limit_delay: float = RATE_LIMIT_DELAY,
        user_agent: str = USER_AGENT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _rate_limit(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def fetch_html(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Fetch HTML text with retries and rate limiting."""
        client = await self.get_client()
        for attempt in range(1, self.max_retries + 1):
            await self._rate_limit()
            try:
                response = await client.get(url, params=params)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self.retry_delay * 2))
                    logger.warning(f"Rate limited (429) for {url}. Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response.text
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt == self.max_retries:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {exc}")
                    raise
                backoff = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed for {url}: {exc}. Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
        raise RuntimeError(f"Unexpected loop exit while fetching {url}")

    async def fetch_page_data(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch page and extract React Router / Turbo-Stream loaderData."""
        html = await self.fetch_html(url, params=params)
        m = re.search(
            r'<script>window\.__reactRouterContext\.streamController\.enqueue\((.*?)\);</script>',
            html,
            re.DOTALL
        )
        if m:
            raw_json = m.group(1)
            try:
                decoded_outer = json.loads(raw_json)
                stream_list = json.loads(decoded_outer) if isinstance(decoded_outer, str) else decoded_outer
                root = decode_turbo_stream_array(stream_list)
                if isinstance(root, dict):
                    loader_data = root.get("loaderData", {})
                    return {
                        "html": html,
                        "loaderData": loader_data,
                        "raw_stream": stream_list,
                    }
            except Exception as e:
                logger.warning(f"Failed to decode turbo stream from {url}: {e}")

        # Fallback if no stream found
        return {
            "html": html,
            "loaderData": {},
            "raw_stream": None,
        }
