import os
import json
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "pyron"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"
MEMORY_DIR = CONFIG_DIR / "memory"
BUG_DB_FILE = CONFIG_DIR / "bugs.json"

DEFAULT_CONFIG = {
    "base_url": "https://opencode.ai/zen/v1/chat/completions",
    "model": "deepseek-v4-flash-free",
    "api_key": "public",
    "memory_enabled": True,
    "max_working_tokens": 180000,
    "compression_threshold": 140000,
    "reflection_interval_min": 8,
    "reflection_interval_max": 12,
    "forgetting_threshold": 0.05,
}


def load_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text()))
        except (json.JSONDecodeError, IOError):
            pass
    return cfg


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get_api_config() -> dict:
    cfg = load_config()
    return {
        "base_url": cfg.get("base_url", DEFAULT_CONFIG["base_url"]),
        "model": cfg.get("model", DEFAULT_CONFIG["model"]),
        "api_key": cfg.get("api_key", DEFAULT_CONFIG["api_key"]),
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


def get_memory_config() -> dict:
    cfg = load_config()
    return {
        "enabled": cfg.get("memory_enabled", True),
        "max_working_tokens": cfg.get("max_working_tokens", 180000),
        "compression_threshold": cfg.get("compression_threshold", 140000),
        "reflection_interval_min": cfg.get("reflection_interval_min", 8),
        "reflection_interval_max": cfg.get("reflection_interval_max", 12),
        "forgetting_threshold": cfg.get("forgetting_threshold", 0.05),
    }


def load_bug_db() -> list[dict]:
    if BUG_DB_FILE.exists():
        return json.loads(BUG_DB_FILE.read_text())
    return []


def save_bug_db(bugs: list[dict]):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BUG_DB_FILE.write_text(json.dumps(bugs, indent=2, ensure_ascii=False))


def add_bug(description: str, cause: str, solution: str, file_path: str = ""):
    bugs = load_bug_db()
    bugs.append({
        "description": description,
        "cause": cause,
        "solution": solution,
        "file": file_path,
        "timestamp": time.time(),
    })
    save_bug_db(bugs)
