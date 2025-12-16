import itertools
import regex as re
import emoji
from typing import Final, Set

from models.stats_model import Stats

NON_WORD_RE: Final = re.compile(r"[^\w\s]+", re.UNICODE | re.VERSION1)

EMOJI_FINDER = (
    emoji.get_emoji_regexp()
    if hasattr(emoji, "get_emoji_regexp")
    else re.compile(r"\p{Emoji}", re.UNICODE)
)

def get_author(msg: dict) -> str | None:
    if not isinstance(msg, dict):
        return None

    if msg.get("type") != "message":
        return None

    return (
        msg.get("from")
        or msg.get("actor")
        or msg.get("author")
    )

def get_bot_names(data: dict) -> set[str]:
    bot_names = set()
    
    chats = data.get("chats", {}).get("list") or []
    left_chats = data.get("left_chats", {}).get("list") or []
    
    for chat in itertools.chain(chats, left_chats):
        if chat.get("type") == "bot_chat":
            name = chat.get("name")
            if name:
                bot_names.add(name)
                
    return bot_names


def _get_plain_text(message: dict) -> str | None:
    entities = message.get("text_entities")
    if entities:
        first = entities[0]
        if first.get("type") == "plain":
            return first.get("text")
    return None


def get_messages(message: dict, author: str, stats: Stats) -> None:
    stats.messages_total[author] += 1
    
    if message.get("media_type") == "voice_message":
        if not _get_plain_text(message):
            stats.voice_total[author] += 1


def get_reactions(message: dict, stats: Stats) -> None:
    reactions = message.get("reactions")
    if not reactions:
        return

    for reaction in reactions:
        emoji_token = reaction.get("emoji") or reaction.get("document_id")
        if not emoji_token:
            continue

        recent = reaction.get("recent")
        if not recent:
            continue

        for ra in recent:
            user_id = ra.get("from") or ra.get("from_id")
            if not user_id:
                continue

            reaction_stats = stats.reactions[user_id][emoji_token]
            reaction_stats["value"] += 1


def get_emojis(message: dict, author: str, stats: Stats) -> None:
    entities = message.get("text_entities") or []
    if not entities:
        return

    for ent in entities:
        if ent.get("type") not in ("plain", "custom_emoji"):
            continue

        text = ent.get("text")
        if not isinstance(text, str):
            continue

        path = ent.get("document_id")

        for emo in emoji.emoji_list(text):
            token = emo.get("emoji")
            if not token:
                continue

            e = stats.emojis[author][token]
            e["value"] += 1

            if path:
                e["path"] = path


def get_word(message: dict, author: str, stats: Stats, stopset: Set[str]) -> None:
    text = _get_plain_text(message)
    if not text:
        return

    clean_text = NON_WORD_RE.sub(" ", text).casefold()
    author_words_counter = stats.words[author]
    
    for token in clean_text.split():
        if token not in stopset:
            author_words_counter[token] += 1


def format_authors(stats: Stats) -> list[dict]:
    authors_arr = []
    for author_name in stats.messages_total.keys():
        authors_arr.append({
            "name": author_name,
            "messages_total": stats.messages_total[author_name],
            "voice_message_total": stats.voice_total[author_name],
            "top_emojis": [
                {
                    "emoji": e,
                    "value": d["value"],
                    **({"path": d["path"]} if d.get("path") else {})
                }
                for e, d in sorted(
                    stats.emojis[author_name].items(),
                    key=lambda x: x[1]["value"],
                    reverse=True
                )[:10]
            ],
            "top_words": [
                {"word": w, "value": v}
                for w, v in stats.words[author_name].most_common(10)
            ],
            "top_reactions": [
                {
                    "emoji": e,
                    "value": d["value"],
                    **({"path": d["path"]} if d.get("path") else {})
                }
                for e, d in sorted(
                    stats.reactions[author_name].items(),
                    key=lambda x: x[1]["value"],
                    reverse=True
                )[:10]
            ],
        })
    return authors_arr


def get_top_dialogs(messages: list[dict], owner: str) -> list[dict]:
    if not owner or not messages:
        return []
    
    owner_chats = {}
    for msg in messages:
        if msg.get("from") != owner:
            continue

        cid = msg.get("chat_id")
        cname = msg.get("chat_name") or "Unknown chat"

        if cid not in owner_chats:
            owner_chats[cid] = {
                "chat_id": cid,
                "name": cname,
                "messages_from_owner": 0,
            }

        owner_chats[cid]["messages_from_owner"] += 1

    return sorted(
        owner_chats.values(),
        key=lambda x: x["messages_from_owner"],
        reverse=True
    )[:5]