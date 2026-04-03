"""
llm_client.py — 统一 LLM 调用客户端

支持 Anthropic 原生 API 和 OpenAI 兼容接口（OpenAI / Gemini / DeepSeek / 自定义中转）。
2.2 / 2.3 动态加载本文件，通过 LLMClient 发起调用。

注意：默认使用流式请求（stream=True），规避中转代理对非流式响应体的大小限制。
"""

import json
import os
import time
import requests


class LLMClient:
    """轻量 LLM 客户端，支持 Anthropic API 和 OpenAI 兼容接口"""

    # 各 provider 的默认 base_url
    _DEFAULT_BASE_URLS = {
        "anthropic": "https://api.anthropic.com",
        "openai":    "https://api.openai.com/v1",
        "deepseek":  "https://api.deepseek.com",
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
        """openai / deepseek / gemini / custom 等 OpenAI 兼容格式"""
        return self.provider in ("openai", "deepseek", "gemini", "custom")

    @staticmethod
    def _env_flag(name: str, default: bool = False) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        value = os.environ.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_request_timeouts(self) -> tuple:
        connect_timeout = self._env_int("LLM_CONNECT_TIMEOUT_SECONDS", 30)
        read_timeout = self._env_int("LLM_READ_TIMEOUT_SECONDS", 180)
        return (connect_timeout, read_timeout)

    def _get_stream_wall_clock_timeout_seconds(self) -> int:
        return self._env_int("LLM_STREAM_WALL_CLOCK_TIMEOUT_SECONDS", 0)

    def _debug_log(self, message: str) -> None:
        if self._env_flag("LLM_DEBUG", False):
            print(f"[LLMClient] {message}", flush=True)

    def _ensure_stream_not_timed_out(self, started_at: float, stream_timeout_seconds: int) -> None:
        if stream_timeout_seconds <= 0:
            return
        elapsed_seconds = time.monotonic() - started_at
        if elapsed_seconds > stream_timeout_seconds:
            raise TimeoutError(
                f"LLM stream wall-clock timeout after {int(elapsed_seconds)}s "
                f"(limit={stream_timeout_seconds}s)"
            )

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
        timeouts = self._get_request_timeouts()
        stream_timeout_seconds = self._get_stream_wall_clock_timeout_seconds()

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
                started_at = time.time()
                self._debug_log(
                    f"request_start provider={self.provider} model={model} attempt={attempt + 1}/{max_retries} "
                    f"url={url} connect_timeout={timeouts[0]} read_timeout={timeouts[1]} "
                    f"stream_wall_clock_timeout={stream_timeout_seconds or 'off'}"
                )
                resp = requests.post(url, headers=headers, json=payload, timeout=timeouts, stream=True)
                resp.raise_for_status()
                self._debug_log(
                    f"response_headers status={resp.status_code} elapsed_ms={int((time.time() - started_at) * 1000)}"
                )
                stream_started_at = time.monotonic()
                if self._is_openai_compat():
                    text = self._collect_stream_openai(resp, stream_started_at, stream_timeout_seconds)
                else:
                    text = self._collect_stream_anthropic(resp, stream_started_at, stream_timeout_seconds)
                self._debug_log(
                    f"response_complete chars={len(text)} elapsed_ms={int((time.time() - started_at) * 1000)}"
                )
                return text
            except Exception as e:
                self._debug_log(
                    f"request_error provider={self.provider} model={model} attempt={attempt + 1}/{max_retries} error={e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e

    def _collect_stream_anthropic(self, resp, started_at: float, stream_timeout_seconds: int) -> str:
        """消费 Anthropic SSE 流：content_block_delta / text_delta"""
        text_parts = []
        first_chunk_logged = False
        for raw_line in resp.iter_lines():
            self._ensure_stream_not_timed_out(started_at, stream_timeout_seconds)
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
                    text = delta.get("text", "")
                    if text:
                        text_parts.append(text)
                        if not first_chunk_logged:
                            self._debug_log(
                                f"stream_first_chunk provider={self.provider} chars={len(text)} elapsed_ms={int((time.monotonic() - started_at) * 1000)}"
                            )
                            first_chunk_logged = True
            elif etype == "message_stop":
                break
        return "".join(text_parts)

    def _collect_stream_openai(self, resp, started_at: float, stream_timeout_seconds: int) -> str:
        """消费 OpenAI 兼容 SSE 流：choices[0].delta.content"""
        text_parts = []
        first_chunk_logged = False
        for raw_line in resp.iter_lines():
            self._ensure_stream_not_timed_out(started_at, stream_timeout_seconds)
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
                    if not first_chunk_logged:
                        self._debug_log(
                            f"stream_first_chunk provider={self.provider} chars={len(content)} elapsed_ms={int((time.monotonic() - started_at) * 1000)}"
                        )
                        first_chunk_logged = True
        return "".join(text_parts)

    # 向后兼容别名
    def _collect_stream(self, resp) -> str:
        return self._collect_stream_anthropic(resp, time.monotonic(), self._get_stream_wall_clock_timeout_seconds())
