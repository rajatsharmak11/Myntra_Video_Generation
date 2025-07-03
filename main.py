from myntra_image_merge import convert_excel_to_image_format
from slide_image_downloader import download_slide_images
from template_generator import generate_all_templates
from video_merge import group_and_copy_videos_by_sku
from video_merge import merge_videos_from_folder
from progress import progress_state


from fastapi.responses import HTMLResponse, FileResponse,JSONResponse
from fastapi import FastAPI, File, UploadFile, Request, Form
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import BackgroundTasks
from collections import defaultdict
from typing import Dict
import threading
import asyncio
import zipfile
import shutil
import uuid
import json
import os

# Track progress per session ID
progress_tracker: Dict[str, int] = {}

progress = {
    "percent": 0,
    "status": "idle",
    "current": 0,
    "total": 1
}



uploaded_folder_zip = None

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
AUDIO_FILE_PATH = "Myntra_updated_audio.mp3"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def zip_output_files(file_paths: list, output_zip_path: str):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            arcname = os.path.basename(file_path)
            zipf.write(file_path, arcname)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

uploaded_file_name = None

# For Image Merge -------------------------------------------------------------
@app.get("/image_merge", response_class=HTMLResponse)
def image_merge_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "file_uploaded": False})

@app.post("/image_merge/upload", response_class=HTMLResponse)
async def upload_image_merge(request: Request, file: UploadFile = File(...)):
    global uploaded_image_merge_file
    uploaded_image_merge_file = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(uploaded_image_merge_file, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return templates.TemplateResponse("index.html", {"request": request, "file_uploaded": True})

@app.post("/image_merge/process", response_class=HTMLResponse)
def process_image_merge(request: Request):
    if not uploaded_image_merge_file or not os.path.exists(uploaded_image_merge_file):
        return templates.TemplateResponse("index.html", {"request": request, "file_uploaded": False, "error": "No file uploaded."})
    from myntra_image_merge import convert_excel_to_image_format
    success = convert_excel_to_image_format(uploaded_image_merge_file, os.path.join(OUTPUT_FOLDER, "myntra_image_merge.xlsx"))
    context = {"request": request, "file_uploaded": True}
    if success:
        context["download_ready"] = True
        context["output_file"] = "myntra_image_merge.xlsx"
    else:
        context["error"] = "Processing failed."
    return templates.TemplateResponse("index.html", context)

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    return FileResponse(path=file_path, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# For Template Generation --------------------------------------------------------------------------------


@app.get("/template", response_class=HTMLResponse)
def template_generator_page(request: Request):
    return templates.TemplateResponse("template.html", {"request": request, "file_uploaded": False})

@app.post("/template/upload", response_class=HTMLResponse)
async def upload_template(request: Request, file: UploadFile = File(...)):
    global uploaded_template_file
    uploaded_template_file = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(uploaded_template_file, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return templates.TemplateResponse("template.html", {"request": request, "file_uploaded": True})


@app.post("/template/process", response_class=HTMLResponse)
def process_template(request: Request):
    global uploaded_template_file
    if not uploaded_template_file or not os.path.exists(uploaded_template_file):
        return templates.TemplateResponse("template.html", {"request": request, "file_uploaded": False, "error": "No file uploaded."})
    
    output_files = generate_all_templates(uploaded_template_file, OUTPUT_FOLDER)
    context = {"request": request, "file_uploaded": True}

    if output_files:
        # Pass only filenames, not full paths
        context["download_ready"] = True
        context["output_files"] = [os.path.basename(f) for f in output_files]
    else:
        context["error"] = "Template generation failed."
    return templates.TemplateResponse("template.html", context)
    

# For Image Downloading -----------------------------------------------------------------
@app.get("/downloader", response_class=HTMLResponse)
def downloader_page(request: Request):
    return templates.TemplateResponse("downloader.html", {"request": request, "file_uploaded": False})

@app.post("/downloader/upload", response_class=HTMLResponse)
async def upload_downloader(request: Request, file: UploadFile = File(...)):
    global uploaded_downloader_file
    uploaded_downloader_file = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(uploaded_downloader_file, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return templates.TemplateResponse("downloader.html", {"request": request, "file_uploaded": True})

@app.post("/downloader/process", response_class=HTMLResponse)
def process_downloader(request: Request, background_tasks: BackgroundTasks):
    if not uploaded_downloader_file or not os.path.exists(uploaded_downloader_file):
        return templates.TemplateResponse("downloader.html", {"request": request, "file_uploaded": False, "error": "No file uploaded."})

    # Reset progress
    progress.update({"percent": 0, "status": "downloading", "current": 0, "total": 1})

    try:
        folder = download_slide_images(uploaded_downloader_file, progress=progress)
        zip_filename = f"slides_output.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)

        shutil.make_archive(zip_path.replace(".zip", ""), 'zip', folder)
        background_tasks.add_task(shutil.rmtree, folder)

        return templates.TemplateResponse("downloader.html", {
            "request": request,
            "file_uploaded": True,
            "download_ready": True,
            "zip_file": zip_filename
        })
    except Exception as e:
        progress["status"] = "error"
        return templates.TemplateResponse("downloader.html", {
            "request": request,
            "file_uploaded": True,
            "error": str(e)
        })    


@app.get("/downloader/progress")
def get_download_progress():
    return JSONResponse(content=progress)

# For Video Merge -------------------------------------------------------------------------

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/video_merge")

@app.get("/merge-progress")
async def merge_progress():
    async def event_generator():
        while not progress_state["done"]:
            yield f"data: {json.dumps(progress_state)}\n\n"
            await asyncio.sleep(1)
        yield f"data: {json.dumps(progress_state)}\n\n"
    return EventSourceResponse(event_generator())

@app.get("/video_merge", response_class=HTMLResponse)
def video_merge_page(request: Request):
    return templates.TemplateResponse("video_merge.html", {"request": request, "file_uploaded": False})


@app.post("/video_merge/upload", response_class=HTMLResponse)
async def upload_zip_and_merge(request: Request, file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())

    session_path = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_path, exist_ok=True)

    # Save uploaded ZIP
    zip_path = os.path.join(session_path, "uploaded.zip")
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract ZIP
    extracted_path = os.path.join(session_path, "extracted")
    os.makedirs(extracted_path, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extracted_path)

    # If single root folder inside ZIP
    extracted_items = os.listdir(extracted_path)
    if len(extracted_items) == 1:
        first_path = os.path.join(extracted_path, extracted_items[0])
        if os.path.isdir(first_path):
            extracted_path = first_path

    print("Decoded structure:", os.listdir(extracted_path))

    # Group and organize
    sku_folder_path = group_and_copy_videos_by_sku(extracted_path, session_path)

    # Merge
    merged_files = merge_videos_from_folder(sku_folder_path, OUTPUT_FOLDER, AUDIO_FILE_PATH)
    print("Merged outputs:", merged_files)

    # Zip final result
    zip_filename = f"merged_videos_{session_id}.zip"
    zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
    zip_output_files(merged_files, zip_path)

    # Cleanup session
    shutil.rmtree(session_path, ignore_errors=True)

    context = {
        "request": request,
        "file_uploaded": True,
        "merged_files": [os.path.basename(m) for m in merged_files],
        "zip_file": os.path.basename(zip_path)
    }

    return templates.TemplateResponse("video_merge.html", context)


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/zip')
    return {"error": "File not found"}

