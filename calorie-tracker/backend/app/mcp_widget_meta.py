from __future__ import annotations

from typing import Any

from mcp import types

from .mcp_dashboard import MCP_APP_DASHBOARD_URI, OPENAI_DASHBOARD_URI

_WIDGET_URIS = {MCP_APP_DASHBOARD_URI, OPENAI_DASHBOARD_URI}


def widget_resource_meta(widget_domain: str) -> dict[str, Any]:
    """Metadata ChatGPT/MCP Apps hosts need to sandbox the Food Reader widget.

    The dashboard is fully self-contained: it does not fetch APIs, load CDN
    assets, or embed frames. Keep the CSP allowlists explicit and empty until
    the widget genuinely needs an external origin.
    """

    domain = widget_domain.rstrip("/")
    return {
        "ui": {
            "prefersBorder": True,
            "domain": domain,
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
                "frameDomains": [],
            },
        },
        # Compatibility with ChatGPT hosts that still inspect the legacy
        # OpenAI Apps SDK resource metadata keys.
        "openai/widgetPrefersBorder": True,
        "openai/widgetDomain": domain,
        "openai/widgetCSP": {
            "connect_domains": [],
            "resource_domains": [],
            "frame_domains": [],
        },
    }


def install_widget_resource_metadata(mcp: Any, widget_domain: str) -> None:
    """Add CSP/domain metadata to dashboard resources on FastMCP v1.

    FastMCP v1.22 can expose `_meta` on tools but its high-level resource
    adapter drops `_meta` from resources/read. Until the server is migrated to
    the MCP 2.x Apps extension, replace only the resource list/read handlers so
    ChatGPT receives the metadata required for widget validation.
    """

    if getattr(mcp, "_food_reader_widget_meta_installed", False):
        return

    lowlevel = getattr(mcp, "_mcp_server", None)
    resource_manager = getattr(mcp, "_resource_manager", None)
    if lowlevel is None or resource_manager is None:
        raise RuntimeError("FastMCP internals required for widget metadata are unavailable")

    meta = widget_resource_meta(widget_domain)

    # Preserve all ordinary resources while adding metadata to the two UI
    # resources in resources/list.
    original_list_resources = mcp.list_resources

    async def _list_resources_with_widget_meta():
        resources = await original_list_resources()
        for resource in resources:
            if str(resource.uri) in _WIDGET_URIS:
                resource.meta = meta
        return resources

    lowlevel.list_resources()(_list_resources_with_widget_meta)

    # The v1 low-level read_resource adapter reconstructs TextResourceContents
    # and discards `_meta`. Handle only our UI resources directly and delegate
    # every other URI to the original handler.
    original_read_handler = lowlevel.request_handlers.get(types.ReadResourceRequest)
    if original_read_handler is None:
        raise RuntimeError("FastMCP resources/read handler is unavailable")

    async def _read_resource_with_widget_meta(req: types.ReadResourceRequest):
        if str(req.params.uri) not in _WIDGET_URIS:
            return await original_read_handler(req)

        context = mcp.get_context()
        resource = await resource_manager.get_resource(req.params.uri, context=context)
        if resource is None:
            return await original_read_handler(req)

        content = await resource.read()
        if not isinstance(content, str):
            return await original_read_handler(req)

        return types.ServerResult(
            types.ReadResourceResult(
                contents=[
                    types.TextResourceContents(
                        uri=req.params.uri,
                        text=content,
                        mimeType=resource.mime_type,
                        _meta=meta,
                    )
                ]
            )
        )

    lowlevel.request_handlers[types.ReadResourceRequest] = _read_resource_with_widget_meta
    setattr(mcp, "_food_reader_widget_meta_installed", True)
