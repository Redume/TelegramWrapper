import json
import tempfile
import uuid

from pathlib import Path

import shutil
import orjson

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, status, File, BackgroundTasks
from fastapi.responses import JSONResponse
from stopwordsiso import has_lang
from stopwordsiso import stopwords as sw_iso

from utils.file import unarchive, aiosave_file
from utils.detect_lang import detect_lang
from models.stats_model import Stats
from functions.export_processing import get_author, get_emojis, get_messages, get_reactions, get_word
from functions.collect_messages import collect_messages

app = FastAPI(debug=True)
temp_dir = Path(tempfile.TemporaryDirectory().name)


@app.post('/upload')
async def _(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JSONResponse:
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
            return JSONResponse({
                "message": "No JSON file (result.json) found in the archive."
            }, status_code=status.HTTP_400_BAD_REQUEST)
    else:
        json_path = src_path

    try:
        with open(json_path, 'rb') as f:
            data = orjson.loads(f.read())
    except Exception:
        background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)
        return JSONResponse({"message": "Invalid JSON format"}, status_code=status.HTTP_400_BAD_REQUEST)
        
    messages = collect_messages(data)

    if not messages:
        background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)
        return JSONResponse({"message": "No data available"}, status_code=status.HTTP_400_BAD_REQUEST)
    
    stats = Stats()

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
        author = get_author(msg)
        if not author:
            continue

        get_messages(msg, author, stats)
        get_reactions(msg, stats)
        get_emojis(msg, author, stats)
        get_word(msg, author, stats, stopset)

    background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)

    if not stats.messages_total:        
        return JSONResponse({
            "message": "No data available for processing"
        }, status_code=status.HTTP_400_BAD_REQUEST)
    
    return JSONResponse({
        "authors": [
            {
                "name": a,
                "messages_total": stats.messages_total[a],
                "voice_message_total": stats.voice_total[a],
                "top_emojis": [
                    {
                        "emoji": emoji_token,
                        "value": data["value"],
                        **({"path": data["path"]} if data.get("path") else {})
                    }
                    for emoji_token, data in sorted(
                        stats.emojis[a].items(),
                        key=lambda x: x[1]["value"],
                        reverse=True
                    )[:10]
                ],
                "top_words": [
                    {"word": w, "value": v}
                    for w, v in stats.words[a].most_common(10)
                ],
                "top_reactions": [
                    {
                        "emoji": emoji,
                        "value": data["value"],
                        **({"path": data["path"]} if data.get("path") else {})
                    }
                    for emoji, data in sorted(
                        stats.reactions[a].items(),
                        key=lambda x: x[1]["value"],
                        reverse=True
                    )[:10]
                ]
            }
            for a in stats.messages_total
        ],
    })


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7070)
