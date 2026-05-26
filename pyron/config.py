import os
import json
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "pyron"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get_api_config() -> dict:
    cfg = load_config()
    return {
        "base_url": cfg.get("base_url", "https://opencode.ai/zen/v1/chat/completions"),
        "model": cfg.get("model", "deepseek-v4-flash-free"),
        "api_key": cfg.get("api_key", "public"),
    }


def set_api_config(base_url: str = None, model: str = None, api_key: str = None):
    cfg = load_config()
    if base_url:
        cfg["base_url"] = base_url
    if model:
        cfg["model"] = model
    if api_key:
        cfg["api_key"] = api_key
    save_config(cfg)
