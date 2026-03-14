"""
Phase 2.1 情报解码模块 - 核心解码器
基于 phase2.1_设计方案.md 第四节的抽取流程设计
"""

import json
import re
import time
from datetime import datetime
from typing import List, Dict, Any
from anthropic import Anthropic

from schemas import (
    IntelligenceDecodeRequest,
    DecodedIntelligence,
    Signal,
    SignalType,
    SourceType
)
from prompt_templates import build_prompt, PROMPT_VERSION


class IntelligenceDecoder:
    """情报解码器 - Prompt-first + 轻量后处理策略"""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6"):
        """
        初始化解码器

        Args:
            api_key: Anthropic API key
            model: 使用的模型，默认 Claude Opus 4.6
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.decoder_version = PROMPT_VERSION

    def decode(self, request: IntelligenceDecodeRequest) -> DecodedIntelligence:
        """
        解码情报

        Args:
            request: 解码请求

        Returns:
            DecodedIntelligence: 解码后的情报
        """
        start_time = time.time()
        warnings = []

        try:
            # [1] 文本预处理
            cleaned_text = self._preprocess(request.content)

            # 检查文本长度
            if len(cleaned_text) < 50:
                warnings.append("原文过短（<50 字），可能影响抽取质量")

            # [2] 构建 Prompt
            prompt = build_prompt(cleaned_text, request.source_id)

            # [3] LLM 调用
            response = self._call_llm(prompt)

            # [4] 后处理与规范化
            signals = self._post_process(response, request.source_id, warnings)

            # [5] Schema 校验
            validated_signals = self._validate_signals(signals, warnings)

            # 计算处理耗时
            processing_time_ms = int((time.time() - start_time) * 1000)

            # [6] 返回结果
            return DecodedIntelligence(
                source_id=request.source_id,
                source_type=request.source_type,
                signals=validated_signals,
                summary=self._generate_summary(validated_signals),
                decoder_version=self.decoder_version,
                processing_time_ms=processing_time_ms,
                warnings=warnings if warnings else None
            )

        except Exception as e:
            # 错误处理
            processing_time_ms = int((time.time() - start_time) * 1000)
            warnings.append(f"解码失败: {str(e)}")

            return DecodedIntelligence(
                source_id=request.source_id,
                source_type=request.source_type,
                signals=[],
                summary=None,
                decoder_version=self.decoder_version,
                processing_time_ms=processing_time_ms,
                warnings=warnings
            )

    def _preprocess(self, text: str) -> str:
        """
        文本预处理

        Args:
            text: 原始文本

        Returns:
            str: 清洗后的文本
        """
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空格
        text = text.strip()
        return text

    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """
        调用 LLM（带重试机制）

        Args:
            prompt: 完整 Prompt
            max_retries: 最大重试次数

        Returns:
            str: LLM 响应
        """
        for attempt in range(max_retries):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.0,  # 使用 0 温度保证稳定性
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            except Exception as e:
                if attempt < max_retries - 1:
                    # 指数退避
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise e

    def _post_process(
        self,
        response: str,
        source_id: str,
        warnings: List[str]
    ) -> List[Dict[str, Any]]:
        """
        后处理与规范化

        Args:
            response: LLM 响应
            source_id: 原始来源 ID
            warnings: 警告列表

        Returns:
            List[Dict]: 信号列表
        """
        try:
            # 尝试解析 JSON
            # 提取 JSON 部分（可能包含在 markdown 代码块中）
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response

            data = json.loads(json_str)
            signals = data.get("signals", [])

            # 格式规范化
            for signal in signals:
                # 去除多余空格
                if "signal_label" in signal:
                    signal["signal_label"] = signal["signal_label"].strip()
                if "description" in signal:
                    signal["description"] = signal["description"].strip()

                # 字段补全：如果 entities 为空，尝试从 evidence_text 提取
                if not signal.get("entities") and signal.get("evidence_text"):
                    # 简单的实体提取（可以后续增强）
                    signal["entities"] = []

                # 确保 source_ref 正确
                signal["source_ref"] = source_id

                # 确保 extracted_at 存在
                if "extracted_at" not in signal:
                    signal["extracted_at"] = datetime.utcnow().isoformat() + "Z"

            # 去重：同一 source 内的重复信号
            unique_signals = []
            seen = set()
            for signal in signals:
                key = (signal.get("signal_type"), signal.get("signal_label"))
                if key not in seen:
                    seen.add(key)
                    unique_signals.append(signal)

            return unique_signals

        except json.JSONDecodeError as e:
            warnings.append(f"JSON 解析失败: {str(e)}")
            return []
        except Exception as e:
            warnings.append(f"后处理失败: {str(e)}")
            return []

    def _validate_signals(
        self,
        signals: List[Dict[str, Any]],
        warnings: List[str]
    ) -> List[Signal]:
        """
        Schema 校验

        Args:
            signals: 信号列表
            warnings: 警告列表

        Returns:
            List[Signal]: 校验后的信号列表
        """
        validated = []

        for i, signal_data in enumerate(signals):
            try:
                # 评分校验：确保 1-10 范围
                for score_field in ["intensity_score", "confidence_score", "timeliness_score"]:
                    if score_field in signal_data:
                        score = signal_data[score_field]
                        if not isinstance(score, int) or score < 1 or score > 10:
                            warnings.append(f"信号 {i+1} 的 {score_field} 超出范围，已修正")
                            signal_data[score_field] = max(1, min(10, int(score)))

                # 使用 Pydantic 校验
                signal = Signal(**signal_data)
                validated.append(signal)

            except Exception as e:
                warnings.append(f"信号 {i+1} 校验失败: {str(e)}，已丢弃该信号")
                continue

        return validated

    def _generate_summary(self, signals: List[Signal]) -> str:
        """
        生成人类可读摘要

        Args:
            signals: 信号列表

        Returns:
            str: 摘要
        """
        if not signals:
            return "未检测到范式信号"

        signal_counts = {}
        for signal in signals:
            signal_type = signal.signal_type.value
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

        summary_parts = []
        type_names = {
            "technical": "技术信号",
            "market": "市场信号",
            "team": "团队信号",
            "capital": "资本信号"
        }

        for signal_type, count in signal_counts.items():
            summary_parts.append(f"{type_names[signal_type]} {count} 个")

        return f"检测到 {len(signals)} 个范式信号：" + "、".join(summary_parts)