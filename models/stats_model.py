from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter, defaultdict
from typing_extensions import DefaultDict

@dataclass
class Stats:
    messages_total: Counter[str] = field(default_factory=Counter)
    voice_total: Counter[str] = field(default_factory=Counter)
    words: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    emojis: DefaultDict[str, DefaultDict[str, dict]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: {"value": 0}))
    )
    reactions: dict[str, dict[str, dict]] = field(default_factory=lambda: defaultdict(dict))