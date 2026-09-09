import asyncio

from mcp import types


def test_widget_resource_metadata_is_served(client):
    from backend.app.mcp_dashboard import MCP_APP_DASHBOARD_URI
    from backend.app.mcp_server import mcp
    from backend.app.mcp_widget_meta import widget_resource_meta
    from backend.app.settings import settings

    expected = widget_resource_meta(settings.mcp_public_base_url)
    assert expected["ui"]["domain"] == settings.mcp_public_base_url.rstrip("/")
    assert expected["ui"]["csp"] == {
        "connectDomains": [],
        "resourceDomains": [],
        "frameDomains": [],
    }

    resources = asyncio.run(mcp.list_resources())
    dashboard = next(resource for resource in resources if str(resource.uri) == MCP_APP_DASHBOARD_URI)
    assert dashboard.meta == expected

    request = types.ReadResourceRequest(
        params=types.ReadResourceRequestParams(uri=MCP_APP_DASHBOARD_URI)
    )
    handler = mcp._mcp_server.request_handlers[types.ReadResourceRequest]
    response = asyncio.run(handler(request))
    result = response.root
    assert len(result.contents) == 1
    content = result.contents[0]
    assert content.meta == expected
    assert content.mimeType == "text/html;profile=mcp-app"
    assert "Food Reader" in content.text
