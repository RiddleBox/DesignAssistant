"""
llm_client.py — 统一 LLM 调用客户端

支持 Anthropic 原生 API 和中转代理（ANTHROPIC_BASE_URL）。
2.2 / 2.3 动态加载本文件，通过 LLMClient 发起调用。
"""

import json
import time
import requests


class LLMClient:
    """轻量 LLM 客户端，支持 Anthropic API 和 Bearer token 中转"""

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com"):
        self.api_key  = api_key
        self.base_url = base_url.rstrip("/")

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
        url = self.base_url + "/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model":       model,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages":    messages,
        }
        if system:
            payload["system"] = system

        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=(30, 180))
                resp.raise_for_status()
                data = resp.json()
                # 提取文本（跳过 thinking 块）
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                return ""
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e
