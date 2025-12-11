import itertools

def collect_messages(data: dict) -> list[dict]:

    chats_list = data.get("chats", {}).get("list")
    left_chats_list = data.get("left_chats", {}).get("list")
    
    if chats_list or left_chats_list:
        all_messages = []
        source_lists = (l for l in (chats_list, left_chats_list) if l)
        
        for chat_list in source_lists:
            for chat in chat_list:
                msgs = chat.get("messages")
                if msgs and isinstance(msgs, list):
                    all_messages.extend(msgs)
        return all_messages

    root_msgs = data.get("messages")
    if root_msgs and isinstance(root_msgs, list):
        return root_msgs

    return []