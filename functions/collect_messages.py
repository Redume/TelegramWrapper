import itertools


def collect_messages(data: dict, ignored_authors: set[str]) -> list[dict]:
    chats_list = data.get("chats", {}).get("list")
    left_chats_list = data.get("left_chats", {}).get("list")
    
    if chats_list or left_chats_list:
        all_messages = []
        source_lists = (l for l in (chats_list, left_chats_list) if l)
        
        for chat in itertools.chain.from_iterable(source_lists):
            msgs = chat.get("messages")
            
            if msgs and isinstance(msgs, list):
                filtered = [
                    msg for msg in msgs 
                    if isinstance(msg, dict) 
                    and msg.get("type") != "service"
                    and msg.get("from") not in ignored_authors
                ]
                all_messages.extend(filtered)
                
        return all_messages

    root_msgs = data.get("messages")
    if root_msgs and isinstance(root_msgs, list):
        return [
            msg for msg in root_msgs 
            if isinstance(msg, dict) 
            and msg.get("type") != "service"
            and msg.get("from") not in ignored_authors
        ]

    return []