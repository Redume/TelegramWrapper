from typing import Set


def safe_get(d: dict, key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


def safe_list(val):
    return val if isinstance(val, list) else []


def safe_dict(val):
    return val if isinstance(val, dict) else {}


def get_author(msg: dict) -> str:
    if not isinstance(msg, dict):
        return "unknown"
    return msg.get("from") or msg.get("actor") or msg.get("from_id") or "unknown"


def get_bot_names(data: dict) -> Set[str]:
    bot_names = set()
    for chat in safe_list(data.get("chats", {}).get("list")) + safe_list(
        data.get("left_chats", {}).get("list")
    ):
        if safe_get(chat, "type") == "bot_chat":
            name = safe_get(chat, "name")
            if name:
                bot_names.add(name)
    return bot_names


def extract_text(message: dict) -> str:
    entities = safe_list(message.get("text_entities"))
    if entities:
        for ent in entities:
            t = ent.get("text")
            if t:
                return t
    text = message.get("text")
    if isinstance(text, str):
        return text
    elif isinstance(text, list):
        plain_texts = [t["text"] for t in text if isinstance(t, dict) and t.get("text")]
        return " ".join(plain_texts)
    return ""
