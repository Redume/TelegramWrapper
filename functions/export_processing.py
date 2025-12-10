import regex as re

import emoji
from typing import Final

from models.stats_model import Stats

EMOJI_RE = (
    emoji.get_emoji_regexp()
    if hasattr(emoji, "get_emoji_regexp")
    else re.compile(r"\p{Emoji}", re.UNICODE)
)
PUNCTSYM_RE: Final[re.Pattern[str]] = re.compile(r"[\p{P}\p{S}]", re.UNICODE)

def get_author(message: dict) -> str:
    author = message.get("from")
    return str(author).strip() if isinstance(author, str) and author.strip() else 'Unknown'


def _get_plain_text(message: dict) -> str | None:
    entities = message.get("text_entities")
    if not isinstance(entities, list) or not entities:
        return None

    first = entities[0]
    if not isinstance(first, dict):
        return None

    if first.get("type") != "plain":
        return None

    text = first.get("text")
    return text if isinstance(text, str) else None


def get_messages(message: dict, author: str, stats: Stats) -> None:
    if message.get("media_type") == "voice_message" and _get_plain_text(message) is None:
        stats.voice_total[author] += 1
    
    stats.messages_total[author] += 1


def get_reactions(message: dict, stats: Stats) -> None:
    reactions = message.get('reactions')
    if reactions:
        for reaction in reactions:
            if reaction['type'] == 'emoji':
                reactions_authors = reaction.get('recent', None)
                if not reactions_authors:
                    continue

                for reaction_author in reactions_authors:
                    stats.reactions[reaction_author['from']][reaction['emoji']] += 1


def get_emojis(text_entity: dict | None, author: str, stats: Stats, stopset: set[str]) -> None:
    if not isinstance(text_entity, dict):
        return

    if text_entity.get("type") != "plain":
        return

    text = text_entity.get("text")
    if not isinstance(text, str) or not text:
        return

    for emo in emoji.emoji_list(text):
        em = emo.get("emoji")
        if isinstance(em, str) and em:
            stats.emojis[author][em] += 1

    clean = EMOJI_RE.sub(" ", text)
    clean = PUNCTSYM_RE.sub(" ", clean)
    for token in clean.casefold().split():
        if token and token not in stopset:
            stats.words[author][token] += 1
