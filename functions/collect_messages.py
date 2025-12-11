import itertools

def collect_messages(data: dict) -> list[dict]:
    chats_list = data.get("chats", {}).get("list")
    left_chats_list = data.get("left_chats", {}).get("list")
    
    source_lists = (l for l in (chats_list, left_chats_list) if l)
    
    if chats_list or left_chats_list:
        all_messages = []
        all_chats = itertools.chain.from_iterable(source_lists)

        for chat in all_chats:
            msgs = chat.get("messages")
            
            if msgs and isinstance(msgs, list):

                filtered_msgs = [
                    msg for msg in msgs 
                    if isinstance(msg, dict) and msg.get("type") != "service"
                ]
                all_messages.extend(filtered_msgs)
                
        return all_messages

    root_msgs = data.get("messages")
    
    if root_msgs and isinstance(root_msgs, list):
        filtered_root_msgs = [
            msg for msg in root_msgs 
            if isinstance(msg, dict) and msg.get("type") != "service"
        ]
        return filtered_root_msgs

    return []