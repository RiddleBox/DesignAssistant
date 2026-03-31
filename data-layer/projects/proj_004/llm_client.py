"""
llm_client.py — 统一 LLM 调用客户端

支持 Anthropic 原生 API 和中转代理（ANTHROPIC_BASE_URL）。
2.2 / 2.3 动态加载本文件，通过 LLMClient 发起调用。

注意：默认使用流式请求（stream=True），规避中转代理对非流式响应体的大小限制。
"""

import json
import time
import requests


class LLMClient:
    """轻量 LLM 客户端，支持 Anthropic API 和 Bearer token 中转"""

    # 各 provider 的默认 base_url
    _DEFAULT_BASE_URLS = {
        "anthropic": "https://api.anthropic.com",
        "openai":    "https://api.openai.com/v1",
        "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai",
        "custom":    "",
    }

    def __init__(self, api_key: str, base_url: str = "", provider: str = "anthropic"):
        self.api_key  = api_key
        self.provider = provider
        # base_url 优先用传入值，否则用 provider 默认值
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = self._DEFAULT_BASE_URLS.get(provider, "https://api.anthropic.com")

    def _build_headers(self) -> dict:
        """根据 provider 构建请求 headers"""
        base = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.provider == "anthropic":
            # Anthropic 原生 / 中转代理额外加版本 header
            base["anthropic-version"] = "2023-06-01"
        # openai / gemini / custom：仅 Bearer，不加额外 header
        return base

    def _is_openai_compat(self) -> bool:
        """openai / gemini / deepseek 等 OpenAI 兼容格式"""
        return self.provider in ("openai", "gemini", "custom")

    def call(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        max_retries: int = 3,
        system: str = None,
    ) -> str:
        """
        调用 LLM，返回文本响应。

        - anthropic provider：POST /messages，system 在顶层，SSE 用 content_block_delta
        - openai/gemini/custom provider：POST /chat/completions，system 在 messages[0]，SSE 用 choices[0].delta.content

        Args:
            prompt:      用户消息内容
            model:       模型名称
            max_tokens:  最大输出 token 数
            temperature: 温度
            max_retries: 最大重试次数
            system:      系统提示（可选）

        Returns:
            str: 模型输出文本
        """
        headers = self._build_headers()

        if self._is_openai_compat():
            # ── OpenAI 兼容格式（DeepSeek / Gemini / 自定义中转）──────────
            url = self.base_url + "/chat/completions"
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model":       model,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "messages":    messages,
                "stream":      True,
            }
        else:
            # ── Anthropic 原生 / 中转代理格式 ────────────────────────────
            url = self.base_url + "/messages"
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "model":       model,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "messages":    messages,
                "stream":      True,
            }
            if system:
                payload["system"] = system

        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=(30, 180), stream=True)
                resp.raise_for_status()
                if self._is_openai_compat():
                    return self._collect_stream_openai(resp)
                else:
                    return self._collect_stream_anthropic(resp)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e

    def _collect_stream_anthropic(self, resp) -> str:
        """消费 Anthropic SSE 流：content_block_delta / text_delta"""
        text_parts = []
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                event = json.loads(data_str)
            except Exception:
                continue
            etype = event.get("type", "")
            if etype == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text_parts.append(delta.get("text", ""))
            elif etype == "message_stop":
                break
        return "".join(text_parts)

    def _collect_stream_openai(self, resp) -> str:
        """消费 OpenAI 兼容 SSE 流：choices[0].delta.content"""
        text_parts = []
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                event = json.loads(data_str)
            except Exception:
                continue
            choices = event.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    text_parts.append(content)
        return "".join(text_parts)

    # 向后兼容别名
    def _collect_stream(self, resp) -> str:
        return self._collect_stream_anthropic(resp)
