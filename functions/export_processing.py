import regex as re
import emoji
from typing import Final, Set

from models.stats_model import Stats

NON_WORD_RE: Final = re.compile(r"[^\w\s]+", re.UNICODE | re.VERSION1)

EMOJI_FINDER = emoji.get_emoji_regexp() if hasattr(emoji, "get_emoji_regexp") else re.compile(r"\p{Emoji}", re.UNICODE)


def get_author(message: dict) -> str | None:
    val = message.get("from")
    if val:
        s = str(val)
        return s if not s.startswith(' ') and not s.endswith(' ') else s.strip()
    return None


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
    reactions = message.get('reactions')
    if not reactions:
        return

    all_reactions_stats = stats.reactions

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

            user_stats = all_reactions_stats[user_id]

            try:
                user_stats[emoji_token]["value"] += 1
            except KeyError:
                user_stats[emoji_token] = {"value": 1}

def get_emojis(message: dict, author: str, stats: Stats) -> None:
    text_entity = (message.get("text_entities") or [None])[0]
    if not text_entity:
        return

    if text_entity.get("type") not in ['plain', 'custom_emoji']:
        return

    text = text_entity.get("text")
    path = text_entity.get("document_id", None)

    if not isinstance(text, str):
        return

    for emo in emoji.emoji_list(text):
        token = emo.get("emoji")
        if not token:
            continue

        if token not in stats.emojis[author]:
            stats.emojis[author][token] = {
                "value": 0,
                "path": path
            }

        stats.emojis[author][token]["value"] += 1
                 
    
def get_word(message: dict, author: str, stats: Stats, stopset: Set[str]) -> None:
    text = _get_plain_text(message)
    if not text:
        return

    clean_text = NON_WORD_RE.sub(" ", text).casefold()
    

    author_words_counter = stats.words[author]
    
    for token in clean_text.split():
        if token not in stopset:
            author_words_counter[token] += 1
