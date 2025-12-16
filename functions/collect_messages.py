from typing import List, Set
from utils.fail_safe import safe_get, safe_list, safe_dict, get_author

def collect_messages(data: dict, ignored_authors: Set[str]) -> List[dict]:
    messages: List[dict] = []

    chats_list = safe_list(data.get("chats", {}).get("list"))
    left_chats_list = safe_list(data.get("left_chats", {}).get("list"))

    for chat in chats_list + left_chats_list:
        chat_type = safe_get(chat, "type", "unknown")
        chat_id = safe_get(chat, "id")
        chat_name = safe_get(chat, "name") or safe_get(chat, "title") or "Unknown chat"
        msgs = safe_list(chat.get("messages"))
        for msg in msgs:
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "service":
                continue
            author = get_author(msg)
            if author in ignored_authors:
                continue
            msg["chat_id"] = chat_id
            msg["chat_name"] = chat_name
            msg["chat_type"] = chat_type
            messages.append(msg)

    for msg in safe_list(data.get("messages")):
        if not isinstance(msg, dict):
            continue
        if msg.get("type") == "service":
            continue
        author = get_author(msg)
        if author in ignored_authors:
            continue
        msg["chat_id"] = None
        msg["chat_name"] = None
        msg["chat_type"] = "saved_messages"
        messages.append(msg)

    return messages