from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter, defaultdict

@dataclass
class Stats:
    messages_total: Counter[str] = field(default_factory=Counter)
    voice_total: Counter[str] = field(default_factory=Counter)
    words: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    emojis: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    reactions: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
