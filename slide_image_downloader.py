import pandas as pd
import os
import requests
from io import BytesIO
from PIL import Image
import pillow_avif  # Required to read AVIF images

def download_image_convert_avif(url, save_path):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        if url.lower().endswith('.avif') or 'image/avif' in response.headers.get('Content-Type', '').lower():
            img = Image.open(BytesIO(response.content))
            img.save(save_path, format='PNG')
        else:
            with open(save_path, 'wb') as f:
                f.write(response.content)
        return True
    except Exception as e:
        print(f"[!] Failed to download or convert {url}: {e}")
        return False

def download_slide_images(input_file, output_base="slide_images", progress=None):
    df = pd.read_excel(input_file, sheet_name='Tasks').to_dict('records')
    total_images = len(df) * 4
    processed = 0

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
                    continue

                image_url = images[usp_index - 1].strip()
                style_id = str(row.get('Style ID', 'unknown')).strip()
                batch_folder = os.path.join(folder_name, f'batch_{batch}')
                os.makedirs(batch_folder, exist_ok=True)

                image_filename = f"{style_id}_{usp_index}.PNG"
                image_path = os.path.join(batch_folder, image_filename)

                if not os.path.exists(image_path):
                    download_image_convert_avif(image_url, image_path)

                processed += 1
                if progress:
                    progress['percent'] = int((processed / total_images) * 100)

                temp += 1
                if temp > 98:
                    temp = 1
                    batch += 1

            except Exception as e:
                print(f"[!] Error on row {i + 1}, slide {slide_num}: {e}")
                processed += 1
                if progress:
                    progress['percent'] = int((processed / total_images) * 100)

    progress['status'] = 'completed'
    progress['done'] = True
