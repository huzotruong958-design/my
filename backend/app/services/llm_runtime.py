from __future__ import annotations

import json
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
        return self._invoke_structured_with_retry(agent_type, state, model_info)

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _invoke_structured_with_retry(
        self, agent_type: str, state: dict, model_info: dict
    ) -> dict[str, Any]:
        prompt = AGENT_PROMPTS[agent_type]
        model = self._build_model(model_info)
        structured_model = model.with_structured_output(prompt.output_schema)
        messages = [
            SystemMessage(content=prompt.system_prompt),
            HumanMessage(
                content=(
                    f"{prompt.task_template}\n\n"
                    "请严格输出 JSON，禁止补充解释。\n"
                    f"当前状态上下文如下：\n{json.dumps(state, ensure_ascii=False, indent=2)}"
                )
            ),
        ]
        result = structured_model.invoke(messages)
        if isinstance(result, dict):
            return result
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, str):
            return json.loads(result)
        raise TypeError(f"Unsupported structured output for {agent_type}: {type(result)!r}")

    def _build_model(self, model_info: dict):
        provider = model_info["provider"]
        credential = model_info.get("credential") or {}
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_tokens=model_info.get("max_tokens", 3000),
                request_timeout=model_info.get("timeout_seconds", 60),
                retries=3,
                api_key=credential.get("api_key") or os.getenv("GOOGLE_API_KEY"),
            )
        if provider == "openai-compatible":
            return ChatOpenAI(
                model=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_completion_tokens=model_info.get("max_tokens", 3000),
                timeout=model_info.get("timeout_seconds", 60),
                max_retries=3,
                api_key=credential.get("api_key") or os.getenv("OPENAI_API_KEY"),
                base_url=credential.get("base_url") or os.getenv("OPENAI_BASE_URL"),
            )
        if provider == "anthropic":
            return ChatAnthropic(
                model_name=model_info["model_name"],
                temperature=model_info.get("temperature", 0.2),
                max_tokens_to_sample=model_info.get("max_tokens", 3000),
                timeout=model_info.get("timeout_seconds", 60),
                max_retries=3,
                api_key=credential.get("api_key") or os.getenv("ANTHROPIC_API_KEY"),
            )
        raise ValueError(f"Unsupported provider: {provider}")


llm_runtime = LLMRuntime()
