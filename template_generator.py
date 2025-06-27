import pandas as pd
import os

def generate_all_templates(input_file: str, output_dir: str = "outputs") -> list:
    try:
        df = pd.read_excel(input_file).to_dict('records')
        os.makedirs(output_dir, exist_ok=True)

        default_prompt = 'Generate white background'
        slides = {1: [], 2: [], 3: [], 4: []}

        for data in df:
            brand = data.get('Brand', '').strip()
            style_id = data.get('Style ID', '')

            for i in range(1, 5):
                usp_raw = data.get(f'USP {i}', '')
                if not usp_raw or not isinstance(usp_raw, str):
                    continue

                usp_lines = [line.strip() for line in usp_raw.strip().split('\n') if line.strip()]

                if i == 1 and brand:
                    brand_lower = brand.lower()
                    usp_text_combined = ' '.join(usp_lines).lower()
                    if brand_lower not in usp_text_combined and usp_lines:
                        usp_lines[0] = f"{brand} {usp_lines[0]}"

                for index, usp_line in enumerate(usp_lines):
                    slide_entry = {
                        'Background image prompt': default_prompt,
                        'Foreground image file name': f"{style_id}_{data.get(f'USP Image {i}', '')}.PNG",
                        f'bullet_point_{index+1}': usp_line
                    }
                    slides[i].append(slide_entry)

        output_files = []
        for i in range(1, 5):
            df_slide = pd.DataFrame(slides[i])
            output_file = os.path.join(output_dir, f"slide_{i}.xlsx")
            df_slide.to_excel(output_file, index=False)
            output_files.append(output_file)

        return output_files

    except Exception as e:
        print(f"[!] Template generation failed: {e}")
        return []
