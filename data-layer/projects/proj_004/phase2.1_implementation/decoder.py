"""
Phase 2.1 情报解码模块 - 核心解码器
基于 phase2.1_设计方案.md 第四节的抽取流程设计
"""

import json
import copy
import re
import time
import os
from datetime import datetime
from typing import List, Dict, Any
import requests as _requests
# anthropic SDK 为可选依赖：只在走官方端点（无 ANTHROPIC_BASE_URL）时才需要。
# 不在顶层 import，避免云桌面等未安装 anthropic 包的环境启动即崩溃。

from schemas import (
    IntelligenceDecodeRequest,
    DecodedIntelligence,
    Signal,
    SignalType,
    SourceType
)
from prompt_templates import build_prompt, build_screen_prompt, PROMPT_VERSION
from llm_client import LLMClient


class IntelligenceDecoder:
    """情报解码器 - Prompt-first + 轻量后处理策略"""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6",
                 screen_model: str = None,
                 enable_two_stage: bool = True,
                 provider: str = "anthropic",
                 base_url: str = None,
                 connect_timeout_seconds: int = 30,
                 read_timeout_seconds: int = 180,
                 max_retries: int = 3):
        """
        初始化解码器

        Args:
            api_key: LLM API key
            model: 精筛模型
            screen_model: 粗筛模型；未指定时，Anthropic 默认用 Claude Haiku，其他 provider 复用主模型
            enable_two_stage: 是否启用两阶段筛选（默认开启）
            provider: LLM provider（anthropic / openai / deepseek / gemini / custom）
            base_url: 自定义 API 端点；未指定时按 provider 或环境变量兜底
            connect_timeout_seconds: HTTP connect timeout（秒）
            read_timeout_seconds: HTTP read timeout（秒）
            max_retries: LLM 请求最大重试次数
        """
        self.api_key = api_key
        self.provider = str(provider or "anthropic").strip().lower()
        env_base_url_map = {
            "anthropic": os.environ.get("ANTHROPIC_BASE_URL", ""),
            "openai": os.environ.get("OPENAI_BASE_URL", ""),
            "deepseek": os.environ.get("DEEPSEEK_BASE_URL", "") or os.environ.get("OPENAI_BASE_URL", ""),
            "gemini": os.environ.get("GEMINI_BASE_URL", ""),
            "doubao": os.environ.get("DOUBAO_BASE_URL", "") or os.environ.get("ARK_BASE_URL", "") or os.environ.get("OPENAI_BASE_URL", ""),
            "custom": os.environ.get("CUSTOM_LLM_BASE_URL", ""),
        }
        default_base_url_map = {
            "anthropic": "https://api.anthropic.com",
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
            "custom": "",
        }
        env_base_url = env_base_url_map.get(self.provider, "")
        default_base_url = default_base_url_map.get(self.provider, "")
        self.base_url = (base_url or env_base_url or default_base_url).rstrip("/")
        self.model = model
        self.screen_model = screen_model or (
            "claude-haiku-4-5-20251001" if self.provider == "anthropic" else model
        )
        self.enable_two_stage = enable_two_stage
        self.connect_timeout_seconds = max(1, int(connect_timeout_seconds or 30))
        self.read_timeout_seconds = max(1, int(read_timeout_seconds or 180))
        self.max_retries = max(1, int(max_retries or 3))
        self.decoder_version = PROMPT_VERSION
        self.debug_enabled = os.environ.get("PHASE21_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        # Anthropic SDK client：只在走官方 Anthropic 端点时初始化；
        # openai/gemini/custom 以及 anthropic 中转都走 requests。
        if self.provider == "anthropic" and self.base_url == "https://api.anthropic.com":
            try:
                from anthropic import Anthropic as _Anthropic
                self.client = _Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "当前 2.1 配置使用官方 Anthropic 端点，但 anthropic 包未安装。\n"
                    "请二选一：\n"
                    "  1) 安装 anthropic 包：pip install anthropic\n"
                    "  2) 改用兼容 API 并提供 base_url"
                )
        else:
            self.client = LLMClient(
                api_key=api_key,
                base_url=self.base_url,
                provider=self.provider,
            )

    def _debug(self, message: str) -> None:
        if self.debug_enabled:
            print(f"[decoder-debug] {message}", flush=True)

    def _write_debug_artifact(self, source_id: str, stage: str, payload: Dict[str, Any]) -> None:
        if not self.debug_enabled:
            return
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_artifacts", "phase2.1")
            os.makedirs(debug_dir, exist_ok=True)
            safe_source_id = re.sub(r'[^A-Za-z0-9._-]+', '_', str(source_id or 'unknown'))
            safe_stage = re.sub(r'[^A-Za-z0-9._-]+', '_', str(stage or 'stage'))
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            path = os.path.join(debug_dir, f"{ts}_{safe_source_id}_{safe_stage}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._debug(f"artifact.written stage={stage} path={path}")
        except Exception as e:
            self._debug(f"artifact.write_failed stage={stage} error={type(e).__name__}: {e}")

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
            self._debug(
                f"decode.start source_id={request.source_id} source_type={request.source_type} text_len={len(cleaned_text)}"
            )

            # 检查文本长度
            if len(cleaned_text) < 50:
                warnings.append("原文过短（<50 字），可能影响抽取质量")

            # [1.5] 两阶段筛选：先粗筛，有信号才精筛
            if self.enable_two_stage:
                self._debug(f"decode.before_screen source_id={request.source_id} model={self.screen_model}")
                screen_result = self._screen(cleaned_text, request.source_type, warnings)
                self._debug(
                    f"decode.after_screen source_id={request.source_id} has_signal={screen_result.get('has_signal')} method={screen_result.get('screen_method')}"
                )
                if not screen_result["has_signal"]:
                    # 粗筛判断无信号，提前返回空结果
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    return DecodedIntelligence(
                        source_id=request.source_id,
                        source_type=request.source_type,
                        signals=[],
                        summary="粗筛判断：无范式信号",
                        decoder_version=self.decoder_version,
                        processing_time_ms=processing_time_ms,
                        warnings=warnings if warnings else None
                    )

            # [2] 构建 Prompt
            prompt = build_prompt(cleaned_text, request.source_id)

            # [3] LLM 调用
            self._debug(f"decode.before_main_llm source_id={request.source_id} model={self.model}")
            response = self._call_llm(prompt)
            self._debug(f"decode.after_main_llm source_id={request.source_id} response_len={len(response)}")
            self._write_debug_artifact(request.source_id, "main_response", {
                "provider": self.provider,
                "model": self.model,
                "response_len": len(response),
                "raw_response": response,
            })

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

    def _screen(self, text: str, source_type, warnings: List[str]) -> dict:
        """
        两阶段粗筛：先用规则快速排除，再用 haiku 轻量判断。

        方向四（source_type 规则预筛）：
          - report 类型：含大量泛趋势关键词且无具体事件名称 → 直接跳过 LLM
        方向二（haiku 粗筛）：
          - 规则未排除的内容，用 screen_model 轻量判断有无范式信号

        Returns:
            {"has_signal": bool, "signal_types": list, "screen_method": str}
        """
        # ── 规则层：source_type 预筛 ──────────────────────────────
        source_type_val = source_type.value if hasattr(source_type, 'value') else str(source_type)
        if source_type_val == "report":
            # 泛趋势关键词（无具体事实支撑的预测/分析）
            noise_patterns = [
                "will transform", "is expected to", "analysts predict", "forecast",
                "is projected", "在未来", "预计将", "有望", "将改变",
                "survey shows", "survey reveals", "according to analysts",
                "market research", "industry analysts", "by 2026", "by 2027", "by 2030",
            ]
            text_lower = text.lower()
            noise_hits = sum(1 for p in noise_patterns if p.lower() in text_lower)

            # 报告类文本里有 3+ 个泛趋势关键词，且文本较短（<500字，更可能是纯预测）→ 直接跳过
            if noise_hits >= 3 and len(text) < 500:
                warnings.append(f"规则预筛：report 类型含 {noise_hits} 个趋势预测关键词，判定为噪音，跳过 LLM")
                return {"has_signal": False, "signal_types": [], "screen_method": "rule"}

        # ── LLM 粗筛层：haiku 轻量判断 ───────────────────────────
        try:
            screen_prompt = build_screen_prompt(text)
            self._debug(f"screen.before_llm model={self.screen_model} text_len={len(text)}")
            raw = self._call_llm(screen_prompt, model_override=self.screen_model, max_tokens=80)
            self._debug(f"screen.after_llm model={self.screen_model} response_len={len(raw)}")
            self._write_debug_artifact("screen", "screen_response", {
                "provider": self.provider,
                "model": self.screen_model,
                "response_len": len(raw),
                "raw_response": raw,
                "text_len": len(text),
            })
            # 解析 JSON
            json_match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                has_signal = result.get("has_signal", True)  # 解析失败默认放行
                signal_types = result.get("signal_types", [])
                if not has_signal:
                    warnings.append(f"LLM粗筛（{self.screen_model}）：判定无范式信号，跳过精筛")
                return {"has_signal": has_signal, "signal_types": signal_types, "screen_method": "llm"}
        except Exception as e:
            self._write_debug_artifact("screen", "screen_parse_error", {
                "provider": self.provider,
                "model": self.screen_model,
                "error_type": type(e).__name__,
                "error": str(e),
                "raw_response": raw if 'raw' in locals() else "",
                "text_len": len(text),
            })
            # 粗筛失败不阻塞：放行进入精筛
            warnings.append(f"粗筛失败（{e}），放行进入精筛")

        return {"has_signal": True, "signal_types": [], "screen_method": "fallback"}

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

    def _call_llm(self, prompt: str, max_retries: int = None,
                  model_override: str = None, max_tokens: int = 4096) -> str:
        """
        调用 LLM（带重试机制）

        Args:
            prompt: 完整 Prompt
            max_retries: 最大重试次数（未指定时使用实例配置）
            model_override: 覆盖模型名（粗筛时传 screen_model）
            max_tokens: 最大输出 token 数（粗筛时传 80）
        """
        model = model_override or self.model
        retry_count = max(1, int(max_retries or self.max_retries))
        timeout_tuple = (self.connect_timeout_seconds, self.read_timeout_seconds)
        for attempt in range(retry_count):
            try:
                if self.provider == "anthropic" and self.base_url == "https://api.anthropic.com":
                    self._debug(
                        f"llm.request provider=anthropic sdk model={model} attempt={attempt + 1}/{retry_count} max_tokens={max_tokens} timeout={timeout_tuple}"
                    )
                    # 官方 Anthropic 端点：使用 SDK（self.client 在 __init__ 中初始化）
                    message = self.client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=0.0,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    text = message.content[0].text
                    self._debug(
                        f"llm.response provider=anthropic sdk model={model} attempt={attempt + 1}/{retry_count} response_len={len(text)}"
                    )
                    return text

                if self.provider == "anthropic":
                    # Anthropic 中转代理：优先尝试 /messages，失败时回退到 /v1/messages
                    candidate_urls = [
                        self.base_url.rstrip("/") + "/messages",
                        self.base_url.rstrip("/") + "/v1/messages",
                    ]
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    }
                    payload = {
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": 0.0,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                    last_error = None
                    for candidate_url in candidate_urls:
                        try:
                            self._debug(
                                f"llm.request provider=anthropic proxy model={model} attempt={attempt + 1}/{retry_count} max_tokens={max_tokens} timeout={timeout_tuple} url={candidate_url}"
                            )
                            resp = _requests.post(candidate_url, headers=headers, json=payload, timeout=timeout_tuple)
                            self._debug(
                                f"llm.http_response provider=anthropic proxy model={model} attempt={attempt + 1}/{retry_count} status={resp.status_code} url={candidate_url}"
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            for block in data.get("content", []):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    self._debug(
                                        f"llm.response provider=anthropic proxy model={model} attempt={attempt + 1}/{retry_count} response_len={len(text)} url={candidate_url}"
                                    )
                                    return text
                            self._debug(
                                f"llm.response provider=anthropic proxy model={model} attempt={attempt + 1}/{retry_count} response_len=0 url={candidate_url}"
                            )
                            return ""
                        except Exception as proxy_error:
                            last_error = proxy_error
                            self._debug(
                                f"llm.proxy_candidate_error provider=anthropic model={model} attempt={attempt + 1}/{retry_count} url={candidate_url} error={type(proxy_error).__name__}: {proxy_error}"
                            )
                    raise last_error

                self._debug(
                    f"llm.request provider={self.provider} shared_client model={model} attempt={attempt + 1}/{retry_count} max_tokens={max_tokens} timeout={timeout_tuple}"
                )
                text = self.client.call(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.0,
                    max_retries=1,
                )
                self._debug(
                    f"llm.response provider={self.provider} shared_client model={model} attempt={attempt + 1}/{retry_count} response_len={len(text)}"
                )
                return text

            except Exception as e:
                self._debug(
                    f"llm.error provider={self.provider} model={model} attempt={attempt + 1}/{retry_count} error={type(e).__name__}: {str(e)}"
                )
                if attempt < retry_count - 1:
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
            raw_signals = data.get("signals", [])
            signals = []

            # 格式规范化 + 保守多方向拆分兜底
            for raw_signal in raw_signals:
                for signal in self._split_multi_direction_signal(raw_signal, warnings):
                    # 去除多余空格
                    if "signal_label" in signal and isinstance(signal.get("signal_label"), str):
                        signal["signal_label"] = signal["signal_label"].strip()
                    if "description" in signal and isinstance(signal.get("description"), str):
                        signal["description"] = signal["description"].strip()
                    if "evidence_text" in signal and isinstance(signal.get("evidence_text"), str):
                        signal["evidence_text"] = signal["evidence_text"].strip()

                    # 字段补全：如果 entities 为空，尝试从 evidence_text 提取
                    if not signal.get("entities") and signal.get("evidence_text"):
                        # 简单的实体提取（可以后续增强）
                        signal["entities"] = []

                    # 确保 source_ref 正确
                    signal["source_ref"] = source_id

                    # 确保 extracted_at 存在
                    if "extracted_at" not in signal:
                        signal["extracted_at"] = datetime.utcnow().isoformat() + "Z"

                    self._normalize_signal_contract(signal, source_id, warnings)
                    self._audit_signal_reliability(signal)
                    signals.append(signal)

            # 去重：同一 source 内的重复信号
            unique_signals = []
            seen = set()
            for signal in signals:
                logic_frame = signal.get("logic_frame") or {}
                key = (
                    signal.get("signal_type"),
                    signal.get("signal_label"),
                    logic_frame.get("what_changed", ""),
                    logic_frame.get("change_direction", "")
                )
                if key not in seen:
                    seen.add(key)
                    unique_signals.append(signal)

            return unique_signals

        except json.JSONDecodeError as e:
            self._write_debug_artifact(source_id, "main_parse_error", {
                "provider": self.provider,
                "model": self.model,
                "error_type": type(e).__name__,
                "error": str(e),
                "raw_response": response,
            })
            warnings.append(f"JSON 解析失败: {str(e)}")
            return []
        except Exception as e:
            self._write_debug_artifact(source_id, "main_post_process_error", {
                "provider": self.provider,
                "model": self.model,
                "error_type": type(e).__name__,
                "error": str(e),
                "raw_response": response,
            })
            warnings.append(f"后处理失败: {str(e)}")
            return []

    def _split_multi_direction_signal(
        self,
        signal: Dict[str, Any],
        warnings: List[str]
    ) -> List[Dict[str, Any]]:
        """对少数明显违约的多方向输出做保守兜底拆分。"""
        logic_frame = signal.get("logic_frame")
        if not isinstance(logic_frame, dict):
            return [signal]

        directions = self._extract_direction_tokens(logic_frame.get("change_direction", ""))
        if len(directions) <= 1:
            return [signal]

        what_changed_parts = self._split_multi_value_field(logic_frame.get("what_changed", ""))
        if len(what_changed_parts) != len(directions):
            self._add_audit_flag(signal, "multi_direction_detected_not_split")
            return [signal]

        evidence_parts = self._split_clause_text(signal.get("evidence_text", ""), len(directions))
        description_parts = self._split_clause_text(signal.get("description", ""), len(directions))

        base_signal_id = str(signal.get("signal_id", "") or "sig")
        base_label = str(signal.get("signal_label", "") or "").strip()
        split_signals = []

        for index, direction in enumerate(directions, start=1):
            split_signal = copy.deepcopy(signal)
            split_signal["signal_id"] = f"{base_signal_id}_split_{index}"

            if base_label:
                split_signal["signal_label"] = f"{base_label} [{direction}]"

            if len(description_parts) == len(directions):
                split_signal["description"] = description_parts[index - 1]
            else:
                self._add_audit_flag(split_signal, "split_reused_description")

            if len(evidence_parts) == len(directions):
                split_signal["evidence_text"] = evidence_parts[index - 1]
            else:
                self._add_audit_flag(split_signal, "split_reused_evidence_text")

            split_logic_frame = split_signal.setdefault("logic_frame", {})
            split_logic_frame["what_changed"] = what_changed_parts[index - 1]
            split_logic_frame["change_direction"] = direction
            self._add_audit_flag(split_signal, "decoder_split_by_direction_fallback")
            split_signals.append(split_signal)

        warnings.append(
            f"信号 {base_signal_id} 检测到多方向输出，decoder 已保守拆分为 {len(split_signals)} 条"
        )
        return split_signals

    @staticmethod
    def _extract_direction_tokens(value: Any) -> List[str]:
        text = str(value or "").strip().lower()
        if not text:
            return []

        pattern = r'(?<![a-z])(invalidate|validate|increase|decrease|tighten|loosen|unknown|enter|shift|exit)(?![a-z])'
        matches = re.findall(pattern, text)

        directions = []
        seen = set()
        for match in matches:
            if match not in seen:
                seen.add(match)
                directions.append(match)
        return directions

    @staticmethod
    def _split_multi_value_field(value: Any) -> List[str]:
        text = str(value or "").strip()
        if not text:
            return []

        parts = re.split(
            r'\s*(?:/|\||;|；|,|，|、|→|->|=>|\band\b|\bor\b|与|和|及|以及)\s*',
            text,
            flags=re.IGNORECASE
        )
        return [part.strip() for part in parts if part and part.strip()]

    @staticmethod
    def _split_clause_text(value: Any, expected_parts: int) -> List[str]:
        text = str(value or "").strip()
        if not text or expected_parts <= 1:
            return []

        parts = re.split(
            r'\s*(?:;|；|。|\.\s+|,\s+and\s+|,\s+but\s+|,\s+while\s+|，并且|，并|同时|而同时)\s*',
            text,
            flags=re.IGNORECASE
        )
        parts = [part.strip() for part in parts if part and part.strip()]
        if len(parts) == expected_parts:
            return parts
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

    def _normalize_signal_contract(
        self,
        signal: Dict[str, Any],
        source_id: str,
        warnings: List[str]
    ) -> None:
        """规范化 2.1 输出契约，并尽量保留原始信号。"""
        metadata = self._ensure_audit_metadata(signal)

        raw_signal_type = signal.get("signal_type", "")
        normalized_signal_type = str(raw_signal_type).strip().lower() if raw_signal_type is not None else ""
        metadata["raw_signal_type"] = raw_signal_type
        metadata["normalized_signal_type"] = normalized_signal_type
        signal["signal_type"] = normalized_signal_type or "market"

        for score_field in ["intensity_score", "confidence_score", "timeliness_score"]:
            raw_score = signal.get(score_field, 5)
            try:
                score = int(raw_score)
            except Exception:
                self._add_audit_flag(signal, f"invalid_{score_field}")
                score = 5
            score = max(1, min(10, score))
            signal[score_field] = score

        logic_frame = signal.get("logic_frame")
        if not logic_frame:
            self._add_audit_flag(signal, "missing_logic_frame")
            return

        if not isinstance(logic_frame, dict):
            self._add_audit_flag(signal, "invalid_logic_frame")
            signal["logic_frame"] = None
            return

        what_changed = str(logic_frame.get("what_changed", "") or "").strip()
        raw_direction = str(logic_frame.get("change_direction", "") or "").strip().lower()
        affects = logic_frame.get("affects", [])

        allowed_directions = {
            "increase", "decrease", "tighten", "loosen", "enter",
            "exit", "shift", "validate", "invalidate", "unknown"
        }

        if not what_changed:
            self._add_audit_flag(signal, "missing_what_changed")

        if raw_direction not in allowed_directions:
            if raw_direction:
                self._add_audit_flag(signal, "invalid_change_direction")
            raw_direction = "unknown"

        if isinstance(affects, str):
            affects = [affects]
        elif not isinstance(affects, list):
            self._add_audit_flag(signal, "invalid_affects")
            affects = []

        normalized_affects = []
        for item in affects:
            text = str(item).strip()
            if text:
                normalized_affects.append(text)

        if not what_changed:
            signal["logic_frame"] = None
            return

        signal["logic_frame"] = {
            "what_changed": what_changed,
            "change_direction": raw_direction,
            "affects": normalized_affects,
        }

    def _audit_signal_reliability(self, signal: Dict[str, Any]) -> None:
        """生成轻量 audit flags，不阻断主链路。"""
        intensity = signal.get("intensity_score", 5)
        confidence = signal.get("confidence_score", 5)
        evidence_text = str(signal.get("evidence_text", "") or "")
        evidence_lower = evidence_text.lower()

        if confidence <= 4 and intensity >= 8:
            self._add_audit_flag(signal, "low_conf_high_intensity")

        if len(evidence_text) < 60 and intensity >= 8:
            self._add_audit_flag(signal, "short_evidence_high_intensity")

        uncertain_markers = ["reportedly", "rumor", "rumour", "可能", "据称", "传闻", "分析师认为"]
        if confidence >= 8 and any(marker in evidence_lower for marker in uncertain_markers):
            self._add_audit_flag(signal, "uncertain_wording_high_confidence")

        official_markers = ["announced", "confirmed", "official", "版权局", "委员会", "发布报告", "正式"]
        if confidence <= 4 and any(marker in evidence_lower for marker in official_markers):
            self._add_audit_flag(signal, "official_wording_low_confidence")

    @staticmethod
    def _ensure_audit_metadata(signal: Dict[str, Any]) -> Dict[str, Any]:
        metadata = signal.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            signal["metadata"] = metadata
        audit = metadata.get("audit")
        if not isinstance(audit, dict):
            audit = {}
            metadata["audit"] = audit
        flags = audit.get("audit_flags")
        if not isinstance(flags, list):
            audit["audit_flags"] = []
        return audit

    def _add_audit_flag(self, signal: Dict[str, Any], flag: str) -> None:
        audit = self._ensure_audit_metadata(signal)
        flags = audit.setdefault("audit_flags", [])
        if flag not in flags:
            flags.append(flag)

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
            "capital": "资本信号",
            "regulatory": "监管信号"
        }

        for signal_type, count in signal_counts.items():
            summary_parts.append(f"{type_names.get(signal_type, signal_type)} {count} 个")

        return f"检测到 {len(signals)} 个范式信号：" + "、".join(summary_parts)