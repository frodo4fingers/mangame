"""Nothing on the way to a visible tray icon may pay for the network.

``httpx`` and its connection pools are the most expensive thing this app
imports that the user cannot see. These tests pin the two seams that keep that
cost on the polling thread, where it belongs: the module is imported on first
request, and each source's pool is opened only if that source is asked
something.
"""

import subprocess
import sys
import textwrap

import httpx
import respx

from mangame.sources import mangadex
from mangame.sources.http import HttpClient
from mangame.sources.registry import SourceRegistry


def _in_subprocess(body: str) -> str:
    """Run ``body`` in a clean interpreter and return its stdout.

    Import tests cannot run in-process: pytest, respx and the rest of this
    suite import httpx long before the assertion would be made.
    """
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestStartupImports:
    """The GUI import path must not drag httpx in behind it."""

    def test_source_plumbing_imports_without_httpx(self) -> None:
        loaded = _in_subprocess("""
            import sys
            import mangame.sources.http
            import mangame.sources.base
            import mangame.sources.registry
            print("httpx" in sys.modules)
        """)
        assert loaded == "False"

    def test_building_a_registry_imports_no_httpx(self) -> None:
        loaded = _in_subprocess("""
            import sys
            from mangame.sources.registry import SourceRegistry
            registry = SourceRegistry()
            registry.client("mangadex")
            print("httpx" in sys.modules)
        """)
        assert loaded == "False"

    def test_tray_reaches_visible_without_httpx(self) -> None:
        """The whole GUI, up to a shown tray icon, with no networking loaded."""
        loaded = _in_subprocess("""
            import os, sys
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from PySide6.QtWidgets import QApplication
            from mangame.ui.tray import MangameTray
            app = QApplication(sys.argv)
            tray = MangameTray(app)
            tray.start()
            app.processEvents()
            print("httpx" in sys.modules)
            tray.shutdown()
        """)
        assert loaded == "False"


class TestLazyConnection:
    """A client that is never asked anything never opens a pool."""

    def test_construction_opens_nothing(self) -> None:
        assert HttpClient().connected is False

    def test_registry_opens_nothing(self) -> None:
        registry = SourceRegistry()
        assert [s.source_id for s in registry if registry.client(s.source_id).connected] == []

    async def test_closing_an_unused_client_stays_unconnected(self) -> None:
        """Shutting down must not open a pool purely to close it."""
        client = HttpClient()
        await client.aclose()
        assert client.connected is False

    @respx.mock
    async def test_first_request_connects(self) -> None:
        respx.get(f"{mangadex.API}/manga/x").mock(return_value=httpx.Response(200, json={}))
        client = HttpClient(rate_per_second=1000.0, burst=64)
        before = client.connected
        await client.get_json(f"{mangadex.API}/manga/x")
        after = client.connected
        await client.aclose()
        assert (before, after) == (False, True)

    @respx.mock
    async def test_the_pool_is_reused(self) -> None:
        route = respx.get(f"{mangadex.API}/manga/x").mock(return_value=httpx.Response(200, json={}))
        client = HttpClient(rate_per_second=1000.0, burst=64)
        await client.get_json(f"{mangadex.API}/manga/x")
        first = client._client
        await client.get_json(f"{mangadex.API}/manga/x")
        assert client._client is first
        assert route.call_count == 2
        await client.aclose()

    @respx.mock
    async def test_only_the_asked_source_connects(self) -> None:
        """The search path skips sources by language; skipping must cost nothing.

        This is the case the eager constructor got wrong: every registry built
        one pool per adapter, including the ones the caller was about to pass
        over.
        """
        respx.get(f"{mangadex.API}/manga").mock(
            return_value=httpx.Response(200, json={"result": "ok", "data": []})
        )
        registry = SourceRegistry()
        source = registry.get("mangadex")
        assert source is not None
        try:
            await source.search(registry.client("mangadex"), "one piece")
            connected = {s.source_id for s in registry if registry.client(s.source_id).connected}
            assert connected == {"mangadex"}
        finally:
            await registry.aclose()


class TestInjectedClient:
    """An injected pool is borrowed, not owned."""

    async def test_injected_client_counts_as_connected(self) -> None:
        async with httpx.AsyncClient() as borrowed:
            client = HttpClient(client=borrowed)
            assert client.connected is True
            await client.aclose()
            assert borrowed.is_closed is False
