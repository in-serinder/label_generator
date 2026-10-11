import os
import configparser

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.ini")

config = configparser.ConfigParser()


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


def add_to_history(section, new_value):
    if not new_value.strip():
        return
    load_history()
    items = get_history_list(section)
    if new_value not in items:
        items.insert(0, new_value)
        if len(items) > 50:
            items = items[:50]
        if section == "types":
            save_history(",".join(items), config.get("history", "packages") if config.has_option("history", "packages") else "", config.get("history", "values") if config.has_option("history", "values") else "")
        elif section == "packages":
            save_history(config.get("history", "types") if config.has_option("history", "types") else "", ",".join(items), config.get("history", "values") if config.has_option("history", "values") else "")
        elif section == "values":
            save_history(config.get("history", "types") if config.has_option("history", "types") else "", config.get("history", "packages") if config.has_option("history", "packages") else "", ",".join(items))