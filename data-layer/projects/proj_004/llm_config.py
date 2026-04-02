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


def _get_active_config_path():
    """优先使用本地私有配置，否则回退到可提交模板配置"""
    if os.path.exists(_LOCAL_CONFIG_PATH):
        return _LOCAL_CONFIG_PATH
    if os.path.exists(_TEMPLATE_CONFIG_PATH):
        return _TEMPLATE_CONFIG_PATH
    return None

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
        "gemini": {
            "api_key": os.environ.get("GEMINI_API_KEY", ""),
            "base_url": os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
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
    """优先加载本地私有配置，其次加载可提交模板配置"""
    if not _has_yaml:
        return {}

    config_path = _get_active_config_path()
    if not config_path:
        return {}

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_llm_config(phase: str = None) -> dict:
    """
    获取指定阶段的 LLM 配置，自动合并 default + 环境变量。

    Args:
        phase: "2.1" / "2.2" / "2.3" / "2.4" / "2.5"，None 时只用 default

    Returns:
        dict with keys: provider, api_key, base_url, model, max_tokens, temperature
    """
    _load_env()
    raw = _load_yaml_config()

    # 1. 全局 default
    default = raw.get("default", {})
    cfg = {
        "provider":    default.get("provider", "anthropic"),
        "api_key":     default.get("api_key", ""),
        "base_url":    default.get("base_url", ""),
        "model":       default.get("model", "claude-sonnet-4-6"),
        "max_tokens":  default.get("max_tokens", 4096),
        "temperature": default.get("temperature", 0.0),
    }

    # 2. 阶段覆盖
    if phase:
        phase_cfg = raw.get("phases", {}).get(str(phase), {})
        for k, v in phase_cfg.items():
            if v:  # 非空才覆盖
                cfg[k] = v

    provider_env = _provider_env_defaults(cfg["provider"])

    # 3. 环境变量兜底（yaml 没填 api_key/base_url 时，按 provider 取值）
    if not cfg["api_key"]:
        cfg["api_key"] = provider_env["api_key"]
    if not cfg["base_url"]:
        cfg["base_url"] = provider_env["base_url"]

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
    active_path = _get_active_config_path()
    print(f"  配置文件: {os.path.basename(active_path) if active_path else '不存在，使用环境变量'}")
    for phase in [None, "2.1", "2.2", "2.3", "2.4", "2.5"]:
        cfg = get_llm_config(phase)
        key_hint = cfg['api_key'][:12] + "..." if cfg['api_key'] else "(未设置)"
        label = f"phase {phase}" if phase else "default "
        print(f"  {label}: model={cfg['model']:25s} key={key_hint}  base_url={cfg['base_url']}")


if __name__ == "__main__":
    print_config_summary()
