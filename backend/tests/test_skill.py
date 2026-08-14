import pytest

ROOT = "http://test"


@pytest.mark.asyncio
async def test_skill_returns_markdown_no_auth(client):
    resp = await client.get(f"{ROOT}/skill")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    body = resp.text
    assert body.startswith("---\n")
    assert "name: aero" in body
    assert "description:" in body
    assert 'version: "0.1.0"' in body
    assert "GET /api/v1/agents/me" in body
    assert "VERSION_CONFLICT" in body
    assert "context_snapshot" in body
