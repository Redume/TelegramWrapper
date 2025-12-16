import regex as re
from langdetect import LangDetectException, detect

EMOJI_RE = re.compile(r"\p{Emoji}", re.UNICODE)

def detect_lang(sample: list[str]) -> str:
    if not sample:
        return "unknown"

    cleaned = []
    for s in sample:
        if len(s) < 3:
            continue
        s = EMOJI_RE.sub("", s)
        if s.strip():
            cleaned.append(s)

    if not cleaned:
        return "unknown"

    text = " ".join(cleaned)
    text = text[:5000]

    try:
        return detect(text)
    except LangDetectException:
        pass

    cyr = sum(ch.isalpha() and ("А" <= ch <= "я") for ch in text)
    lat = sum(ch.isalpha() and ("A" <= ch <= "z") for ch in text)

    if cyr > lat:
        return "ru"
    if lat > cyr:
        return "en"
    return "unknown"
