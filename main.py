import json
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Final

import emoji
import regex as re
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, status, File, BackgroundTasks
from fastapi.responses import JSONResponse
from stopwordsiso import has_lang
from stopwordsiso import stopwords as sw_iso

from utils.file import unarchive, aiosave_file
from utils.detect_lang import detect_lang

app = FastAPI()

temp_dir = Path(tempfile.TemporaryDirectory().name)

EMOJI_RE = (
    emoji.get_emoji_regexp()
    if hasattr(emoji, "get_emoji_regexp")
    else re.compile(r"\p{Emoji}", re.UNICODE)
)

PUNCTSYM_RE: Final[re.Pattern[str]] = re.compile(r"[\p{P}\p{S}]", re.UNICODE)

@app.post('/upload')
async def _(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> None:
    if file.content_type not in ['application/zip', 'application/json']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail='This file type is not supported. Supported extensions: zip, json.'
            )

    # save file to temp dir
    sid = uuid.uuid4().hex
    work_dir = temp_dir / sid
    if not work_dir.exists():
        work_dir.mkdir(parents=True, exist_ok=True)

    src_path = work_dir / file.filename

    # save file and unarchive, find result.json
    await aiosave_file(file, src_path)

    json_path: Path | None
    if src_path.suffix.lower() == ".zip":
        json_path = unarchive(src_path, work_dir)
        if not json_path:
            background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No JSON file (result.json) found in the archive."
            )
    else:
        json_path = src_path

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    messages = data.get('messages', [])

    # counters
    author_message_counter: Counter[str] = Counter()
    voice_message_author_counter: Counter[str] = Counter()
    word_counter:  dict[str, Counter[str]] = defaultdict(Counter)
    emoji_counter: dict[str, Counter[str]] = defaultdict(Counter)
    reactions_counter: dict[str, Counter[str]] = defaultdict(Counter)

    sample_texts = [
        ent.get("text", "")
        for m in messages[:500]
        for ent in m.get("text_entities", [])[:1]
        if ent.get("type") == "plain"
    ]

    lang = detect_lang(sample_texts)
    stopset = set(sw_iso(lang)) if has_lang(lang) else set()

    # analyzing messages
    for msg in messages:
        author = msg.get('from', 'Unknown')

        if not msg.get('text_entities', []):
            if msg.get('media_type') == 'voice_message':
                voice_message_author_counter[author] += 1
            continue

        text_entities = msg['text_entities'][0]
        author = msg.get('from', 'Unknown')

        author_message_counter[author] += 1

        # reaction on message per user
        reactions = msg.get('reactions')
        if reactions:

            for reaction in reactions:
                if reaction['type'] == 'emoji':
                    reactions_authors = reaction.get('recent', None)
                    if not reactions_authors:
                        continue

                    for reaction_author in reactions_authors:
                        reactions_counter[reaction_author['from']][reaction['emoji']] += 1

        if text_entities['type'] == 'plain':

            # most use emoji per user
            for emo in emoji.emoji_list(text_entities['text']):    
                item_emoji = emo['emoji']
                emoji_counter[author][item_emoji] += 1

            # frequently used words of the user, without prefixes, etc.
            clean = EMOJI_RE.sub(" ", text_entities['text'])
            clean = PUNCTSYM_RE.sub(" ", clean)
            clean = clean.casefold()
            for token in clean.split():
                if token and token not in stopset:
                    word_counter[author][token] += 1


    return JSONResponse({
        "authors": [
            {
                "name": a,
                "messages_total": author_message_counter[a],
                "voice_message_total": voice_message_author_counter[a],
                "top_emojis": emoji_counter[a].most_common(10),
                "top_words":  word_counter[a].most_common(10),
                "top_reactions": reactions_counter[a].most_common(10)
            }
            for a in author_message_counter
        ],
    })


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7070)
