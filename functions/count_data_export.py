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


def get_messages(message: dict, author: str, stats: Stats) -> None:
    if not message['text_entities'][0] and ['media_type'] == 'voice_message':
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


def get_emojis(message: dict, author, stats: Stats, stopset: set | str) -> None:
    text_entities = message['text_entities']
    if text_entities['type'] == 'plain':
        for emo in emoji.emoji_list(text_entities['text']):    
            item_emoji = emo['emoji']
            stats.emojis[author][item_emoji] += 1

        clean = EMOJI_RE.sub(" ", text_entities['text'])
        clean = PUNCTSYM_RE.sub(" ", clean)
        clean = clean.casefold()
        for token in clean.split():
            if token and token not in stopset:
                stats.words[author][token] += 1
