import tempfile
import uuid
import shutil
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Set, Any

import orjson
import uvicorn
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status
from stopwordsiso import has_lang, stopwords as sw_iso
import emoji

from models.stats_model import Stats
from utils.fail_safe import safe_get, safe_list, safe_dict, get_author, get_bot_names, extract_text
from functions.collect_messages import collect_messages
from functions.export_processing import get_messages
from utils.detect_lang import detect_lang
from utils.file import aiosave_file, unarchive

config = {
    "saved_messages": False,
    "bots": False,
    "chats": False,
    "channels": False,
}

CHAT_TYPE_MAP = {
    "saved_messages": "saved_messages",
    "bot_chat": "bots",
    "personal_chat": "chats",
    "private_group": "chats",
    "private_supergroup": "chats",
    "public_supergroup": "chats",
    "private_channel": "channels",
    "public_channel": "channels"
}

app = FastAPI(debug=False)
temp_dir = Path(tempfile.mkdtemp())

@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JSONResponse:
    work_dir = temp_dir / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        is_zip = file.content_type == "application/zip" or file.filename.lower().endswith(".zip")
        is_json = file.content_type == "application/json" or file.filename.lower().endswith(".json")

        if not (is_zip or is_json):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
                detail='This file type is not supported. Supported extensions: zip, json.'
            )

        src_path = work_dir / file.filename
        await aiosave_file(file, src_path)

        target_json_path = src_path

        if is_zip:
            extracted_json = unarchive(src_path, work_dir)
            if not extracted_json:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="result.json not found in the archive"
                )
            target_json_path = extracted_json

        try:
            data = orjson.loads(target_json_path.read_bytes())
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON file")

        bot_names = get_bot_names(data)
        messages = collect_messages(data, bot_names)

        if not messages:
            return JSONResponse({"message": "No messages found"}, status_code=200)

        stats = Stats()
        stopset: Set[str] = set()
        sample_texts = [extract_text(m) for m in messages[:500]]
        lang = "en"
        if sample_texts:
            try:
                lang = detect_lang(sample_texts)
            except Exception:
                pass
        if lang and has_lang(lang):
            stopset = set(sw_iso(lang))

        for msg in messages:
            author = get_author(msg)
            stats.messages_total[author] += 1
            text = extract_text(msg)
            if text:
                for word in text.lower().split():
                    if word not in stopset:
                        stats.words[author][word] += 1

            for reaction in safe_list(msg.get("reactions")):
                token = reaction.get("emoji")
                if not token:
                    continue
                for r in safe_list(reaction.get("recent")):
                    stats.reactions[author][token]["value"] += 1
                    stats.reactions_total[token] += 1

            for ch in text:
                if emoji.is_emoji(ch):
                    stats.emojis[author][ch]["value"] += 1
                    stats.emojis_total[ch] += 1


            if msg.get("media_type") == "voice_message":
                stats.voice_total[author] += 1

            cid = msg.get("chat_id")
            if cid is not None:
                chat = stats.chats.setdefault(cid, {
                    "id": cid,
                    "name": msg.get("chat_name") or "Unknown chat",
                    "type": msg.get("chat_type") or "unknown",
                    "messages_from_owner": 0,
                    "words": Counter(),
                    "emojis": defaultdict(lambda: {"value": 0, "path": None}),
                    "reactions": defaultdict(lambda: {"value": 0, "path": None}),
                })
                stats.chats_authors[author].add(cid)
                if msg.get("from") == author:
                    chat["messages_from_owner"] += 1

        response: Dict[str, Any] = {}

        response["user"] = {
            "user_id": safe_get(data.get("personal_information"), "user_id"),
            "user_name": "{} {}".format(
                safe_get(data.get("personal_information"), "first_name", ""),
                safe_get(data.get("personal_information"), "last_name", "")
            ).strip(),
            "user_pfp_url": "",
            "all_messages_total": sum(stats.messages_total.values()),
            "direct_messages_total": sum(v for k, v in stats.messages_total.items() if k not in stats.chats_authors),
            "group_messages_total": sum(v for k, v in stats.messages_total.items() if k in stats.chats_authors),
            "group_chats_total": len(stats.chats_authors),
            "voice_messages_total": sum(stats.voice_total.values()),
            "video_messages_total": sum(getattr(stats, "video_total", {}).values()),
            "most_used_chat": max(stats.chats_authors, key=lambda x: len(stats.chats_authors[x]), default=None),
            "most_active_day": max(getattr(stats, "messages_per_day", {}), key=lambda x: getattr(stats, "messages_per_day", {}).get(x), default=None),
            "most_used_emoji": max(stats.emojis_total, key=stats.emojis_total.get, default=None),
            "most_used_reaction": max(stats.reactions_total, key=stats.reactions_total.get, default=None)
        }

        authors_arr = []
        for a in stats.messages_total.keys():
            authors_arr.append({
                "name": a,
                "messages_total": stats.messages_total[a],
                "voice_message_total": stats.voice_total[a],
                "top_emojis": [
                    {"emoji": e, "value": d["value"]}
                    for e, d in sorted(stats.emojis[a].items(), key=lambda x: x[1]["value"], reverse=True)[:10]
                ],
                "top_words": [{"word": w, "value": v} for w, v in stats.words[a].most_common(10)],
                "top_reactions": [
                    {"emoji": e, "value": d["value"]}
                    for e, d in sorted(stats.reactions[a].items(), key=lambda x: x[1]["value"], reverse=True)[:10]
                ],
            })
        response["authors"] = authors_arr

        chats_out = []
        for cid, chat in stats.chats.items():
            chat_type = chat.get("type")
            cfg_key = CHAT_TYPE_MAP.get(chat_type)
            if not cfg_key or not config.get(cfg_key):
                continue
            chats_out.append({
                "chat_id": cid,
                "chat_name": chat.get("name") or "Unknown chat",
                "messages_from_owner": chat.get("messages_from_owner", 0),
                "top_words": [{"word": w, "value": c} for w, c in chat.get("words", {}).most_common(10)],
                "top_emojis": [{"emoji": k, "value": v["value"]} for k, v in sorted(chat.get("emojis", {}).items(), key=lambda x: x[1]["value"], reverse=True)[:10]],
                "top_reactions": [{"emoji": k, "value": v["value"]} for k, v in sorted(chat.get("reactions", {}).items(), key=lambda x: x[1]["value"], reverse=True)[:10]],
            })
        response["chats"] = chats_out

        return JSONResponse(response)

    finally:
        background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7070)
