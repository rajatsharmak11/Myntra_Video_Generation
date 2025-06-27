import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import pillow_avif  # Enables AVIF support

def download_slide_images(input_file, output_base="slide_images", progress=None):
    df = pd.read_excel(input_file, sheet_name='Tasks').to_dict('records')
    total_images = len(df) * 4  # 4 slides per product
    processed = 0

    if progress:
        progress["status"] = "downloading"
        progress["percent"] = 0
        progress["current"] = 0
        progress["total"] = total_images

    for slide_num in range(1, 5):
        folder_name = os.path.join(output_base, f"Slide {slide_num}")
        temp = 1
        batch = 1

        for i, row in enumerate(df):
            try:
                images = str(row.get('images', '')).split(',')
                usp_index = int(row.get(f'USP Image {slide_num}', 0))

                if usp_index < 1 or usp_index > len(images):
                    processed += 1
                    if progress:
                        progress["current"] = processed
                        progress["percent"] = int((processed / total_images) * 100)
                    continue

                image_url = images[usp_index - 1].strip()
                style_id = str(row.get('Style ID', 'unknown')).strip()
                batch_folder = os.path.join(folder_name, f'batch_{batch}')
                os.makedirs(batch_folder, exist_ok=True)

                image_filename = f"{style_id}_{usp_index}.PNG"
                image_path = os.path.join(batch_folder, image_filename)

                if not os.path.exists(image_path):
                    response = requests.get(image_url, timeout=10)
                    if 'image/avif' in response.headers.get('Content-Type', ''):
                        img = Image.open(BytesIO(response.content))
                        img.save(image_path, format='PNG')
                    else:
                        with open(image_path, 'wb') as f:
                            f.write(response.content)

                processed += 1
                if progress:
                    progress["current"] = processed
                    progress["percent"] = int((processed / total_images) * 100)

                temp += 1
                if temp > 98:
                    temp = 1
                    batch += 1

            except Exception as e:
                print(f"[!] Error on row {i+1}, slide {slide_num}: {e}")
                processed += 1
                if progress:
                    progress["current"] = processed
                    progress["percent"] = int((processed / total_images) * 100)

    if progress:
        progress["status"] = "done"
        progress["percent"] = 100
        progress["current"] = total_images

    return output_base
