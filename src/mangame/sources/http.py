"""Shared HTTP plumbing for source adapters.

Three concerns live here so that no adapter has to think about them:

* **Rate limiting** — one token bucket per source, so tracking thirty series on
  MangaDex still respects MangaDex's budget.
* **Conditional requests** — ETag / Last-Modified are stored per request key and
  replayed, turning most polls into a 304 that costs almost nothing. This is
  what makes an aggressive hot-window cadence affordable.
* **Retries** — 429 and 5xx back off exponentially and honour ``Retry-After``.

``httpx`` is imported on first use rather than at module import. It costs
~14 MB of resident memory and ~140 ms, and nothing on the path to a visible
tray icon needs it: the UI only asks this package which sources *serve* a
language, which is metadata. The underlying connection pool is likewise opened
on the first request, so a registry hands out four clients for the price of the
one or two that actually get asked something.
"""

import asyncio
import time
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import httpx

USER_AGENT = "mangame/0.1 (+https://github.com/mangame/mangame)"


class RateLimiter:
    """Simple async token bucket."""

    def __init__(self, rate_per_second: float, burst: int = 1) -> None:
        self._rate = rate_per_second
        self._capacity = float(max(burst, 1))
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity, self._tokens + (now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                await asyncio.sleep((1.0 - self._tokens) / self._rate)


class CacheValidators(BaseModel):
    """What a previous response told us to send back next time."""

    model_config = ConfigDict(frozen=True)

    etag: str | None = None
    last_modified: str | None = None

    def as_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        return headers


class Response(BaseModel):
    """Adapter-facing result. ``not_modified`` means "reuse what you had"."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    status_code: int
    payload: Any = None
    validators: CacheValidators = CacheValidators()

    @property
    def not_modified(self) -> bool:
        return self.status_code == 304


class HttpClient:
    """Rate-limited, cache-aware JSON client shared by every adapter.

    The connection pool is opened lazily, so constructing one of these for a
    source that is never asked anything costs a token bucket and nothing else.
    """

    MAX_ATTEMPTS = 4

    def __init__(
        self,
        *,
        rate_per_second: float = 2.0,
        burst: int = 4,
        timeout: float = 20.0,
        client: "httpx.AsyncClient | None" = None,
    ) -> None:
        self._limiter = RateLimiter(rate_per_second, burst)
        self._timeout = timeout
        self._owns_client = client is None
        self._client = client

    @property
    def connected(self) -> bool:
        """Has this client actually opened a connection pool yet?"""
        return self._client is not None

    def _connect(self) -> "httpx.AsyncClient":
        """Open the pool on first use. Importing httpx is part of the cost."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        validators: CacheValidators | None = None,
        parse_json: bool = True,
    ) -> Response:
        import httpx

        client = self._connect()
        merged = dict(headers or {})
        if validators is not None:
            merged.update(validators.as_headers())

        last_error: Exception | None = None
        for attempt in range(self.MAX_ATTEMPTS):
            await self._limiter.acquire()
            try:
                response = await client.request(
                    method, url, params=params, json=json_body, headers=merged
                )
            except httpx.HTTPError as exc:  # network-level failure
                last_error = exc
                await asyncio.sleep(min(2**attempt, 30))
                continue

            if response.status_code == 304:
                return Response(status_code=304, validators=validators or CacheValidators())

            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(self._retry_delay(response, attempt))
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code} from {url}",
                    request=response.request,
                    response=response,
                )
                continue

            response.raise_for_status()
            payload = response.json() if parse_json else response.text
            return Response(
                status_code=response.status_code,
                payload=payload,
                validators=CacheValidators(
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                ),
            )

        raise last_error or httpx.HTTPError(f"giving up on {url}")

    @staticmethod
    def _retry_delay(response: "httpx.Response", attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 120.0)
            except ValueError:
                pass
        return float(min(2**attempt, 30))

    async def get_json(self, url: str, **kwargs: Any) -> Response:
        return await self.request("GET", url, **kwargs)

    async def post_json(self, url: str, **kwargs: Any) -> Response:
        return await self.request("POST", url, **kwargs)
