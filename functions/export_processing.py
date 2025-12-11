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

def get_author(message: dict) -> str | None:
    author = message.get("from")
    return str(author).strip() if isinstance(author, str) and author.strip() else None


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
    if not isinstance(reactions, list):
        return

    for reaction in reactions:
        if not isinstance(reaction, dict):
            continue

        emoji_token = reaction.get("emoji") or reaction.get("document_id")

        if not emoji_token:
            continue

        recent = reaction.get("recent") or []
        for ra in recent:
            if not isinstance(ra, dict):
                continue
            author = ra.get("from") or ra.get("from_id")

            if emoji_token not in stats.reactions[author]:
                stats.reactions[author][emoji_token] = {
                    "value": 0,
                }

            stats.reactions[author][emoji_token]["value"] += 1


def get_emojis(message: dict, author: str, stats: Stats) -> None:
    text_entity = (message.get("text_entities") or [None])[0]

    if not isinstance(text_entity, dict):
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


def get_word(message: dict, author, stats: Stats, stopset: set[str]) -> None:
    text = _get_plain_text(message)
    if not text:
        return None

    clean = EMOJI_RE.sub(" ", text)
    clean = PUNCTSYM_RE.sub(" ", clean)
    for token in clean.casefold().split():
        if token and token not in stopset:
            stats.words[author][token] += 1
