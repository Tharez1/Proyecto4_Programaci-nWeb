from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi import UploadFile, File, Form

import boto3


app = FastAPI()


# CLIENTE S3
s3 = boto3.client("s3")

BUCKET_NAME = "tristan-web"


# archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


# templates HTML
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/api/message")
async def message():

    return {
        "message": "Hola desde FastAPI"
    }


# SUBIR IMAGEN A S3
@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    process_type: str = Form(...)
):

    print("SUBIENDO IMAGEN...")

    try:

        s3.upload_fileobj(
            file.file,
            BUCKET_NAME,
            f"img/{file.filename}",
            ExtraArgs={
                "ContentType": file.content_type,
                "Metadata": {
                    "process_type": process_type
                }
            }
        )

        print("IMAGEN SUBIDA")

        return {
            "message": f"{file.filename} subida correctamente a S3"
        }

    except Exception as e:

        print("ERROR:", str(e))

        return {
            "error": str(e)
        }