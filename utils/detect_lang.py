from langdetect import LangDetectException, detect

def detect_lang(sample: list[str]) -> str:
    try:
        return detect(" ".join(sample)) if sample else "unknown"
    except LangDetectException:
        return "unknown"
