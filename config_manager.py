"""
config_manager.py - Oyun Ayarları Yöneticisi
===============================================
Kalıcı ayarları JSON dosyasından yükler ve kaydeder.
"""

import json
import os
from typing import Any, Dict

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_config.json")

# Kullanilabilir AI modelleri (OpenAI uyumlu API)
AVAILABLE_MODELS = [
    # Google Gemini
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    # OpenAI GPT
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.1",
    # OpenAI o-serisi
    "o4-mini",
    "o3",
    "o3-mini",
    # Anthropic Claude
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    # Meta Llama (OpenRouter vb.)
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-3.3-70b-instruct",
    # Ozel model (kullanici girer)
    "Ozel...",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model_name": "gemini-2.5-flash",
    "max_tokens": 1024,
    "camera_index": 0,
}


def load_config() -> Dict[str, Any]:
    """Ayarlari JSON dosyasindan yukler. Dosya yoksa varsayilan deger dondurur."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass  # Bozuk dosya - varsayilan kullan
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Ayarlari JSON dosyasina kaydeder."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[*] Ayarlar kaydedildi: {CONFIG_FILE}")
    except IOError as e:
        print(f"[!] Ayarlar kaydedilemedi: {e}")


def mask_api_key(key: str) -> str:
    """API anahtarini gosterim icin maskeler (ilk 4 ve son 4 karakter gorunur)."""
    if len(key) <= 10:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]
