from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter, defaultdict
from typing import Dict
from typing_extensions import DefaultDict


@dataclass
class Stats:
    messages_total: Counter[str] = field(default_factory=Counter)
    voice_total: Counter[str] = field(default_factory=Counter)
    video_total: Counter[str] = field(default_factory=Counter)

    words: Dict[str, Counter[str]] = field(
        default_factory=lambda: defaultdict(Counter)
    )

    emojis: DefaultDict[str, DefaultDict[str, dict]] = field(
        default_factory=lambda: defaultdict(
            lambda: defaultdict(lambda: {"value": 0, "path": None})
        )
    )

    reactions: DefaultDict[str, DefaultDict[str, dict]] = field(
        default_factory=lambda: defaultdict(
            lambda: defaultdict(lambda: {"value": 0, "path": None})
        )
    )

    messages_per_day: Counter[str] = field(default_factory=Counter)
    emojis_total: Counter[str] = field(default_factory=Counter)
    reactions_total: Counter[str] = field(default_factory=Counter)

    chats: Dict[int, dict] = field(default_factory=dict)
    chats_authors: Dict[str, set] = field(default_factory=lambda: defaultdict(set))