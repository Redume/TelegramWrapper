from fastapi import FastAPI, UploadFile, HTTPException, status, Request
import uvicorn
import tempfile
from pathlib import Path
import uuid
import aiofiles
import json

import zipfile

from typing import Annotated
app = FastAPI()

temp_dir = Path(tempfile.TemporaryDirectory().name)

async def aiosave_file(src: UploadFile, dst: Path) -> None:
    async with aiofiles.open(dst, "wb") as out:
        while chunk := await src.read(64 * 1024):
            await out.write(chunk)
    await src.close()

def extract_first_json(zip_path: Path, dest_dir: Path) -> Path | None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.lower().endswith(".json"):
                zf.extract(member, path=dest_dir)
                return dest_dir / member
    return None


@app.post('/upload')
async def upload_export(file: UploadFile, req: Request) -> None:

    if not file.content_type in ['application/zip', 'application/json']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail='This file type is not supported. Supported extensions: zip, json.'
            )

    sid = uuid.uuid4().hex
    work_dir = temp_dir / sid
    if not work_dir.exists():
        work_dir.mkdir(parents=True, exist_ok=True)

    src_path = work_dir / file.filename

    await aiosave_file(file, src_path)

    json_path: Path | None
    if src_path.suffix.lower() == ".zip":
        json_path = extract_first_json(src_path, work_dir)
        if not json_path:
            background_tasks.add_task(shutil.rmtree, work_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No JSON file (result.json) found in the archive."
            )
    else:
        json_path = src_path

    with open(json_path) as file:
        print(json.load(file))

    return file

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7070)
