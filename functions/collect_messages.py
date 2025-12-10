def collect_messages(data: dict) -> list[dict]:
    all_messages: list[dict] = []

    for section in ("chats", "left_chats"):
        chats = data.get(section, {}).get("list", []) or []
        for chat in chats:
            if not isinstance(chat, dict):
                continue
            for msg in (chat.get("messages") or []):
                if isinstance(msg, dict):
                    all_messages.append(msg)

    return all_messages
