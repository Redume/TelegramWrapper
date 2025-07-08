from fastapi import FastAPI, UploadFile, HTTPException, status, Request
import uvicorn

from typing import Annotated
app = FastAPI()


@app.post('/upload')
async def upload_export(file: UploadFile, req: Request) -> None:

    if not file.content_type in ['application/zip', 'application/json']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail='This file type is not supported. Supported extensions: zip, json.'
            )

    return file

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7070)
