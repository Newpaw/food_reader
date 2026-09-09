import asyncio


def test_food_reader_dashboard_is_exposed_as_mcp_app(client):
    # Importing main (done by the client fixture) registers the presentation
    # layer on the existing FastMCP tools without changing their tool names.
    from backend.app.mcp_dashboard import (
        DASHBOARD_HTML,
        MCP_APP_DASHBOARD_URI,
        MCP_APP_MIME,
        OPENAI_APP_MIME,
        OPENAI_DASHBOARD_URI,
    )
    from backend.app.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    by_name = {tool.name: tool.model_dump(by_alias=True) for tool in tools}

    for tool_name in (
        "get_health_summary",
        "get_oura_daily",
        "get_withings_measurements",
        "get_meals",
    ):
        meta = by_name[tool_name]["_meta"]
        assert meta["ui"]["resourceUri"] == MCP_APP_DASHBOARD_URI
        assert meta["ui"]["visibility"] == ["model", "app"]
        assert meta["ui/resourceUri"] == MCP_APP_DASHBOARD_URI
        assert meta["openai/outputTemplate"] == OPENAI_DASHBOARD_URI
        assert meta["openai/widgetAccessible"] is True
        # OAuth metadata from the original tool must survive the UI patch.
        assert meta["securitySchemes"]

    resources = asyncio.run(mcp.list_resources())
    by_uri = {str(resource.uri): resource.model_dump(by_alias=True) for resource in resources}
    assert by_uri[MCP_APP_DASHBOARD_URI]["mimeType"] == MCP_APP_MIME
    assert by_uri[OPENAI_DASHBOARD_URI]["mimeType"] == OPENAI_APP_MIME

    assert "Food Reader" in DASHBOARD_HTML
    assert "window.openai" in DASHBOARD_HTML
    assert "addEventListener('message'" in DASHBOARD_HTML
    assert "<svg" in DASHBOARD_HTML
