

async def aiosave_file(src: UploadFile, dst: Path) -> None:
    async with aiofiles.open(dst, "wb") as out:
        while chunk := await src.read(64 * 1024):
            await out.write(chunk)
    await src.close()

def unarchive(zip_path: Path, dest_dir: Path) -> Path | None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.lower().endswith(".json"):
                zf.extract(member, path=dest_dir)
                return dest_dir / member
    return None
