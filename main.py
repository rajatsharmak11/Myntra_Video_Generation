from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks
import zipfile
import shutil
import os

progress = {
    "percent": 0,
    "status": "idle",
    "current": 0,
    "total": 1
}
uploaded_folder_zip = None


# For Image Merge -------------------------------------------------------------

from myntra_image_merge import convert_excel_to_image_format



app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

uploaded_file_name = None

# Image Merge (script1_converter)
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
from template_generator import generate_all_templates

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
from slide_image_downloader import download_slide_images  # <-- add this



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
    
from fastapi.responses import JSONResponse

@app.get("/downloader/progress")
def get_download_progress():
    return JSONResponse(content=progress)
