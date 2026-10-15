import os
import configparser

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.ini")

# 关闭插值：历史记录里可能包含 "%"（如 "10K 1%"），
# 默认的 BasicInterpolation 会把它当作插值符号并抛异常。
config = configparser.ConfigParser(interpolation=None)

# 默认标签尺寸（宽*高，毫米）
DEFAULT_SIZE = "50*25"


def load_history():
    if os.path.exists(HISTORY_FILE):
        config.read(HISTORY_FILE)
    else:
        config["history"] = {
            "types": "",
            "packages": "",
            "values": ""
        }
    return config


def save_history(types, packages, values):
    config["history"]["types"] = types
    config["history"]["packages"] = packages
    config["history"]["values"] = values
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        config.write(f)


def get_history_list(section):
    load_history()
    value = config.get("history", section) if config.has_option("history", section) else ""
    if value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def get_last_size(default=DEFAULT_SIZE):
    """读取上一次打印使用的标签尺寸，形如 "50*25"。"""
    load_history()
    try:
        value = config.get("size", "last").strip()
    except Exception:
        value = ""
    return value or default


def save_last_size(value):
    """记录本次打印使用的标签尺寸，下次启动自动回填。"""
    if not value or not str(value).strip():
        return
    load_history()
    if not config.has_section("size"):
        config["size"] = {}
    config["size"]["last"] = str(value).strip()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        config.write(f)


def add_to_history(section, new_value):
    if not new_value or not new_value.strip():
        return
    load_history()
    if not config.has_section("history"):
        config["history"] = {"types": "", "packages": "", "values": ""}
    items = get_history_list(section)
    if new_value in items:
        return
    items.insert(0, new_value)
    # 最多保留最近 50 条
    del items[50:]
    config["history"][section] = ",".join(items)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        config.write(f)