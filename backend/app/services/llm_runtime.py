from __future__ import annotations

import json
import os
from typing import Any

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.agents.prompts import AGENT_PROMPTS


class LLMRuntime:
    real_agent_types = {
        "researcher",
        "fact_checker",
        "writer",
        "formatter",
        "editor",
        "image_editor",
    }

    def can_run(self, agent_type: str, model_info: dict) -> bool:
        if agent_type not in self.real_agent_types:
            return False
        provider = model_info["provider"]
        credential = model_info.get("credential") or {}
        if provider == "gemini":
            return bool(credential.get("api_key") or os.getenv("GOOGLE_API_KEY"))
        if provider == "openai-compatible":
            return bool(credential.get("api_key") or os.getenv("OPENAI_API_KEY"))
        if provider == "anthropic":
            return bool(credential.get("api_key") or os.getenv("ANTHROPIC_API_KEY"))
        return False

    def invoke_structured(self, agent_type: str, state: dict, model_info: dict) -> dict[str, Any]:
        prompt = AGENT_PROMPTS[agent_type]
        compact_state = self._compact_state(state)
        messages = [
            SystemMessage(content=prompt.system_prompt),
            HumanMessage(
                content=(
                    f"{prompt.task_template}\n\n"
                    "请严格输出 JSON，禁止补充解释。\n"
                    f"当前状态上下文如下：\n{json.dumps(compact_state, ensure_ascii=False, indent=2)}"
                )
            ),
        ]

        last_error: Exception | None = None
        for timeout_seconds in self._attempt_timeouts(self._resolve_timeout_seconds(model_info)):
            try:
                model = self._build_model(model_info, timeout_seconds=timeout_seconds)
                structured_model = model.with_structured_output(prompt.output_schema)
                result = structured_model.invoke(messages)
                if isinstance(result, dict):
                    return result
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                if isinstance(result, str):
                    return json.loads(result)
                raise TypeError(f"Unsupported structured output for {agent_type}: {type(result)!r}")
            except (httpx.TimeoutException, httpx.TransportError, TimeoutError) as exc:
                last_error = exc
                continue
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                raise
            except Exception as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Structured invoke failed for {agent_type}")

    def _resolve_timeout_seconds(self, model_info: dict) -> int:
        configured = int(model_info.get("timeout_seconds", 60) or 60)
        return max(20, min(configured, 90))

    def _attempt_timeouts(self, base_timeout: int) -> list[int]:
        if base_timeout <= 30:
            return [base_timeout, base_timeout]
        return [
            max(20, int(base_timeout * 0.55)),
            max(24, int(base_timeout * 0.8)),
            base_timeout,
        ]

    def _compact_state(self, value: Any, *, depth: int = 0) -> Any:
        if depth >= 6:
            return self._truncate_text(value)
        if isinstance(value, dict):
            compact: dict[str, Any] = {}
            for key, item in value.items():
                if item in ("", None, [], {}):
                    continue
                compact[key] = self._compact_state(item, depth=depth + 1)
            return compact
        if isinstance(value, list):
            limit = 12 if depth <= 2 else 6
            items = [self._compact_state(item, depth=depth + 1) for item in value[:limit]]
            if len(value) > limit:
                items.append({"truncated_items": len(value) - limit})
            return items
        return self._truncate_text(value)

    def _truncate_text(self, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip()
            if len(normalized) <= 4000:
                return normalized
            return f"{normalized[:4000]}\n...[truncated {len(normalized) - 4000} chars]"
        return value

    def _build_model(self, model_info: dict, *, timeout_seconds: int):
        provider = model_info["provider"]
        credential = model_info.get("credential") or {}
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_tokens=model_info.get("max_tokens", 3000),
                request_timeout=timeout_seconds,
                retries=1,
                api_key=credential.get("api_key") or os.getenv("GOOGLE_API_KEY"),
            )
        if provider == "openai-compatible":
            return ChatOpenAI(
                model=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_completion_tokens=model_info.get("max_tokens", 3000),
                timeout=timeout_seconds,
                max_retries=1,
                api_key=credential.get("api_key") or os.getenv("OPENAI_API_KEY"),
                base_url=credential.get("base_url") or os.getenv("OPENAI_BASE_URL"),
            )
        if provider == "anthropic":
            return ChatAnthropic(
                model_name=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_tokens_to_sample=model_info.get("max_tokens", 3000),
                timeout=timeout_seconds,
                max_retries=1,
                api_key=credential.get("api_key") or os.getenv("ANTHROPIC_API_KEY"),
            )
        raise ValueError(f"Unsupported provider: {provider}")


llm_runtime = LLMRuntime()
