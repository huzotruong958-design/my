from __future__ import annotations

import json
import time
from typing import Any

import httpx


class XiaohongshuMcpClient:
    candidate_tools = {
        "login_status": ["check_login_status", "login_status", "get_login_status"],
        "search": ["search_feeds", "search_notes", "search_posts", "search_content"],
        "detail": ["get_feed_detail", "get_note_detail", "get_post_detail", "get_note_by_url"],
    }

    def __init__(
        self,
        endpoint: str,
        api_token: str = "",
        timeout_seconds: int = 30,
        auth_header: str = "Authorization",
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_token = api_token.strip()
        self.timeout_seconds = timeout_seconds
        self.auth_header = auth_header.strip() or "Authorization"
        self.session_id: str = ""
        self._rpc_id = 1
        self._initialized = False

    def probe(self) -> dict[str, Any]:
        initialize_payload = self._initialize()
        tools_payload = self._rpc("tools/list", {})
        tools = tools_payload.get("tools", []) if isinstance(tools_payload, dict) else []
        tool_names = [tool.get("name", "") for tool in tools if isinstance(tool, dict)]
        login_status = None
        login_tool = self._find_tool(tools, "login_status")
        if login_tool:
            try:
                login_status = self.call_tool(login_tool["name"], {})
            except Exception as exc:
                login_status = {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "endpoint": self.endpoint,
            "initialize": initialize_payload,
            "tool_count": len(tool_names),
            "tool_names": tool_names,
            "login_status": login_status,
            "search_tool": login_tool["name"] if False else (self._find_tool(tools, "search") or {}).get("name", ""),
            "detail_tool": (self._find_tool(tools, "detail") or {}).get("name", ""),
        }

    def search_notes(self, keyword: str, limit: int = 8) -> dict[str, Any]:
        tools = self._list_tools()
        tool = self._find_tool(tools, "search")
        if not tool:
            raise RuntimeError("No search tool exposed by xiaohongshu MCP")
        args = self._build_args(
            tool,
            {
                "keyword": keyword,
                "query": keyword,
                "search_keyword": keyword,
                "searchKey": keyword,
                "page": 1,
                "page_size": limit,
                "pageSize": limit,
                "size": limit,
                "limit": limit,
                "num": limit,
            },
        )
        return self._call_tool_with_retry(tool["name"], args, attempts=3)

    def get_note_detail(self, item: dict[str, Any]) -> dict[str, Any]:
        tools = self._list_tools()
        tool = self._find_tool(tools, "detail")
        if not tool:
            raise RuntimeError("No detail tool exposed by xiaohongshu MCP")
        args = self._build_args(
            tool,
            {
                "feed_id": item.get("feed_id") or item.get("id") or item.get("note_id"),
                "feedId": item.get("feed_id") or item.get("id") or item.get("note_id"),
                "note_id": item.get("note_id") or item.get("feed_id") or item.get("id"),
                "id": item.get("id") or item.get("feed_id") or item.get("note_id"),
                "xsec_token": item.get("xsec_token") or item.get("xsecToken"),
                "xsecToken": item.get("xsec_token") or item.get("xsecToken"),
                "url": item.get("url") or item.get("link"),
            },
        )
        return self._call_tool_with_retry(tool["name"], args, attempts=2)

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        result = self._rpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": {k: v for k, v in arguments.items() if v not in (None, "")},
            },
            timeout_seconds=timeout_seconds,
        )
        return self._normalize_tool_result(result)

    def _call_tool_with_retry(self, tool_name: str, arguments: dict[str, Any], *, attempts: int) -> dict[str, Any]:
        last_error: Exception | None = None
        base_timeout = max(10, int(self.timeout_seconds or 30))
        for attempt in range(1, attempts + 1):
            try:
                attempt_timeout = min(base_timeout, max(10, int(base_timeout * (0.55 + (attempt - 1) * 0.25))))
                return self.call_tool(tool_name, arguments, timeout_seconds=attempt_timeout)
            except (httpx.TimeoutException, httpx.TransportError, RuntimeError) as exc:
                last_error = exc
                self._initialized = False
                self.session_id = ""
                if attempt >= attempts:
                    break
                time.sleep(1.5 * attempt)
        raise RuntimeError(f"{tool_name} failed after {attempts} attempts: {last_error}") from last_error

    def _list_tools(self) -> list[dict[str, Any]]:
        self._initialize()
        payload = self._rpc("tools/list", {})
        tools = payload.get("tools", []) if isinstance(payload, dict) else []
        return [tool for tool in tools if isinstance(tool, dict)]

    def _find_tool(self, tools: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
        names = self.candidate_tools.get(kind, [])
        for candidate in names:
            for tool in tools:
                if tool.get("name") == candidate:
                    return tool
        for tool in tools:
            name = str(tool.get("name") or "")
            if kind == "search" and "search" in name:
                return tool
            if kind == "detail" and ("detail" in name or "note" in name or "feed" in name):
                return tool
            if kind == "login_status" and "login" in name and "status" in name:
                return tool
        return None

    def _build_args(self, tool: dict[str, Any], preferred_values: dict[str, Any]) -> dict[str, Any]:
        schema = tool.get("inputSchema", {}) if isinstance(tool, dict) else {}
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if not isinstance(properties, dict) or not properties:
            return {k: v for k, v in preferred_values.items() if v not in (None, "")}
        args: dict[str, Any] = {}
        for key in properties.keys():
            if key in preferred_values and preferred_values[key] not in (None, ""):
                args[key] = preferred_values[key]
        return args

    def _normalize_tool_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict) and "structuredContent" in result:
            return {
                "ok": True,
                "structured": result.get("structuredContent"),
                "content": result.get("content", []),
                "raw": result,
            }
        if isinstance(result, dict) and "content" in result:
            parsed = self._parse_content(result.get("content", []))
            return {
                "ok": True,
                "structured": parsed,
                "content": result.get("content", []),
                "raw": result,
            }
        return {"ok": True, "structured": result, "content": [], "raw": result}

    def _parse_content(self, content: list[dict[str, Any]]) -> Any:
        if not isinstance(content, list):
            return {}
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text") or ""))
        if not text_parts:
            return {}
        joined = "\n".join(text_parts).strip()
        try:
            return json.loads(joined)
        except Exception:
            return {"text": joined}

    def _rpc(self, method: str, params: dict[str, Any], timeout_seconds: int | None = None) -> Any:
        body = {"jsonrpc": "2.0", "id": self._rpc_id, "method": method, "params": params}
        self._rpc_id += 1
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            if self.auth_header.lower() == "authorization":
                headers["Authorization"] = f"Bearer {self.api_token}"
            else:
                headers[self.auth_header] = self.api_token
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        request_timeout = timeout_seconds or self.timeout_seconds
        timeout = httpx.Timeout(
            connect=min(10, request_timeout),
            read=request_timeout,
            write=min(10, request_timeout),
        )
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(self.endpoint, json=body, headers=headers)
            response.raise_for_status()
            session_id = response.headers.get("mcp-session-id", "")
            if session_id:
                self.session_id = session_id
            payload = response.json()
        if "error" in payload:
            raise RuntimeError(str(payload["error"]))
        return payload.get("result")

    def _initialize(self) -> Any:
        if self._initialized:
            return {"already_initialized": True}
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "wechat-travel-agents", "version": "0.1.0"},
            },
        )
        self._initialized = True
        return result


xiaohongshu_mcp_client = XiaohongshuMcpClient
