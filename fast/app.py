from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
import boto3
import redis
import os
import asyncio

app = FastAPI()

# CLIENTE S3
s3 = boto3.client("s3")
BUCKET_NAME = "tristan-web"

# REDIS
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    decode_responses=True
)

# ARCHIVOS ESTÁTICOS Y TEMPLATES
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# SUBIR IMAGEN A S3
@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    process_type: str = Form(...)
):
    print(f"SUBIENDO: {file.filename} → process_type={process_type}", flush=True)
    try:
        s3.upload_fileobj(
            file.file,
            BUCKET_NAME,
            f"img/{file.filename}",
            ExtraArgs={
                "ContentType": file.content_type,
                "Metadata": {"process_type": process_type}
            }
        )
        print(f"SUBIDA OK: img/{file.filename}", flush=True)
        r.set(file.filename, "pendiente")
        return {"message": f"{file.filename} subida correctamente", "filename": file.filename}
    except Exception as e:
        print("ERROR upload:", str(e), flush=True)
        return {"error": str(e)}
        
# SSE — STREAM DE ESTADO
@app.get("/status/stream/{filename}")
async def status_stream(filename: str):

    async def event_generator():
        while True:
            status = r.get(filename) or "pendiente"
            yield f"data: {status}\n\n"

            if status in ("completed", "error"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# CONSULTAR ESTADO (opcional, para polling manual)
@app.get("/status/{filename}")
async def get_status(filename: str):
    status = r.get(filename) or "pendiente"
    return {"filename": filename, "status": status}