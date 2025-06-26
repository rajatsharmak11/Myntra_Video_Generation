# script1_converter.py

import pandas as pd
import os

def convert_excel_to_image_format(input_file, output_file='outputs/myntra_image_merge.xlsx'):
    try:
        df = pd.read_excel(input_file)

        # Find columns starting with "AL"
        al_columns = [col for col in df.columns if str(col).startswith("AL")]
        if not al_columns:
            print("[!] No columns starting with 'AL' found.")
            return False

        # Create 'images' column by combining all non-empty ALx values
        def extract_images(row):
            links = []
            for col in al_columns:
                val = row.get(col, '')
                if pd.notna(val) and str(val).strip():
                    links.append(str(val).strip())
            return ','.join(links)

        df['images'] = df.apply(extract_images, axis=1)

        os.makedirs('outputs', exist_ok=True)
        df.to_excel(output_file, index=False)

        print(f"[✓] Output written to: {output_file}")
        return True

    except Exception as e:
        print(f"[✖] Error: {e}")
        return False
