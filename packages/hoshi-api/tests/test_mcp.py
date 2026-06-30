"""Integration tests for the MCP Streamable HTTP transport at /mcp."""

import json

import pytest
from starlette.testclient import TestClient

from hoshi_api.app import app

MCP_URL = "/mcp"

# Minimal MCP JSON-RPC helpers

_HEADERS = {"Accept": "application/json, text/event-stream"}


def _rpc(method: str, params: dict | None = None, id: int = 1) -> dict:
    body: dict = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        body["params"] = params
    return body


def _initialize(client: TestClient) -> dict:
    resp = client.post(
        MCP_URL,
        headers=_HEADERS,
        json=_rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0.1"},
            },
        ),
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def client():
    # Must use TestClient as a context manager so the FastAPI lifespan runs,
    # which initialises the MCP session manager task group.
    with TestClient(app) as c:
        yield c


class TestMCPTransport:
    def test_initialize(self, client):
        data = _initialize(client)
        assert "result" in data
        assert data["result"]["serverInfo"]["name"] == "hoshi"

    def test_tools_list(self, client):
        resp = client.post(MCP_URL, headers=_HEADERS, json=_rpc("tools/list"))
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        names = {t["name"] for t in data["result"]["tools"]}
        assert names == {
            "compute_chart",
            "compute_transits",
            "compare_charts",
            "compute_cusps",
            "import_chart",
        }

    def test_tools_call_compute_chart(self, client, mock_chart):
        resp = client.post(
            MCP_URL,
            headers=_HEADERS,
            json=_rpc(
                "tools/call",
                {
                    "name": "compute_chart",
                    "arguments": {
                        "date": "2000-01-01",
                        "time": "12:00",
                        "lat": 30.0,
                        "lon": -90.0,
                    },
                },
            ),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data, data
        content = data["result"]["content"]
        assert len(content) > 0
        # MCP text content block contains the serialized chart dict
        payload = json.loads(content[0]["text"])
        assert "bodies" in payload

    def test_lifespan_survives_warm_start(self, mock_chart):
        """Second lifespan entry must not raise — simulates Lambda warm start."""
        with TestClient(app) as c:
            resp = c.post("/mcp/", headers=_HEADERS, json=_rpc("tools/list"))
            assert resp.status_code == 200
        # Same module-level app singleton — re-enters the lifespan on warm start
        with TestClient(app) as c:
            resp = c.post("/mcp/", headers=_HEADERS, json=_rpc("tools/list"))
            assert resp.status_code == 200

    def test_tools_call_bad_mode_returns_tool_error(self, client, mock_chart):
        # A bad enum value should surface as a tool error (isError=True),
        # not a 500, because FastMCP catches tool exceptions.
        resp = client.post(
            MCP_URL,
            headers=_HEADERS,
            json=_rpc(
                "tools/call",
                {
                    "name": "compute_chart",
                    "arguments": {"date": "2000-01-01", "mode": "bogus"},
                },
            ),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Either an error in the JSON-RPC envelope or isError on the result
        is_rpc_error = "error" in data
        is_tool_error = data.get("result", {}).get("isError") is True
        assert is_rpc_error or is_tool_error
