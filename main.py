from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks
import zipfile
import shutil
import os

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
    if not uploaded_template_file or not os.path.exists(uploaded_template_file):
        return templates.TemplateResponse("template.html", {"request": request, "file_uploaded": False, "error": "No file uploaded."})
    from template_generator import generate_all_templates
    output_files = generate_all_templates(uploaded_template_file, OUTPUT_FOLDER)
    context = {"request": request, "file_uploaded": True}
    if output_files:
        context["download_ready"] = True
        context["output_files"] = output_files
    else:
        context["error"] = "Template generation failed."
    return templates.TemplateResponse("template.html", context)
    

# For Image Downloading -----------------------------------------------------------------
from slide_image_downloader import download_slide_images

# === CONFIG ===

templates = Jinja2Templates(directory="templates")
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === STATE ===
uploaded_downloader_file = None
download_progress = {
    "status": "idle",
    "percent": 0,
    "done": False,
    "output_zip": None
}

# === ROUTES ===

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("downloader.html", {"request": request, "file_uploaded": False})

@app.get("/downloader", response_class=HTMLResponse)
def downloader_page(request: Request):
    return templates.TemplateResponse("downloader.html", {"request": request, "file_uploaded": False})

@app.post("/downloader/upload", response_class=HTMLResponse)
async def upload_downloader_file(request: Request, file: UploadFile = File(...)):
    global uploaded_downloader_file
    uploaded_downloader_file = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(uploaded_downloader_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return templates.TemplateResponse("downloader.html", {
        "request": request,
        "file_uploaded": True
    })

@app.post("/downloader/start")
async def start_download_task(background_tasks: BackgroundTasks):
    global download_progress
    download_progress = {
        "status": "downloading",
        "percent": 0,
        "done": False,
        "output_zip": None
    }

    def run_download():
        output_folder = download_slide_images(uploaded_downloader_file, "slide_images", download_progress)

        zip_path = os.path.join(OUTPUT_FOLDER, "slide_images.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_folder):
                for file in files:
                    abs_path = os.path.join(root, file)
                    arcname = os.path.relpath(abs_path, start=output_folder)
                    zipf.write(abs_path, arcname)

        download_progress['output_zip'] = "slide_images.zip"
        download_progress['done'] = True
        download_progress['status'] = 'completed'

    background_tasks.add_task(run_download)
    return {"message": "Download started"}

@app.get("/downloader/progress")
def check_progress():
    return download_progress

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#For Folder creation for video -------------------------------------------------------------------
# import os
# import shutil
# import time
# import zipfile

# from fastapi import FastAPI, UploadFile, File, Request
# from fastapi.responses import FileResponse, HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

# from folder_organizer import process_video_folders

# # Create folders if not present
# UPLOAD_FOLDER = "uploads"
# OUTPUT_FOLDER = "outputs"
# TEMPLATES_FOLDER = "templates"

# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# # Mount static files and templates
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory=TEMPLATES_FOLDER)

# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/folder_organizer", response_class=HTMLResponse)
# async def folder_organizer_page(request: Request):
#     return templates.TemplateResponse("folder_organizer.html", {
#         "request": request,
#         "file_uploaded": False,
#         "download_ready": False,
#         "error": None,
#     })


# @app.post("/folder_organizer/process", response_class=HTMLResponse)
# async def process_folder_zip(
#     request: Request,
#     file: UploadFile = File(...)
# ):
#     try:
#         # Save uploaded zip file
#         zip_filename = f"uploaded_{int(time.time())}.zip"
#         uploaded_zip_path = os.path.join(UPLOAD_FOLDER, zip_filename)

#         with open(uploaded_zip_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         # Extract uploaded zip
#         extracted_path = os.path.join(UPLOAD_FOLDER, "extracted_" + str(int(time.time())))
#         os.makedirs(extracted_path, exist_ok=True)

#         with zipfile.ZipFile(uploaded_zip_path, 'r') as zip_ref:
#             zip_ref.extractall(extracted_path)

#         # Process with your organizer script
#         organized_folder = process_video_folders(extracted_path, OUTPUT_FOLDER)

#         # Zip the result
#         zip_name = f"organized_output_{int(time.time())}.zip"
#         zip_path = os.path.join(OUTPUT_FOLDER, zip_name)

#         with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for root, _, files in os.walk(organized_folder):
#                 for file in files:
#                     full_path = os.path.join(root, file)
#                     arcname = os.path.relpath(full_path, start=organized_folder)
#                     zipf.write(full_path, arcname)

#         # Return the page with download link
#         return templates.TemplateResponse("folder_organizer.html", {
#             "request": request,
#             "file_uploaded": True,
#             "download_ready": True,
#             "output_file": zip_name
#         })

#     except Exception as e:
#         return templates.TemplateResponse("folder_organizer.html", {
#             "request": request,
#             "file_uploaded": True,
#             "error": f"Error processing file: {str(e)}"
#         })


# @app.get("/download/{filename}")
# def download_file(filename: str):
#     file_path = os.path.join(OUTPUT_FOLDER, filename)
#     if os.path.exists(file_path):
#         return FileResponse(path=file_path, filename=filename, media_type='application/zip')
#     return {"error": "File not found"}