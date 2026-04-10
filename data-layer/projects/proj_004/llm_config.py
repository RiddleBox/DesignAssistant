"""
llm_config.py — 统一 LLM 配置加载器

用法：
    from llm_config import get_llm_config
    cfg = get_llm_config("2.1")
    # cfg = { "api_key": "...", "base_url": "...", "model": "...", "max_tokens": 4096, "temperature": 0.0 }

    from llm_config import make_llm_client
    client = make_llm_client("2.2")
    # 返回 LLMClient 实例，直接可用
"""

import os
import importlib.util

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False

# 配置文件路径（与本文件同目录）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_CONFIG_PATH = os.path.join(_THIS_DIR, "llm_config.local.yaml")
_TEMPLATE_CONFIG_PATH = os.path.join(_THIS_DIR, "llm_config.yaml")


def _get_existing_config_paths():
    """按优先级返回存在的配置文件路径：模板在前，本地覆盖在后"""
    paths = []
    if os.path.exists(_TEMPLATE_CONFIG_PATH):
        paths.append(_TEMPLATE_CONFIG_PATH)
    if os.path.exists(_LOCAL_CONFIG_PATH):
        paths.append(_LOCAL_CONFIG_PATH)
    return paths


def _deep_merge_dict(base: dict, override: dict) -> dict:
    """递归合并字典：override 覆盖 base，同名子字典继续深合并"""
    result = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


# .env 搜索顺序：当前目录 → 上1级 → 上2级 → 上3级（项目根）
def _find_env_path():
    d = _THIS_DIR
    for _ in range(4):
        p = os.path.join(d, ".env")
        if os.path.exists(p):
            return p
        d = os.path.dirname(d)
    return None

_ENV_PATH = _find_env_path()


def _provider_env_defaults(provider: str) -> dict:
    provider = (provider or "anthropic").strip().lower()
    mapping = {
        "anthropic": {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "base_url": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        },
        "openai": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        },
        "deepseek": {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", ""),
            "base_url": os.environ.get("DEEPSEEK_BASE_URL", "") or os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com"),
        },
        "gemini": {
            "api_key": os.environ.get("GEMINI_API_KEY", ""),
            "base_url": os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
        },
        "doubao": {
            "api_key": os.environ.get("DOUBAO_API_KEY", "") or os.environ.get("ARK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", ""),
            "base_url": os.environ.get("DOUBAO_BASE_URL", "") or os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3") or os.environ.get("OPENAI_BASE_URL", ""),
        },
        "custom": {
            "api_key": os.environ.get("CUSTOM_LLM_API_KEY", ""),
            "base_url": os.environ.get("CUSTOM_LLM_BASE_URL", ""),
        },
    }
    return mapping.get(provider, mapping["anthropic"])


def _load_env():
    """加载 .env 文件（不覆盖已有环境变量）"""
    if not _ENV_PATH:
        return
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _load_yaml_config() -> dict:
    """先加载模板默认值，再叠加本地私有覆盖"""
    if not _has_yaml:
        return {}

    config_paths = _get_existing_config_paths()
    if not config_paths:
        return {}

    merged = {}
    for config_path in config_paths:
        with open(config_path, encoding="utf-8") as f:
            merged = _deep_merge_dict(merged, yaml.safe_load(f) or {})
    return merged


def get_llm_config(phase: str = None) -> dict:
    """
    获取指定阶段的 LLM 配置，自动合并 default + 环境变量。

    Args:
        phase: "2.1" / "2.2" / "2.3" / "2.4" / "2.5"，None 时只用 default

    Returns:
        dict with keys: provider, api_key, base_url, model, max_tokens, temperature,
        connect_timeout_seconds, read_timeout_seconds, max_retries,
        max_parallel_samples, request_spacing_ms, step1_cooldown_seconds
    """
    _load_env()
    raw = _load_yaml_config()

    # 1. 全局 default
    default = raw.get("default", {})
    cfg = {
        "provider":               default.get("provider", "anthropic"),
        "api_key":                default.get("api_key", ""),
        "base_url":               default.get("base_url", ""),
        "model":                  default.get("model", "claude-sonnet-4-6"),
        "max_tokens":             default.get("max_tokens", 4096),
        "temperature":            default.get("temperature", 0.0),
        "connect_timeout_seconds": default.get("connect_timeout_seconds", 30),
        "read_timeout_seconds":    default.get("read_timeout_seconds", 180),
        "max_retries":             default.get("max_retries", 3),
        "max_parallel_samples":    default.get("max_parallel_samples", 1),
        "request_spacing_ms":      default.get("request_spacing_ms", 0),
        "step1_cooldown_seconds":  default.get("step1_cooldown_seconds", 0),
    }

    # 2. 阶段覆盖
    if phase:
        phase_cfg = raw.get("phases", {}).get(str(phase), {})
        for k, v in phase_cfg.items():
            if v is not None and v != "":
                cfg[k] = v

    provider_env = _provider_env_defaults(cfg["provider"])

    # 3. 环境变量兜底（yaml 没填 api_key/base_url 时，按 provider 取值）
    if not cfg["api_key"]:
        cfg["api_key"] = provider_env["api_key"]
    if not cfg["base_url"]:
        cfg["base_url"] = provider_env["base_url"]

    if cfg["provider"] in {"deepseek", "doubao"} and cfg["base_url"]:
        cfg["base_url"] = cfg["base_url"].rstrip("/")

    return cfg


def make_llm_client(phase: str = None):
    """
    创建指定阶段的 LLMClient 实例。

    Returns:
        LLMClient 实例，或 None（若 llm_client.py 不存在）
    """
    cfg = get_llm_config(phase)
    if not cfg.get("api_key"):
        return None
    client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_client.py")
    if not os.path.exists(client_path):
        return None

    spec = importlib.util.spec_from_file_location("llm_client", client_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.LLMClient(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        provider=cfg.get("provider", "anthropic"),
    )


def print_config_summary():
    """打印各阶段配置摘要（调试用）"""
    _load_env()
    print("LLM 配置摘要:")
    active_paths = _get_existing_config_paths()
    if active_paths:
        print(f"  配置文件: {' + '.join(os.path.basename(path) for path in active_paths)}")
    else:
        print("  配置文件: 不存在，使用环境变量")
    for phase in [None, "2.1", "2.2", "2.3", "2.4", "2.5"]:
        cfg = get_llm_config(phase)
        key_hint = cfg['api_key'][:12] + "..." if cfg['api_key'] else "(未设置)"
        label = f"phase {phase}" if phase else "default "
        print(f"  {label}: model={cfg['model']:25s} key={key_hint}  base_url={cfg['base_url']}")


if __name__ == "__main__":
    print_config_summary()
