"""Minimal internationalization.

Add a new language by appending a dict to TRANSLATIONS and an entry to
LANGUAGES. Missing keys fall back to English, missing English falls back to the
key itself, so the app never crashes on a forgotten string.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

# (code, native label) — order defines the menu/dropdown order.
LANGUAGES = [
    ("en", "English"),
    ("it", "Italiano"),
    ("zh", "中文"),
]

TRANSLATIONS = {
    "en": {
        "no_data": "No data (keyboard off or disconnected)",
        "undetected": "Undetected",
        "charging_0": "Battery Mode",
        "charging_1": "Charging",
        "charging_2": "Fully charged",
        "age_suffix": "  ({sec}s ago)",
        "tooltip_waiting": "waiting…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "menu_settings": "Settings…",
        "menu_autostart": "Start with Windows",
        "menu_notify": "Low-battery notification",
        "menu_language": "Language",
        "menu_quit": "Quit",
        "notify_low_title": "Low battery",
        "notify_low_body": "Keyboard battery at {pct}%. Plug in the cable to charge.",
        "settings_title": "{app} — Settings",
        "settings_language": "Language",
        "settings_threshold": "Low-battery threshold (%)",
        "settings_notify": "Notify on low battery",
        "settings_smoothing": "Smoothing (lower = steadier)",
        "settings_autostart": "Start automatically with Windows",
        "settings_save": "Save",
        "settings_close": "Close",
        "settings_note": "Some changes apply immediately; language updates the menu too.",
        "cli_no_data": "No battery data (keyboard off/disconnected or firmware without support).",
        "cli_line": "Battery: {pct}%  ({mv} mV)  |  State: {charging}  |  Link: {transport}",
    },
    "it": {
        "no_data": "Nessun dato (tastiera spenta o disconnessa)",
        "undetected": "Non rilevata",
        "charging_0": "Modalità batteria",
        "charging_1": "In carica",
        "charging_2": "Carica completa",
        "age_suffix": "  (dato di {sec}s fa)",
        "tooltip_waiting": "in attesa…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "menu_settings": "Impostazioni…",
        "menu_autostart": "Avvio automatico con Windows",
        "menu_notify": "Notifica batteria bassa",
        "menu_language": "Lingua",
        "menu_quit": "Esci",
        "notify_low_title": "Batteria bassa",
        "notify_low_body": "Batteria tastiera al {pct}%. Collega il cavo per ricaricare.",
        "settings_title": "{app} — Impostazioni",
        "settings_language": "Lingua",
        "settings_threshold": "Soglia batteria bassa (%)",
        "settings_notify": "Notifica batteria bassa",
        "settings_smoothing": "Smoothing (più basso = più stabile)",
        "settings_autostart": "Avvia automaticamente con Windows",
        "settings_save": "Salva",
        "settings_close": "Chiudi",
        "settings_note": "Alcune modifiche sono immediate; la lingua aggiorna anche il menu.",
        "cli_no_data": "Nessun dato batteria (tastiera spenta/disconnessa o firmware senza supporto).",
        "cli_line": "Batteria: {pct}%  ({mv} mV)  |  Stato: {charging}  |  Connessione: {transport}",
    },
    "zh": {
        "no_data": "无数据（键盘已关闭或未连接）",
        "undetected": "未检测到",
        "charging_0": "电池模式",
        "charging_1": "充电中",
        "charging_2": "已充满",
        "age_suffix": "  （{sec} 秒前）",
        "tooltip_waiting": "等待中…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "menu_settings": "设置…",
        "menu_autostart": "开机自启动",
        "menu_notify": "低电量通知",
        "menu_language": "语言",
        "menu_quit": "退出",
        "notify_low_title": "电量低",
        "notify_low_body": "键盘电量 {pct}%。请插入数据线充电。",
        "settings_title": "{app} — 设置",
        "settings_language": "语言",
        "settings_threshold": "低电量阈值 (%)",
        "settings_notify": "低电量时通知",
        "settings_smoothing": "平滑（越低越稳定）",
        "settings_autostart": "随 Windows 自动启动",
        "settings_save": "保存",
        "settings_close": "关闭",
        "settings_note": "部分更改即时生效；语言也会更新菜单。",
        "cli_no_data": "无电池数据（键盘关闭/未连接或固件不支持）。",
        "cli_line": "电池：{pct}%（{mv} mV） | 状态：{charging} | 连接：{transport}",
    },
}

_current = DEFAULT_LANGUAGE


def available_languages():
    return list(LANGUAGES)


def set_language(lang: str) -> None:
    global _current
    if lang in TRANSLATIONS:
        _current = lang


def get_language() -> str:
    return _current


def language_label(lang: str) -> str:
    for code, label in LANGUAGES:
        if code == lang:
            return label
    return lang


def t(key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(_current, {}).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
